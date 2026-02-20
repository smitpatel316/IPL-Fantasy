const express = require('express');
const { pool } = require('../db/pool');

const router = express.Router();

// Get all players
router.get('/', async (req, res) => {
  try {
    const { team, role, search } = req.query;
    
    let query = 'SELECT * FROM players WHERE 1=1';
    const params = [];
    let paramIndex = 1;

    if (team) {
      query += ` AND team = $${paramIndex}`;
      params.push(team);
      paramIndex++;
    }

    if (role) {
      query += ` AND role = $${paramIndex}`;
      params.push(role);
      paramIndex++;
    }

    if (search) {
      query += ` AND name ILIKE $${paramIndex}`;
      params.push(`%${search}%`);
      paramIndex++;
    }

    query += ' ORDER BY base_price DESC, name ASC';

    const result = await pool.query(query, params);

    const players = result.rows.map(p => ({
      id: p.id,
      name: p.name,
      role: p.role,
      team: p.team,
      basePrice: parseFloat(p.base_price),
      imageUrl: p.image_url,
      isOverseas: p.is_overseas
    }));

    res.json(players);
  } catch (error) {
    console.error('Get players error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get player by ID
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;

    const result = await pool.query(
      'SELECT * FROM players WHERE id = $1',
      [id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Player not found' });
    }

    const p = result.rows[0];
    res.json({
      id: p.id,
      name: p.name,
      role: p.role,
      team: p.team,
      basePrice: parseFloat(p.base_price),
      imageUrl: p.image_url,
      isOverseas: p.is_overseas
    });
  } catch (error) {
    console.error('Get player error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get player stats
router.get('/:id/stats', async (req, res) => {
  try {
    const { id } = req.params;

    // Get all-time stats from player_points
    const result = await pool.query(
      `SELECT 
        SUM(points) as total_points,
        SUM(runs) as total_runs,
        SUM(wickets) as total_wickets,
        SUM(catches) as total_catches,
        COUNT(*) as matches_played
       FROM player_points 
       WHERE player_id = $1`,
      [id]
    );

    const stats = result.rows[0];
    res.json({
      totalPoints: parseInt(stats.total_points) || 0,
      totalRuns: parseInt(stats.total_runs) || 0,
      totalWickets: parseInt(stats.total_wickets) || 0,
      totalCatches: parseInt(stats.total_catches) || 0,
      matchesPlayed: parseInt(stats.matches_played) || 0
    });
  } catch (error) {
    console.error('Get player stats error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get players by team
router.get('/team/:team', async (req, res) => {
  try {
    const { team } = req.params;

    const result = await pool.query(
      'SELECT * FROM players WHERE team = $1 ORDER BY base_price DESC',
      [team.toUpperCase()]
    );

    const players = result.rows.map(p => ({
      id: p.id,
      name: p.name,
      role: p.role,
      team: p.team,
      basePrice: parseFloat(p.base_price),
      imageUrl: p.image_url,
      isOverseas: p.is_overseas
    }));

    res.json(players);
  } catch (error) {
    console.error('Get team players error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get all teams
router.get('/meta/teams', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT DISTINCT team FROM players ORDER BY team'
    );

    const teams = result.rows.map(r => r.team);
    res.json(teams);
  } catch (error) {
    console.error('Get teams error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get all roles
router.get('/meta/roles', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT DISTINCT role FROM players ORDER BY role'
    );

    const roles = result.rows.map(r => r.role);
    res.json(roles);
  } catch (error) {
    console.error('Get roles error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
