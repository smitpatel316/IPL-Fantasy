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

// Generate unique league code
const generateCode = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
};

// Get all leagues for user
router.get('/', auth, async (req, res) => {
  try {
    const result = await pool.query(
      `SELECT l.*, lm.team_name, lm.is_commissioner
       FROM leagues l
       JOIN league_members lm ON l.id = lm.league_id
       WHERE lm.user_id = $1
       ORDER BY l.created_at DESC`,
      [req.userId]
    );

    const leagues = result.rows.map(row => ({
      id: row.id,
      name: row.name,
      code: row.code,
      commissionerId: row.commissioner_id,
      maxTeams: row.max_teams,
      auctionBudget: parseFloat(row.auction_budget),
      status: row.status,
      members: [],
      createdAt: row.created_at,
      isCommissioner: row.is_commissioner,
      teamName: row.team_name
    }));

    // Get member count for each league
    for (let league of leagues) {
      const membersResult = await pool.query(
        'SELECT COUNT(*) FROM league_members WHERE league_id = $1',
        [league.id]
      );
      league.memberCount = parseInt(membersResult.rows[0].count);
    }

    res.json(leagues);
  } catch (error) {
    console.error('Get leagues error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Create league
router.post('/', auth, async (req, res) => {
  try {
    const { name, maxTeams = 10, auctionBudget = 100 } = req.body;

    const code = generateCode();

    const leagueResult = await pool.query(
      `INSERT INTO leagues (name, code, commissioner_id, max_teams, auction_budget) 
       VALUES ($1, $2, $3, $4, $5) 
       RETURNING *`,
      [name, code, req.userId, maxTeams, auctionBudget]
    );

    const league = leagueResult.rows[0];

    // Add creator as commissioner member
    await pool.query(
      `INSERT INTO league_members (league_id, user_id, team_name, is_commissioner, budget_remaining) 
       VALUES ($1, $2, $3, $4, $5)`,
      [league.id, req.userId, `${name} Team`, true, auctionBudget]
    );

    // Create team for commissioner
    await pool.query(
      `INSERT INTO teams (user_id, league_id, name) VALUES ($1, $2, $3)`,
      [req.userId, league.id, `${name} Team`]
    );

    res.status(201).json({
      id: league.id,
      name: league.name,
      code: league.code,
      commissionerId: league.commissioner_id,
      maxTeams: league.max_teams,
      auctionBudget: parseFloat(league.auction_budget),
      status: league.status,
      createdAt: league.created_at
    });
  } catch (error) {
    console.error('Create league error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Join league
router.post('/join', auth, async (req, res) => {
  try {
    const { code, teamName } = req.body;

    // Find league by code
    const leagueResult = await pool.query(
      'SELECT * FROM leagues WHERE code = $1',
      [code.toUpperCase()]
    );

    if (leagueResult.rows.length === 0) {
      return res.status(404).json({ error: 'League not found' });
    }

    const league = leagueResult.rows[0];

    // Check if league is full
    const memberCount = await pool.query(
      'SELECT COUNT(*) FROM league_members WHERE league_id = $1',
      [league.id]
    );

    if (parseInt(memberCount.rows[0].count) >= league.max_teams) {
      return res.status(400).json({ error: 'League is full' });
    }

    // Check if already a member
    const existingMember = await pool.query(
      'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
      [league.id, req.userId]
    );

    if (existingMember.rows.length > 0) {
      return res.status(400).json({ error: 'Already a member of this league' });
    }

    // Add user as member
    await pool.query(
      `INSERT INTO league_members (league_id, user_id, team_name, is_commissioner, budget_remaining) 
       VALUES ($1, $2, $3, $4, $5)`,
      [league.id, req.userId, teamName || `${league.name} Team`, false, league.auction_budget]
    );

    // Create team
    await pool.query(
      `INSERT INTO teams (user_id, league_id, name) VALUES ($1, $2, $3)`,
      [req.userId, league.id, teamName || `${league.name} Team`]
    );

    res.json({ message: 'Joined league successfully', leagueId: league.id });
  } catch (error) {
    console.error('Join league error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get league details
router.get('/:id', auth, async (req, res) => {
  try {
    const { id } = req.params;

    const leagueResult = await pool.query(
      'SELECT * FROM leagues WHERE id = $1',
      [id]
    );

    if (leagueResult.rows.length === 0) {
      return res.status(404).json({ error: 'League not found' });
    }

    const league = leagueResult.rows[0];

    // Get members
    const membersResult = await pool.query(
      `SELECT lm.*, u.email, u.display_name, u.avatar_url
       FROM league_members lm
       JOIN users u ON lm.user_id = u.id
       WHERE lm.league_id = $1`,
      [id]
    );

    const members = membersResult.rows.map(m => ({
      id: m.id,
      userId: m.user_id,
      teamName: m.team_name,
      isCommissioner: m.is_commissioner,
      budgetRemaining: parseFloat(m.budget_remaining),
      joinedAt: m.joined_at,
      user: {
        email: m.email,
        displayName: m.display_name,
        avatarUrl: m.avatar_url
      }
    }));

    res.json({
      id: league.id,
      name: league.name,
      code: league.code,
      commissionerId: league.commissioner_id,
      maxTeams: league.max_teams,
      auctionBudget: parseFloat(league.auction_budget),
      status: league.status,
      createdAt: league.created_at,
      members
    });
  } catch (error) {
    console.error('Get league error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Update league status (commissioner only)
router.put('/:id/status', auth, async (req, res) => {
  try {
    const { id } = req.params;
    const { status } = req.body;

    // Check if commissioner
    const leagueResult = await pool.query(
      'SELECT * FROM leagues WHERE id = $1 AND commissioner_id = $2',
      [id, req.userId]
    );

    if (leagueResult.rows.length === 0) {
      return res.status(403).json({ error: 'Only commissioner can update status' });
    }

    await pool.query(
      'UPDATE leagues SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2',
      [status, id]
    );

    res.json({ message: 'Status updated' });
  } catch (error) {
    console.error('Update status error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
