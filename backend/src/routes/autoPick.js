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

// Get auto-pick settings for a league
router.get('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    const result = await pool.query(
      `SELECT * FROM auto_pick_settings 
       WHERE user_id = $1 AND league_id = $2`,
      [req.userId, leagueId]
    );

    if (result.rows.length === 0) {
      // Return default settings
      return res.json({
        isEnabled: false,
        favoritePlayers: [],
        preferredRoles: [],
        maxPrice: 100.00,
        autoBidEnabled: false,
        autoBidIncrement: 1.00
      });
    }

    const settings = result.rows[0];
    
    // Get player details for favorite players
    let favoritePlayersDetails = [];
    if (settings.favorite_players && settings.favorite_players.length > 0) {
      const playersResult = await pool.query(
        `SELECT id, name, role, team, base_price FROM players WHERE id = ANY($1)`,
        [settings.favorite_players]
      );
      favoritePlayersDetails = playersResult.rows.map(p => ({
        id: p.id,
        name: p.name,
        role: p.role,
        team: p.team,
        basePrice: parseFloat(p.base_price)
      }));
    }

    res.json({
      id: settings.id,
      isEnabled: settings.is_enabled,
      favoritePlayers: favoritePlayersDetails,
      favoritePlayerIds: settings.favorite_players || [],
      preferredRoles: settings.preferred_roles || [],
      maxPrice: parseFloat(settings.max_price),
      autoBidEnabled: settings.auto_bid_enabled,
      autoBidIncrement: parseFloat(settings.auto_bid_increment)
    });
  } catch (error) {
    console.error('Get auto-pick settings error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Save auto-pick settings
router.post('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { 
      isEnabled, 
      favoritePlayers, 
      favoritePlayerIds,
      preferredRoles, 
      maxPrice, 
      autoBidEnabled, 
      autoBidIncrement 
    } = req.body;

    // Verify user is a member of the league
    const memberResult = await pool.query(
      'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
      [leagueId, req.userId]
    );

    if (memberResult.rows.length === 0) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    // Handle both array of IDs and array of player objects
    let playerIds = favoritePlayerIds || [];
    if (favoritePlayers && favoritePlayers.length > 0 && typeof favoritePlayers[0] === 'object') {
      playerIds = favoritePlayers.map(p => p.id);
    }

    const result = await pool.query(
      `INSERT INTO auto_pick_settings 
       (user_id, league_id, is_enabled, favorite_players, preferred_roles, max_price, auto_bid_enabled, auto_bid_increment)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       ON CONFLICT (user_id, league_id) 
       DO UPDATE SET 
         is_enabled = $3,
         favorite_players = $4,
         preferred_roles = $5,
         max_price = $6,
         auto_bid_enabled = $7,
         auto_bid_increment = $8,
         updated_at = CURRENT_TIMESTAMP
       RETURNING *`,
      [
        req.userId, 
        leagueId, 
        isEnabled || false, 
        playerIds || [], 
        preferredRoles || [], 
        maxPrice || 100.00, 
        autoBidEnabled || false, 
        autoBidIncrement || 1.00
      ]
    );

    const settings = result.rows[0];

    // Get player details for favorite players
    let favoritePlayersDetails = [];
    if (settings.favorite_players && settings.favorite_players.length > 0) {
      const playersResult = await pool.query(
        `SELECT id, name, role, team, base_price FROM players WHERE id = ANY($1)`,
        [settings.favorite_players]
      );
      favoritePlayersDetails = playersResult.rows.map(p => ({
        id: p.id,
        name: p.name,
        role: p.role,
        team: p.team,
        basePrice: parseFloat(p.base_price)
      }));
    }

    res.json({
      id: settings.id,
      isEnabled: settings.is_enabled,
      favoritePlayers: favoritePlayersDetails,
      favoritePlayerIds: settings.favorite_players || [],
      preferredRoles: settings.preferred_roles || [],
      maxPrice: parseFloat(settings.max_price),
      autoBidEnabled: settings.auto_bid_enabled,
      autoBidIncrement: parseFloat(settings.auto_bid_increment)
    });
  } catch (error) {
    console.error('Save auto-pick settings error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get all auto-pick settings for a user (across leagues)
router.get('/', auth, async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT aps.*, l.name as league_name 
       FROM auto_pick_settings aps 
       JOIN leagues l ON aps.league_id = l.id 
       WHERE aps.user_id = $1`,
      [req.userId]
    );

    res.json(result.rows.map(settings => ({
      id: settings.id,
      leagueId: settings.league_id,
      leagueName: settings.league_name,
      isEnabled: settings.is_enabled,
      favoritePlayers: settings.favorite_players || [],
      preferredRoles: settings.preferred_roles || [],
      maxPrice: parseFloat(settings.max_price),
      autoBidEnabled: settings.auto_bid_enabled,
      autoBidIncrement: parseFloat(settings.auto_bid_increment)
    })));
  } catch (error) {
    console.error('Get all auto-pick settings error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Trigger auto-pick for current player (called when timer expires)
router.post('/league/:leagueId/trigger', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { draftId, playerId } = req.body;
    const io = req.app.get('io');

    // Get auto-pick settings
    const settingsResult = await pool.query(
      'SELECT * FROM auto_pick_settings WHERE user_id = $1 AND league_id = $2 AND is_enabled = true',
      [req.userId, leagueId]
    );

    if (settingsResult.rows.length === 0) {
      return res.status(400).json({ error: 'Auto-pick not enabled' });
    }

    const settings = settingsResult.rows[0];

    // Get current player info
    const playerResult = await pool.query(
      'SELECT * FROM players WHERE id = $1',
      [playerId]
    );

    if (playerResult.rows.length === 0) {
      return res.status(404).json({ error: 'Player not found' });
    }

    const player = playerResult.rows[0];

    // Check if player matches preferences
    const isFavorite = settings.favorite_players.includes(playerId);
    const isPreferredRole = settings.preferred_roles.length === 0 || 
      settings.preferred_roles.includes(player.role);
    const withinBudget = parseFloat(player.base_price) <= parseFloat(settings.max_price);

    // Determine if we should auto-pick/bid
    let shouldAutoPick = isFavorite || (isPreferredRole && withinBudget);

    if (!shouldAutoPick) {
      return res.json({
        autoPickTriggered: false,
        reason: 'Player does not match preferences'
      });
    }

    // Get user's member record
    const memberResult = await pool.query(
      'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
      [leagueId, req.userId]
    );

    if (memberResult.rows.length === 0) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    const member = memberResult.rows[0];

    // Calculate auto-bid amount
    let bidAmount = parseFloat(player.base_price);
    if (settings.auto_bid_enabled) {
      // Get current bid for the player
      const draftResult = await pool.query(
        'SELECT current_bid, current_bidder_id FROM auction_drafts WHERE id = $1',
        [draftId]
      );

      if (draftResult.rows.length > 0) {
        const currentBid = parseFloat(draftResult.rows[0].current_bid);
        const currentBidderId = draftResult.rows[0].current_bidder_id;

        // If someone else is bidding, auto-bid higher
        if (currentBidderId && currentBidderId !== member.id) {
          bidAmount = currentBid + parseFloat(settings.auto_bid_increment);
        } else if (!currentBidderId) {
          bidAmount = parseFloat(player.base_price);
        }
      }
    }

    // Check budget
    if (parseFloat(member.budget_remaining) < bidAmount) {
      return res.json({
        autoPickTriggered: false,
        reason: 'Insufficient budget'
      });
    }

    // Place the bid
    await pool.query(
      `UPDATE auction_drafts 
       SET current_bid = $1, current_bidder_id = $2, timer_seconds = 60, updated_at = CURRENT_TIMESTAMP 
       WHERE id = $3`,
      [bidAmount, member.id, draftId]
    );

    // Broadcast auto-bid to all clients
    io.to(`league-${leagueId}`).emit('draft:autoBid', {
      amount: bidAmount,
      bidder: {
        id: member.id,
        teamName: member.team_name,
        displayName: member.display_name
      },
      isAutoPick: true
    });

    res.json({
      autoPickTriggered: true,
      playerId,
      bidAmount,
      reason: isFavorite ? 'Favorite player' : 'Matches preferences'
    });
  } catch (error) {
    console.error('Trigger auto-pick error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
