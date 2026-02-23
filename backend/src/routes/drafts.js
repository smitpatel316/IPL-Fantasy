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

// Get draft type for a specific draft
router.get('/:draftId/type', auth, async (req, res) => {
  try {
    const { draftId } = req.params;

    const result = await pool.query(
      'SELECT id, draft_type, status FROM auction_drafts WHERE id = $1',
      [draftId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Draft not found' });
    }

    res.json({ 
      id: result.rows[0].id,
      draftType: result.rows[0].draft_type || 'auction',
      status: result.rows[0].status
    });
  } catch (error) {
    console.error('Get draft type error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Set draft type for a specific draft
router.post('/:draftId/type', auth, async (req, res) => {
  try {
    const { draftId } = req.params;
    const { draftType } = req.body;

    // Validate draft type
    if (!['auction', 'snake'].includes(draftType)) {
      return res.status(400).json({ error: 'Invalid draft type' });
    }

    const result = await pool.query(
      'UPDATE auction_drafts SET draft_type = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2 RETURNING *',
      [draftType, draftId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Draft not found' });
    }

    res.json({ 
      id: result.rows[0].id,
      draftType: result.rows[0].draft_type,
      status: result.rows[0].status
    });
  } catch (error) {
    console.error('Set draft type error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get draft type for a league
router.get('/league/:leagueId/type', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    const result = await pool.query(
      'SELECT draft_type FROM auction_drafts WHERE league_id = $1 ORDER BY created_at DESC LIMIT 1',
      [leagueId]
    );

    if (result.rows.length === 0) {
      return res.json({ draftType: 'auction' });
    }

    res.json({ draftType: result.rows[0].draft_type || 'auction' });
  } catch (error) {
    console.error('Get draft type error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Set draft type for a league (before starting)
router.post('/league/:leagueId/type', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { draftType } = req.body; // 'auction' or 'snake'

    // Validate draft type
    if (!['auction', 'snake'].includes(draftType)) {
      return res.status(400).json({ error: 'Invalid draft type. Must be "auction" or "snake"' });
    }

    // Verify commissioner
    const leagueResult = await pool.query(
      'SELECT * FROM leagues WHERE id = $1 AND commissioner_id = $2',
      [leagueId, req.userId]
    );

    if (leagueResult.rows.length === 0) {
      return res.status(403).json({ error: 'Only commissioner can set draft type' });
    }

    // Check if draft already exists
    const existingDraft = await pool.query(
      'SELECT id, status FROM auction_drafts WHERE league_id = $1 ORDER BY created_at DESC LIMIT 1',
      [leagueId]
    );

    if (existingDraft.rows.length > 0 && existingDraft.rows[0].status !== 'completed') {
      return res.status(400).json({ error: 'Cannot change draft type while draft is in progress' });
    }

    // Create new draft with type
    const draftResult = await pool.query(
      `INSERT INTO auction_drafts (league_id, draft_type, status, current_pick_number) 
       VALUES ($1, $2, 'pending', 0) 
       RETURNING *`,
      [leagueId, draftType]
    );

    // If snake draft, generate pick order
    if (draftType === 'snake') {
      const membersResult = await pool.query(
        'SELECT id FROM league_members WHERE league_id = $1 ORDER BY joined_at ASC',
        [leagueId]
      );

      const members = membersResult.rows;
      const totalRounds = 15; // Typical fantasy team size
      let pickNumber = 1;

      for (let round = 1; round <= totalRounds; round++) {
        // Snake order: even rounds go forward, odd rounds go reverse
        const isForward = round % 2 === 1;
        
        for (let position = 0; position < members.length; position++) {
          const teamPosition = isForward ? position : (members.length - 1 - position);
          
          await pool.query(
            `INSERT INTO snake_picks (draft_id, pick_number, round, team_position, is_drafting)
             VALUES ($1, $2, $3, $4, $5)`,
            [draftResult.rows[0].id, pickNumber, round, teamPosition, pickNumber === 1]
          );
          
          pickNumber++;
        }
      }

      // Set first pick as drafting
      await pool.query(
        `UPDATE snake_picks SET is_drafting = TRUE 
         WHERE draft_id = $1 AND pick_number = 1`,
        [draftResult.rows[0].id]
      );
    }

    res.json({
      id: draftResult.rows[0].id,
      draftType: draftResult.rows[0].draft_type,
      status: draftResult.rows[0].status
    });
  } catch (error) {
    console.error('Set draft type error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get snake draft picks
router.get('/league/:leagueId/picks', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    // Get the active draft
    const draftResult = await pool.query(
      `SELECT ad.*, lm.user_id as commissioner_id FROM auction_drafts ad 
       JOIN leagues l ON ad.league_id = l.id 
       WHERE ad.league_id = $1 AND ad.draft_type = 'snake' 
       ORDER BY ad.created_at DESC LIMIT 1`,
      [leagueId]
    );

    if (draftResult.rows.length === 0) {
      return res.json({ picks: [], currentPick: null });
    }

    const draft = draftResult.rows[0];

    // Get all picks with member info
    const picksResult = await pool.query(
      `SELECT sp.*, lm.team_name, u.display_name, p.name as player_name, p.role as player_role, p.team as player_team
       FROM snake_picks sp
       LEFT JOIN league_members lm ON sp.league_member_id = lm.id
       LEFT JOIN users u ON lm.user_id = u.id
       LEFT JOIN players p ON sp.player_id = p.id
       WHERE sp.draft_id = $1
       ORDER BY sp.pick_number`,
      [draft.id]
    );

    // Get current pick
    const currentPickResult = await pool.query(
      `SELECT sp.*, lm.team_name, u.display_name
       FROM snake_picks sp
       LEFT JOIN league_members lm ON sp.league_member_id = lm.id
       LEFT JOIN users u ON lm.user_id = u.id
       WHERE sp.draft_id = $1 AND sp.is_drafting = TRUE`,
      [draft.id]
    );

    // Get available players (not drafted)
    const availablePlayersResult = await pool.query(
      `SELECT p.* FROM players p
       WHERE NOT EXISTS (
         SELECT 1 FROM snake_picks sp
         JOIN auction_drafts ad ON sp.draft_id = ad.id
         WHERE sp.player_id = p.id AND ad.league_id = $1 AND ad.draft_type = 'snake'
       )
       ORDER BY p.base_price DESC`,
      [leagueId]
    );

    res.json({
      draftId: draft.id,
      draftStatus: draft.status,
      currentPickNumber: draft.current_pick_number,
      currentPick: currentPickResult.rows.length > 0 ? currentPickResult.rows[0] : null,
      picks: picksResult.rows,
      availablePlayers: availablePlayersResult.rows
    });
  } catch (error) {
    console.error('Get snake picks error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Make a snake draft pick
router.post('/:draftId/pick', auth, async (req, res) => {
  try {
    const { draftId } = req.params;
    const { playerId } = req.body;
    const io = req.app.get('io');

    // Get draft
    const draftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE id = $1 AND draft_type = $2',
      [draftId, 'snake']
    );

    if (draftResult.rows.length === 0) {
      return res.status(404).json({ error: 'Snake draft not found' });
    }

    const draft = draftResult.rows[0];

    if (draft.status !== 'active') {
      return res.status(400).json({ error: 'Draft is not active' });
    }

    // Get current pick
    const currentPickResult = await pool.query(
      'SELECT * FROM snake_picks WHERE draft_id = $1 AND is_drafting = TRUE',
      [draftId]
    );

    if (currentPickResult.rows.length === 0) {
      return res.status(400).json({ error: 'No active pick' });
    }

    const currentPick = currentPickResult.rows[0];

    // Verify it's this user's turn
    const memberResult = await pool.query(
      'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
      [draft.league_id, req.userId]
    );

    if (memberResult.rows.length === 0) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    const member = memberResult.rows[0];

    // Check if it's this member's turn
    const isTheirTurn = currentPick.league_member_id === member.id || !currentPick.league_member_id;
    
    // If no one assigned yet, assign to current user
    if (!currentPick.league_member_id) {
      // Get the team position for this pick
      const positionResult = await pool.query(
        'SELECT team_position FROM snake_picks WHERE id = $1',
        [currentPick.id]
      );
      
      const teamPosition = positionResult.rows[0].team_position;
      
      // Find the member at this position
      const membersOrdered = await pool.query(
        'SELECT id FROM league_members WHERE league_id = $1 ORDER BY joined_at ASC',
        [draft.league_id]
      );
      
      if (membersOrdered.rows[teamPosition] && membersOrdered.rows[teamPosition].id !== member.id) {
        return res.status(403).json({ 
          error: `Not your turn. Waiting for ${membersOrdered.rows[teamPosition].team_name}` 
        });
      }
    }

    // Verify player is available
    const playerCheckResult = await pool.query(
      `SELECT p.* FROM players p
       WHERE p.id = $1 AND NOT EXISTS (
         SELECT 1 FROM snake_picks sp
         WHERE sp.player_id = p.id AND sp.draft_id = $2
       )`,
      [playerId, draftId]
    );

    if (playerCheckResult.rows.length === 0) {
      return res.status(400).json({ error: 'Player not available' });
    }

    // Update pick with player
    await pool.query(
      `UPDATE snake_picks 
       SET player_id = $1, is_drafting = FALSE, updated_at = CURRENT_TIMESTAMP 
       WHERE id = $2`,
      [playerId, currentPick.id]
    );

    // Get next pick
    const nextPickResult = await pool.query(
      'SELECT * FROM snake_picks WHERE draft_id = $1 AND pick_number = $2',
      [draftId, currentPick.pick_number + 1]
    );

    if (nextPickResult.rows.length > 0) {
      // Mark next pick as drafting
      await pool.query(
        `UPDATE snake_picks SET is_drafting = TRUE, updated_at = CURRENT_TIMESTAMP 
         WHERE id = $1`,
        [nextPickResult.rows[0].id]
      );

      // Update draft current pick number
      await pool.query(
        `UPDATE auction_drafts 
         SET current_pick_number = $1, current_player_id = $2, updated_at = CURRENT_TIMESTAMP 
         WHERE id = $3`,
        [nextPickResult.rows[0].pick_number, playerId, draftId]
      );

      // Broadcast pick made
      const player = playerCheckResult.rows[0];
      io.to(`league-${draft.league_id}`).emit('draft:pick', {
        pickNumber: currentPick.pick_number,
        playerId: player.id,
        playerName: player.name,
        playerRole: player.role,
        playerTeam: player.team,
        nextPickNumber: nextPickResult.rows[0].pick_number,
        nextPickTeamPosition: nextPickResult.rows[0].team_position
      });
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

      const player = playerCheckResult.rows[0];
      io.to(`league-${draft.league_id}`).emit('draft:pick', {
        pickNumber: currentPick.pick_number,
        playerId: player.id,
        playerName: player.name,
        playerRole: player.role,
        playerTeam: player.team,
        nextPickNumber: null,
        isComplete: true
      });
    }

    // Add player to team
    const teamResult = await pool.query(
      'SELECT * FROM teams WHERE league_id = $1 AND user_id = $2',
      [draft.league_id, req.userId]
    );

    if (teamResult.rows.length > 0) {
      await pool.query(
        'INSERT INTO team_players (team_id, player_id, purchase_price) VALUES ($1, $2, $3)',
        [teamResult.rows[0].id, playerId, playerCheckResult.rows[0].base_price]
      );
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Make pick error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Skip pick (auto-pick for user who hasn't picked)
router.post('/:draftId/skip-pick', auth, async (req, res) => {
  try {
    const { draftId } = req.params;
    const io = req.app.get('io');

    const draftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE id = $1 AND draft_type = $2',
      [draftId, 'snake']
    );

    if (draftResult.rows.length === 0) {
      return res.status(404).json({ error: 'Snake draft not found' });
    }

    const draft = draftResult.rows[0];

    // Get current pick
    const currentPickResult = await pool.query(
      'SELECT * FROM snake_picks WHERE draft_id = $1 AND is_drafting = TRUE',
      [draftId]
    );

    if (currentPickResult.rows.length === 0) {
      return res.status(400).json({ error: 'No active pick' });
    }

    const currentPick = currentPickResult.rows[0];

    // Get next pick
    const nextPickResult = await pool.query(
      'SELECT * FROM snake_picks WHERE draft_id = $1 AND pick_number = $2',
      [draftId, currentPick.pick_number + 1]
    );

    // Mark current as skipped
    await pool.query(
      `UPDATE snake_picks SET is_drafting = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
      [currentPick.id]
    );

    if (nextPickResult.rows.length > 0) {
      await pool.query(
        `UPDATE snake_picks SET is_drafting = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
        [nextPickResult.rows[0].id]
      );

      await pool.query(
        `UPDATE auction_drafts SET current_pick_number = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2`,
        [nextPickResult.rows[0].pick_number, draftId]
      );

      io.to(`league-${draft.league_id}`).emit('draft:skipped', {
        pickNumber: currentPick.pick_number,
        nextPickNumber: nextPickResult.rows[0].pick_number
      });
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Skip pick error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

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
      draftType: draft.draft_type || 'auction',
      status: draft.status,
      currentPlayer,
      currentBid: parseFloat(draft.current_bid),
      currentBidder,
      currentPickNumber: draft.current_pick_number,
      timerSeconds: draft.timer_seconds,
      createdAt: draft.created_at
    });
  } catch (error) {
    console.error('Get draft error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Start auction draft (or snake draft)
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

    // Check for existing draft (created via /type endpoint)
    const existingDraftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE league_id = $1 AND status = $2 ORDER BY created_at DESC LIMIT 1',
      [leagueId, 'pending']
    );

    let draftType = 'auction';
    let draftId = null;

    if (existingDraftResult.rows.length > 0) {
      // Use existing draft with type
      draftType = existingDraftResult.rows[0].draft_type || 'auction';
      draftId = existingDraftResult.rows[0].id;
    }

    // For snake draft, just activate it
    if (draftType === 'snake') {
      await pool.query(
        `UPDATE auction_drafts SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
        [draftId]
      );

      await pool.query(
        "UPDATE leagues SET status = 'drafting', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
        [leagueId]
      );

      // Get current pick info
      const currentPickResult = await pool.query(
        `SELECT sp.*, lm.team_name FROM snake_picks sp
         LEFT JOIN league_members lm ON sp.league_member_id = lm.id
         WHERE sp.draft_id = $1 AND sp.is_drafting = TRUE`,
        [draftId]
      );

      const currentPick = currentPickResult.rows[0] || null;

      // Get available players
      const availablePlayersResult = await pool.query(
        `SELECT p.* FROM players p
         WHERE NOT EXISTS (
           SELECT 1 FROM snake_picks sp WHERE sp.player_id = p.id AND sp.draft_id = $1
         )
         ORDER BY p.base_price DESC`,
        [draftId]
      );

      io.to(`league-${leagueId}`).emit('draft:started', {
        draftId,
        draftType: 'snake',
        currentPickNumber: currentPick?.pick_number || 1,
        currentPick: currentPick,
        availablePlayers: availablePlayersResult.rows.map(p => ({
          id: p.id,
          name: p.name,
          role: p.role,
          team: p.team,
          basePrice: parseFloat(p.base_price)
        }))
      });

      return res.json({
        id: draftId,
        draftType: 'snake',
        status: 'active',
        currentPickNumber: currentPick?.pick_number || 1
      });
    }

    // Default to auction draft
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
    let draftResult;
    if (draftId) {
      // Update existing pending draft
      await pool.query(
        `UPDATE auction_drafts 
         SET status = 'active', current_player_id = $1, current_bid = $2, updated_at = CURRENT_TIMESTAMP 
         WHERE id = $3`,
        [playersResult.rows[0].id, playersResult.rows[0].base_price, draftId]
      );
      
      draftResult = await pool.query('SELECT * FROM auction_drafts WHERE id = $1', [draftId]);
    } else {
      draftResult = await pool.query(
        `INSERT INTO auction_drafts (league_id, draft_type, status, current_player_id, current_bid) 
         VALUES ($1, 'auction', 'active', $2, $3) 
         RETURNING *`,
        [leagueId, playersResult.rows[0].id, playersResult.rows[0].base_price]
      );
    }

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
      draftType: 'auction',
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
      draftType: 'auction',
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

// Handle timer expiration and trigger auto-pick if enabled
router.post('/league/:leagueId/timer-expired', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { draftId, playerId } = req.body;
    const io = req.app.get('io');

    // Get the draft
    const draftResult = await pool.query(
      'SELECT * FROM auction_drafts WHERE id = $1 AND league_id = $2',
      [draftId, leagueId]
    );

    if (draftResult.rows.length === 0) {
      return res.status(404).json({ error: 'Draft not found' });
    }

    const draft = draftResult.rows[0];

    // Get all league members who have auto-pick enabled
    const autoPickResult = await pool.query(
      `SELECT aps.*, lm.user_id, lm.team_name, lm.display_name, lm.budget_remaining
       FROM auto_pick_settings aps
       JOIN league_members lm ON aps.user_id = lm.user_id AND aps.league_id = lm.league_id
       WHERE aps.league_id = $1 AND aps.is_enabled = true`,
      [leagueId]
    );

    if (autoPickResult.rows.length === 0) {
      // No auto-pick enabled, just move to next player
      return res.json({ 
        autoPickTriggered: false, 
        action: 'no_auto_pick' 
      });
    }

    // Get player info
    const playerResult = await pool.query(
      'SELECT * FROM players WHERE id = $1',
      [playerId]
    );

    if (playerResult.rows.length === 0) {
      return res.status(404).json({ error: 'Player not found' });
    }

    const player = playerResult.rows[0];
    let autoPickTriggered = false;
    let triggeredMember = null;
    let bidAmount = parseFloat(player.base_price);

    // Check each auto-pick user to see if they want this player
    for (const settings of autoPickResult.rows) {
      const isFavorite = settings.favorite_players.includes(playerId);
      const isPreferredRole = settings.preferred_roles.length === 0 || 
        settings.preferred_roles.includes(player.role);
      const withinBudget = parseFloat(player.base_price) <= parseFloat(settings.max_price);

      const shouldAutoPick = isFavorite || (isPreferredRole && withinBudget);

      if (shouldAutoPick) {
        // Check if someone else is already bidding
        const currentBid = parseFloat(draft.current_bid || 0);
        const currentBidderId = draft.current_bidder_id;

        // Calculate bid amount
        if (settings.auto_bid_enabled && currentBidderId && currentBidderId !== settings.id) {
          bidAmount = currentBid + parseFloat(settings.auto_bid_increment);
        } else {
          bidAmount = parseFloat(player.base_price);
        }

        // Check budget
        if (parseFloat(settings.budget_remaining) >= bidAmount) {
          autoPickTriggered = true;
          triggeredMember = {
            id: settings.id,
            userId: settings.user_id,
            teamName: settings.team_name,
            displayName: settings.display_name,
            bidAmount,
            reason: isFavorite ? 'favorite' : 'matches_preferences'
          };

          // Update draft with auto-bid
          await pool.query(
            `UPDATE auction_drafts 
             SET current_bid = $1, current_bidder_id = $2, timer_seconds = 60, updated_at = CURRENT_TIMESTAMP 
             WHERE id = $3`,
            [bidAmount, settings.id, draftId]
          );

          // Broadcast auto-bid to all clients
          io.to(`league-${leagueId}`).emit('draft:autoBid', {
            draftId,
            playerId,
            amount: bidAmount,
            bidder: {
              id: settings.id,
              teamName: settings.team_name,
              displayName: settings.display_name
            },
            isAutoPick: true,
            reason: triggeredMember.reason
          });

          break;
        }
      }
    }

    if (!autoPickTriggered) {
      // No one auto-picked, check if there's a current bid that should stick
      if (!draft.current_bidder_id) {
        // Mark player as unsold
        // Get next player
        const nextPlayerResult = await pool.query(
          `SELECT p.* FROM players p
           WHERE p.team_id = (SELECT team_id FROM auction_drafts WHERE id = $1)
           AND p.id NOT IN (SELECT player_id FROM auction_drafts WHERE id = $1 AND player_id IS NOT NULL)
           ORDER BY p.base_price DESC LIMIT 1`,
          [draftId]
        );

        const nextPlayer = nextPlayerResult.rows[0] || null;

        // Mark current player unsold
        await pool.query(
          `UPDATE auction_drafts 
           SET current_player_id = $1, current_bid = 0, current_bidder_id = NULL, timer_seconds = 60, updated_at = CURRENT_TIMESTAMP 
           WHERE id = $2`,
          [nextPlayer?.id || null, draftId]
        );

        // Broadcast unsold
        io.to(`league-${leagueId}`).emit('draft:unsold', {
          playerId,
          nextPlayer: nextPlayer ? {
            id: nextPlayer.id,
            name: nextPlayer.name,
            role: nextPlayer.role,
            team: nextPlayer.team,
            basePrice: parseFloat(nextPlayer.base_price)
          } : null
        });
      }
    }

    res.json({ 
      autoPickTriggered,
      triggeredMember: triggeredMember || null,
      action: autoPickTriggered ? 'auto_bid' : 'no_bid'
    });
  } catch (error) {
    console.error('Timer expired error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
