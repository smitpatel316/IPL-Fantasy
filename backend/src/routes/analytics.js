const express = require('express');
const jwt = require('jsonwebtoken');
const { pool } = require('../db/pool');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'ipl-fantasy-secret-key-2026';

// Middleware
const auth = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token' });
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.id;
    next();
  } catch { res.status(401).json({ error: 'Invalid token' }); }
};

// Get analytics for user
router.get('/user', auth, async (req, res) => {
  try {
    // Get user's overall stats
    const statsResult = await pool.query(`
      SELECT 
        COUNT(DISTINCT lm.league_id) as total_leagues,
        COUNT(DISTINCT t.id) as total_teams,
        COALESCE(SUM(t.total_points), 0) as total_points,
        MAX(t.total_points) as best_points
      FROM league_members lm
      LEFT JOIN teams t ON t.league_id = lm.league_id AND t.user_id = lm.user_id
      WHERE lm.user_id = $1
    `, [req.userId]);

    const stats = statsResult.rows[0];

    // Get performance over time
    const historyResult = await pool.query(`
      SELECT 
        DATE_TRUNC('week', ws.created_at) as week,
        SUM(ws.points) as points,
        SUM(ws.category_wins) as wins,
        SUM(ws.category_losses) as losses
      FROM weekly_scores ws
      JOIN teams t ON ws.team_id = t.id
      WHERE t.user_id = $1
      GROUP BY DATE_TRUNC('week', ws.created_at)
      ORDER BY week DESC
      LIMIT 12
    `, [req.userId]);

    // Get achievements
    const achievementsResult = await pool.query(`
      SELECT award_type, created_at
      FROM season_awards
      WHERE winner_team_id IN (
        SELECT id FROM teams WHERE user_id = $1
      )
      ORDER BY created_at DESC
    `, [req.userId]);

    res.json({
      stats: {
        totalLeagues: parseInt(stats.total_leagues) || 0,
        totalTeams: parseInt(stats.total_teams) || 0,
        totalPoints: parseInt(stats.total_points) || 0,
        bestPoints: parseInt(stats.best_points) || 0
      },
      history: historyResult.rows,
      achievements: achievementsResult.rows
    });
  } catch (error) {
    console.error('Get analytics error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get league analytics
router.get('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    // League overview
    const overviewResult = await pool.query(`
      SELECT 
        l.name,
        l.status,
        COUNT(DISTINCT lm.id) as member_count,
        COUNT(DISTINCT t.id) as team_count
      FROM leagues l
      LEFT JOIN league_members lm ON lm.league_id = l.id
      LEFT JOIN teams t ON t.league_id = l.id
      WHERE l.id = $1
      GROUP BY l.id
    `, [leagueId]);

    // Points distribution
    const pointsResult = await pool.query(`
      SELECT 
        t.name,
        t.total_points,
        ROW_NUMBER() OVER (ORDER BY t.total_points DESC) as rank
      FROM teams t
      WHERE t.league_id = $1
      ORDER BY t.total_points DESC
    `, [leagueId]);

    // Category leaders
    const categoryLeaders = await pool.query(`
      SELECT 
        tp.player_id,
        p.name as player_name,
        p.role,
        SUM(pp.points) as total_points,
        SUM(pp.runs) as total_runs,
        SUM(pp.wickets) as total_wickets
      FROM team_players tp
      JOIN teams t ON tp.team_id = t.id
      JOIN players p ON tp.player_id = p.id
      LEFT JOIN player_points pp ON pp.player_id = p.id
      WHERE t.league_id = $1
      GROUP BY tp.player_id, p.name, p.role
      ORDER BY total_points DESC
      LIMIT 10
    `, [leagueId]);

    res.json({
      overview: overviewResult.rows[0],
      standings: pointsResult.rows,
      categoryLeaders: categoryLeaders.rows
    });
  } catch (error) {
    console.error('Get league analytics error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get matchup history
router.get('/matchup/:leagueId/:teamId', auth, async (req, res) => {
  try {
    const { leagueId, teamId } = req.params;

    const result = await pool.query(`
      SELECT 
        m.week,
        m.home_team_id,
        m.away_team_id,
        m.home_points,
        m.away_points,
        m.home_wins,
        m.away_wins,
        m.is_completed,
        ht.name as home_team,
        at.name as away_team
      FROM matchups m
      JOIN teams ht ON m.home_team_id = ht.id
      JOIN teams at ON m.away_team_id = at.id
      WHERE m.league_id = $1 AND (m.home_team_id = $2 OR m.away_team_id = $2)
      ORDER BY m.week DESC
    `, [leagueId, teamId]);

    res.json(result.rows);
  } catch (error) {
    console.error('Get matchup history error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
