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

// Get standings for league
router.get('/league/:leagueId/standings', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    const result = await pool.query(
      `SELECT t.*, u.display_name, lm.team_name
       FROM teams t
       JOIN users u ON t.user_id = u.id
       JOIN league_members lm ON t.league_id = lm.league_id AND t.user_id = lm.user_id
       WHERE t.league_id = $1
       ORDER BY t.total_points DESC`,
      [leagueId]
    );

    // Calculate W-L-T from matchups
    const standings = await Promise.all(result.rows.map(async (team) => {
      const matchupsResult = await pool.query(
        `SELECT * FROM matchups 
         WHERE league_id = $1 AND (home_team_id = $2 OR away_team_id = $2)`,
        [leagueId, team.id]
      );

      let wins = 0, losses = 0, ties = 0;
      let categoriesWon = 0, categoriesLost = 0;

      matchupsResult.rows.forEach(m => {
        if (m.is_completed) {
          const isHome = m.home_team_id === team.id;
          const teamPoints = isHome ? m.home_points : m.away_points;
          const opponentPoints = isHome ? m.away_points : m.home_points;
          
          if (teamPoints > opponentPoints) wins++;
          else if (teamPoints < opponentPoints) losses++;
          else ties++;

          categoriesWon += isHome ? m.home_wins : m.away_wins;
          categoriesLost += isHome ? m.away_wins : m.home_wins;
        }
      });

      return {
        id: team.id,
        name: team.name,
        userId: team.user_id,
        displayName: team.display_name,
        totalPoints: team.total_points,
        wins,
        losses,
        ties,
        categoriesWon,
        categoriesLost
      };
    }));

    // Sort by points
    standings.sort((a, b) => b.totalPoints - a.totalPoints);

    res.json(standings);
  } catch (error) {
    console.error('Get standings error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get current matchup for user
router.get('/league/:leagueId/current', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    // Get user's team
    const teamResult = await pool.query(
      'SELECT id FROM teams WHERE league_id = $1 AND user_id = $2',
      [leagueId, req.userId]
    );

    if (teamResult.rows.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }

    const teamId = teamResult.rows[0].id;

    // Get current week matchup
    const matchupResult = await pool.query(
      `SELECT * FROM matchups 
       WHERE league_id = $1 AND is_completed = FALSE
       AND (home_team_id = $2 OR away_team_id = $2)
       ORDER BY week ASC LIMIT 1`,
      [leagueId, teamId]
    );

    if (matchupResult.rows.length === 0) {
      return res.json(null);
    }

    const matchup = matchupResult.rows[0];

    // Get team details
    const homeTeamResult = await pool.query(
      'SELECT t.*, u.display_name FROM teams t JOIN users u ON t.user_id = u.id WHERE t.id = $1',
      [matchup.home_team_id]
    );

    const awayTeamResult = await pool.query(
      'SELECT t.*, u.display_name FROM teams t JOIN users u ON t.user_id = u.id WHERE t.id = $1',
      [matchup.away_team_id]
    );

    const homeTeam = homeTeamResult.rows[0];
    const awayTeam = awayTeamResult.rows[0];

    // Get category breakdown
    const categories = [
      { name: 'Total Points', homeValue: matchup.home_points, awayValue: matchup.away_points },
      { name: 'Boundaries', homeValue: 0, awayValue: 0 }, // Would need real data
      { name: 'Wickets', homeValue: 0, awayValue: 0 },
      { name: 'Catches', homeValue: 0, awayValue: 0 },
    ];

    res.json({
      id: matchup.id,
      week: matchup.week,
      homeTeam: {
        id: homeTeam.id,
        name: homeTeam.name,
        displayName: homeTeam.display_name,
        points: matchup.home_points
      },
      awayTeam: {
        id: awayTeam.id,
        name: awayTeam.name,
        displayName: awayTeam.display_name,
        points: matchup.away_points
      },
      categories,
      isCompleted: matchup.is_completed
    });
  } catch (error) {
    console.error('Get current matchup error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get matchup details
router.get('/matchup/:matchupId', auth, async (req, res) => {
  try {
    const { matchupId } = req.params;

    const matchupResult = await pool.query(
      'SELECT * FROM matchups WHERE id = $1',
      [matchupId]
    );

    if (matchupResult.rows.length === 0) {
      return res.status(404).json({ error: 'Matchup not found' });
    }

    const matchup = matchupResult.rows[0];

    res.json({
      id: matchup.id,
      leagueId: matchup.league_id,
      week: matchup.week,
      homeTeamId: matchup.home_team_id,
      awayTeamId: matchup.away_team_id,
      homePoints: matchup.home_points,
      awayPoints: matchup.away_points,
      homeWins: matchup.home_wins,
      awayWins: matchup.away_wins,
      isCompleted: matchup.is_completed
    });
  } catch (error) {
    console.error('Get matchup error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get player's team points breakdown
router.get('/league/:leagueId/points', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    // Get user's team
    const teamResult = await pool.query(
      'SELECT id FROM teams WHERE league_id = $1 AND user_id = $2',
      [leagueId, req.userId]
    );

    if (teamResult.rows.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }

    const teamId = teamResult.rows[0].id;

    // Get player points
    const result = await pool.query(
      `SELECT tp.*, p.name, p.role, p.team, p.base_price,
              tp.is_captain, tp.is_vice_captain, tp.is_playing
       FROM team_players tp
       JOIN players p ON tp.player_id = p.id
       WHERE tp.team_id = $1`,
      [teamId]
    );

    const players = result.rows.map(p => {
      let multiplier = 1;
      if (p.is_captain) multiplier = 2;
      else if (p.is_vice_captain) multiplier = 1.5;

      // Mock points - in real app, would aggregate from player_points
      const basePoints = Math.floor(Math.random() * 100);
      const totalPoints = Math.floor(basePoints * multiplier);

      return {
        playerId: p.player_id,
        name: p.name,
        role: p.role,
        team: p.team,
        basePrice: parseFloat(p.base_price),
        isCaptain: p.is_captain,
        isViceCaptain: p.is_vice_captain,
        isPlaying: p.is_playing,
        basePoints,
        multiplier,
        totalPoints
      };
    });

    const totalPoints = players.reduce((sum, p) => sum + p.totalPoints, 0);

    res.json({
      teamId,
      totalPoints,
      players
    });
  } catch (error) {
    console.error('Get points error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
