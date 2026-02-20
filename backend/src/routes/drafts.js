const express = require('express');
const jwt = require('jsonwebtoken');
const { pool } = require('../db/pool');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'ipl-fantasy-secret-key-2026';

// Middleware to verify token
const auth = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.id;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// Get draft for league
router.get('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    const result = await pool.query(
      'SELECT * FROM auction_drafts WHERE league_id = $1 ORDER BY created_at DESC LIMIT 1',
      [leagueId]
    );

    if (result.rows.length === 0) {
      return res.json(null);
    }

    const draft = result.rows[0];

    // Get current player if exists
    let currentPlayer = null;
    if (draft.current_player_id) {
      const playerResult = await pool.query(
        'SELECT * FROM players WHERE id = $1',
        [draft.current_player_id]
      );
      if (playerResult.rows.length > 0) {
        const p = playerResult.rows[0];
        currentPlayer = {
          id: p.id,
          name: p.name,
          role: p.role,
          team: p.team,
          basePrice: parseFloat(p.base_price)
        };
      }
    }

    // Get current bidder
    let currentBidder = null;
    if (draft.current_bidder_id) {
      const bidderResult = await pool.query(
        `SELECT lm.*, u.display_name 
         FROM league_members lm 
         JOIN users u ON lm.user_id = u.id 
         WHERE lm.id = $1`,
        [draft.current_bidder_id]
      );
      if (bidderResult.rows.length > 0) {
        const b = bidderResult.rows[0];
        currentBidder = {
          id: b.id,
          teamName: b.team_name,
          displayName: b.display_name
        };
      }
    }

    res.json({
      id: draft.id,
      leagueId: draft.league_id,
      status: draft.status,
      currentPlayer,
      currentBid: parseFloat(draft.current_bid),
      currentBidder,
      timerSeconds: draft.timer_seconds,
      createdAt: draft.created_at
    });
  } catch (error) {
    console.error('Get draft error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Start auction draft
router.post('/league/:leagueId/start', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const io = req.app.get('io');

    // Verify commissioner
    const leagueResult = await pool.query(
      'SELECT * FROM leagues WHERE id = $1 AND commissioner_id = $2',
      [leagueId, req.userId]
    );

    if (leagueResult.rows.length === 0) {
      return res.status(403).json({ error: 'Only commissioner can start draft' });
    }

    // Get available players (not sold)
    const playersResult = await pool.query(
      `SELECT p.* FROM players p
       WHERE NOT EXISTS (
         SELECT 1 FROM team_players tp
         JOIN teams t ON tp.team_id = t.id
         WHERE tp.player_id = p.id AND t.league_id = $1
       )
       ORDER BY p.base_price DESC`,
      [leagueId]
    );

    // Create draft
    const draftResult = await pool.query(
      `INSERT INTO auction_drafts (league_id, status, current_player_id, current_bid) 
       VALUES ($1, 'active', $2, $3) 
       RETURNING *`,
      [leagueId, playersResult.rows[0].id, playersResult.rows[0].base_price]
    );

    // Update league status
    await pool.query(
      "UPDATE leagues SET status = 'drafting', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
      [leagueId]
    );

    const draft = draftResult.rows[0];
    const firstPlayer = playersResult.rows[0];

    // Broadcast to all clients in league room
    io.to(`league-${leagueId}`).emit('draft:started', {
      draftId: draft.id,
      currentPlayer: {
        id: firstPlayer.id,
        name: firstPlayer.name,
        role: firstPlayer.role,
        team: firstPlayer.team,
        basePrice: parseFloat(firstPlayer.base_price)
      },
      currentBid: parseFloat(firstPlayer.base_price)
    });

    res.json({
      id: draft.id,
      status: draft.status,
      currentPlayer: {
        id: firstPlayer.id,
        name: firstPlayer.name,
        role: firstPlayer.role,
        team: firstPlayer.team,
        basePrice: parseFloat(firstPlayer.base_price)
      }
    });
  } catch (error) {
    console.error('Start draft error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Place bid
router.post('/:draftId/bid', auth, async (req, res) => {
  try {
    const { draftId } = req.params;
    const { amount } = req.body;
    const io = req.app.get('io');

    // Get draft
    const draftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE id = $1',
      [draftId]
    );

    if (draftResult.rows.length === 0) {
      return res.status(404).json({ error: 'Draft not found' });
    }

    const draft = draftResult.rows[0];

    if (draft.status !== 'active') {
      return res.status(400).json({ error: 'Draft is not active' });
    }

    if (amount <= parseFloat(draft.current_bid)) {
      return res.status(400).json({ error: 'Bid must be higher than current bid' });
    }

    // Get user's member record
    const memberResult = await pool.query(
      'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
      [draft.league_id, req.userId]
    );

    if (memberResult.rows.length === 0) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    const member = memberResult.rows[0];

    if (parseFloat(member.budget_remaining) < amount) {
      return res.status(400).json({ error: 'Insufficient budget' });
    }

    // Update bid
    await pool.query(
      `UPDATE auction_drafts 
       SET current_bid = $1, current_bidder_id = $2, timer_seconds = 60, updated_at = CURRENT_TIMESTAMP 
       WHERE id = $3`,
      [amount, member.id, draftId]
    );

    // Broadcast bid to all clients
    io.to(`league-${draft.league_id}`).emit('draft:bid', {
      amount,
      bidder: {
        id: member.id,
        teamName: member.team_name
      }
    });

    res.json({ success: true, amount });
  } catch (error) {
    console.error('Place bid error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Sell player (mark as sold)
router.post('/:draftId/sell', auth, async (req, res) => {
  try {
    const { draftId } = req.params;
    const io = req.app.get('io');

    // Get draft
    const draftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE id = $1',
      [draftId]
    );

    if (draftResult.rows.length === 0) {
      return res.status(404).json({ error: 'Draft not found' });
    }

    const draft = draftResult.rows[0];

    if (!draft.current_bidder_id) {
      return res.status(400).json({ error: 'No winning bid' });
    }

    // Get member (winning bidder)
    const memberResult = await pool.query(
      'SELECT * FROM league_members WHERE id = $1',
      [draft.current_bidder_id]
    );

    const member = memberResult.rows[0];

    // Update budget
    await pool.query(
      'UPDATE league_members SET budget_remaining = budget_remaining - $1 WHERE id = $2',
      [draft.current_bid, member.id]
    );

    // Get team
    const teamResult = await pool.query(
      'SELECT * FROM teams WHERE league_id = $1 AND user_id = $2',
      [draft.league_id, member.user_id]
    );

    const team = teamResult.rows[0];

    // Add player to team
    await pool.query(
      'INSERT INTO team_players (team_id, player_id, purchase_price) VALUES ($1, $2, $3)',
      [team.id, draft.current_player_id, draft.current_bid]
    );

    // Get next player
    const nextPlayerResult = await pool.query(
      `SELECT p.* FROM players p
       WHERE NOT EXISTS (
         SELECT 1 FROM team_players tp
         JOIN teams t ON tp.team_id = t.id
         WHERE tp.player_id = p.id AND t.league_id = $2
       )
       AND p.id != $3
       ORDER BY p.base_price DESC
       LIMIT 1`,
      [draft.league_id, draft.current_player_id]
    );

    let nextPlayer = null;
    let newBid = 0;

    if (nextPlayerResult.rows.length > 0) {
      nextPlayer = nextPlayerResult.rows[0];
      newBid = parseFloat(nextPlayer.base_price);
      
      // Update draft with next player
      await pool.query(
        `UPDATE auction_drafts 
         SET current_player_id = $1, current_bid = $2, current_bidder_id = NULL, timer_seconds = 60, updated_at = CURRENT_TIMESTAMP 
         WHERE id = $3`,
        [nextPlayer.id, newBid, draftId]
      );
    } else {
      // Draft complete
      await pool.query(
        `UPDATE auction_drafts SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
        [draftId]
      );

      await pool.query(
        "UPDATE leagues SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
        [draft.league_id]
      );
    }

    // Broadcast sold
    io.to(`league-${draft.league_id}`).emit('draft:sold', {
      playerId: draft.current_player_id,
      soldTo: member.team_name,
      amount: parseFloat(draft.current_bid),
      nextPlayer: nextPlayer ? {
        id: nextPlayer.id,
        name: nextPlayer.name,
        role: nextPlayer.role,
        team: nextPlayer.team,
        basePrice: parseFloat(nextPlayer.base_price)
      } : null,
      newBid
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Sell player error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Mark player unsold
router.post('/:draftId/unsold', auth, async (req, res) => {
  try {
    const { draftId } = req.params;
    const io = req.app.get('io');

    // Get draft
    const draftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE id = $1',
      [draftId]
    );

    const draft = draftResult.rows[0];

    // Get next player
    const nextPlayerResult = await pool.query(
      `SELECT p.* FROM players p
       WHERE NOT EXISTS (
         SELECT 1 FROM team_players tp
         JOIN teams t ON tp.team_id = t.id
         WHERE tp.player_id = p.id AND t.league_id = $2
       )
       AND p.id != $3
       ORDER BY p.base_price DESC
       LIMIT 1`,
      [draft.league_id, draft.current_player_id]
    );

    let nextPlayer = null;
    let newBid = 0;

    if (nextPlayerResult.rows.length > 0) {
      nextPlayer = nextPlayerResult.rows[0];
      newBid = parseFloat(nextPlayer.base_price);
      
      await pool.query(
        `UPDATE auction_drafts 
         SET current_player_id = $1, current_bid = $2, current_bidder_id = NULL, timer_seconds = 60, updated_at = CURRENT_TIMESTAMP 
         WHERE id = $3`,
        [nextPlayer.id, newBid, draftId]
      );
    } else {
      await pool.query(
        `UPDATE auction_drafts SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
        [draftId]
      );

      await pool.query(
        "UPDATE leagues SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
        [draft.league_id]
      );
    }

    // Broadcast unsold
    io.to(`league-${draft.league_id}`).emit('draft:unsold', {
      playerId: draft.current_player_id,
      nextPlayer: nextPlayer ? {
        id: nextPlayer.id,
        name: nextPlayer.name,
        role: nextPlayer.role,
        team: nextPlayer.team,
        basePrice: parseFloat(nextPlayer.base_price)
      } : null,
      newBid
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Mark unsold error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
