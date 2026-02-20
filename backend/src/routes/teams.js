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

// Get user's team in a league
router.get('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    const teamResult = await pool.query(
      'SELECT * FROM teams WHERE league_id = $1 AND user_id = $2',
      [leagueId, req.userId]
    );

    if (teamResult.rows.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }

    const team = teamResult.rows[0];

    // Get players
    const playersResult = await pool.query(
      `SELECT tp.*, p.name, p.role, p.team, p.base_price, p.image_url
       FROM team_players tp
       JOIN players p ON tp.player_id = p.id
       WHERE tp.team_id = $1`,
      [team.id]
    );

    const players = playersResult.rows.map(p => ({
      id: p.player_id,
      name: p.name,
      role: p.role,
      team: p.team,
      basePrice: parseFloat(p.base_price),
      imageUrl: p.image_url,
      purchasePrice: parseFloat(p.purchase_price),
      isPlaying: p.is_playing,
      isCaptain: p.is_captain,
      isViceCaptain: p.is_vice_captain
    }));

    res.json({
      id: team.id,
      name: team.name,
      captainId: team.captain_id,
      viceCaptainId: team.vice_captain_id,
      totalPoints: team.total_points,
      players,
      budgetRemaining: 0 // Calculate from league_members
    });
  } catch (error) {
    console.error('Get team error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Update captain/vice-captain
router.put('/:teamId/captain', auth, async (req, res) => {
  try {
    const { teamId } = req.params;
    const { captainId, viceCaptainId } = req.body;

    // Verify ownership
    const teamResult = await pool.query(
      'SELECT * FROM teams WHERE id = $1 AND user_id = $2',
      [teamId, req.userId]
    );

    if (teamResult.rows.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }

    // Update captains
    await pool.query(
      `UPDATE team_players SET is_captain = FALSE, is_vice_captain = FALSE WHERE team_id = $1`,
      [teamId]
    );

    if (captainId) {
      await pool.query(
        'UPDATE team_players SET is_captain = TRUE WHERE team_id = $1 AND player_id = $2',
        [teamId, captainId]
      );
    }

    if (viceCaptainId) {
      await pool.query(
        'UPDATE team_players SET is_vice_captain = TRUE WHERE team_id = $1 AND player_id = $2',
        [teamId, viceCaptainId]
      );
    }

    // Update team
    await pool.query(
      'UPDATE teams SET captain_id = $1, vice_captain_id = $2, updated_at = CURRENT_TIMESTAMP WHERE id = $3',
      [captainId, viceCaptainId, teamId]
    );

    res.json({ success: true });
  } catch (error) {
    console.error('Update captain error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Set playing XI
router.put('/:teamId/lineup', auth, async (req, res) => {
  try {
    const { teamId } = req.params;
    const { playingIds } = req.body;

    // Verify ownership
    const teamResult = await pool.query(
      'SELECT * FROM teams WHERE id = $1 AND user_id = $2',
      [teamId, req.userId]
    );

    if (teamResult.rows.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }

    // Reset all
    await pool.query(
      'UPDATE team_players SET is_playing = FALSE WHERE team_id = $1',
      [teamId]
    );

    // Set playing
    for (const playerId of playingIds) {
      await pool.query(
        'UPDATE team_players SET is_playing = TRUE WHERE team_id = $1 AND player_id = $2',
        [teamId, playerId]
      );
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Update lineup error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get all teams in league
router.get('/league/:leagueId/all', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    const result = await pool.query(
      `SELECT t.*, u.display_name, u.avatar_url
       FROM teams t
       JOIN users u ON t.user_id = u.id
       WHERE t.league_id = $1
       ORDER BY t.total_points DESC`,
      [leagueId]
    );

    const teams = result.rows.map(t => ({
      id: t.id,
      name: t.name,
      userId: t.user_id,
      displayName: t.display_name,
      avatarUrl: t.avatar_url,
      totalPoints: t.total_points,
      captainId: t.captain_id,
      viceCaptainId: t.vice_captain_id
    }));

    res.json(teams);
  } catch (error) {
    console.error('Get all teams error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
