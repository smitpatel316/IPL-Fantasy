const express = require('express');
const { pool } = require('../db/pool');
const axios = require('axios');
const NodeCache = require('node-cache');

const router = express.Router();

// Cache for live scores (30 seconds)
const scoresCache = new NodeCache({ stdTTL: 30 });

// Mock cricket API endpoint (in production, use real API like CricAPI)
const CRIC_API_URL = process.env.CRIC_API_URL || 'https://api.cricapi.com/v1';
const CRIC_API_KEY = process.env.CRIC_API_KEY;

// Get live matches
router.get('/live', async (req, res) => {
  try {
    // Check cache first
    const cached = scoresCache.get('live_matches');
    if (cached) {
      return res.json(cached);
    }
    
    // In production, fetch from real API:
    // const response = await axios.get(`${CRIC_API_URL}/matches?apikey=${CRIC_API_KEY}`);
    
    // Mock data for demonstration
    const liveMatches = [
      {
        id: 'match_1',
        league: 'IPL 2026',
        team1: { name: 'Mumbai Indians', abbr: 'MI', score: '145/3', overs: '14.2' },
        team2: { name: 'Chennai Super Kings', abbr: 'CSK', score: '0/0', overs: '0' },
        status: 'In Progress',
        requiredRunRate: 8.5,
        currentRunRate: 10.1,
        lastCommentary: 'Rohit hits a six! MI looking strong',
        startTime: new Date().toISOString()
      }
    ];
    
    // Cache the result
    scoresCache.set('live_matches', liveMatches);
    
    res.json(liveMatches);
  } catch (error) {
    console.error('Error fetching live matches:', error);
    res.status(500).json({ error: 'Failed to fetch live matches' });
  }
});

// Get upcoming matches
router.get('/upcoming', async (req, res) => {
  try {
    const upcomingMatches = [
      {
        id: 'match_2',
        league: 'IPL 2026',
        team1: { name: 'Royal Challengers Bangalore', abbr: 'RCB' },
        team2: { name: 'Kolkata Knight Riders', abbr: 'KKR' },
        status: 'Scheduled',
        startTime: new Date(Date.now() + 86400000).toISOString() // Tomorrow
      },
      {
        id: 'match_3',
        league: 'IPL 2026',
        team1: { name: 'Delhi Capitals', abbr: 'DC' },
        team2: { name: 'Sunrisers Hyderabad', abbr: 'SRH' },
        status: 'Scheduled',
        startTime: new Date(Date.now() + 172800000).toISOString() // Day after tomorrow
      }
    ];
    
    res.json(upcomingMatches);
  } catch (error) {
    console.error('Error fetching upcoming matches:', error);
    res.status(500).json({ error: 'Failed to fetch upcoming matches' });
  }
});

// Get completed matches
router.get('/completed', async (req, res) => {
  try {
    const completedMatches = [
      {
        id: 'match_4',
        league: 'IPL 2026',
        team1: { name: 'Gujarat Titans', abbr: 'GT', score: '180/6', overs: '20' },
        team2: { name: 'Rajasthan Royals', abbr: 'RR', score: '175/8', overs: '19.5' },
        status: 'Completed',
        winner: 'GT',
        result: 'GT won by 5 runs'
      }
    ];
    
    res.json(completedMatches);
  } catch (error) {
    console.error('Error fetching completed matches:', error);
    res.status(500).json({ error: 'Failed to fetch completed matches' });
  }
});

// Get match details
router.get('/:matchId', async (req, res) => {
  try {
    const { matchId } = req.params;
    
    // Fetch from cache or API
    const cacheKey = `match_${matchId}`;
    const cached = scoresCache.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }
    
    // Mock match details
    const matchDetails = {
      id: matchId,
      league: 'IPL 2026',
      team1: { 
        name: 'Mumbai Indians', 
        abbr: 'MI', 
        score: '145/3', 
        overs: '14.2',
        batsmen: [
          { name: 'Rohit Sharma', runs: 45, balls: 32, fours: 4, sixes: 2, strikeRate: 140.6 },
          { name: 'Suryakumar Yadav', runs: 38, balls: 25, fours: 5, sixes: 1, strikeRate: 152.0 }
        ]
      },
      team2: { 
        name: 'Chennai Super Kings', 
        abbr: 'CSK', 
        score: '0/0', 
        overs: '0',
        bowlers: []
      },
      status: 'In Progress',
      requiredRunRate: 8.5,
      currentRunRate: 10.1,
      lastCommentary: 'Rohit hits a six! MI looking strong',
      fallOfWickets: [
        { wicket: 1, score: 78, batsman: 'Ishan Kishan', over: '8.4' }
      ]
    };
    
    scoresCache.set(cacheKey, matchDetails, 60);
    res.json(matchDetails);
  } catch (error) {
    console.error('Error fetching match details:', error);
    res.status(500).json({ error: 'Failed to fetch match details' });
  }
});

// Webhook for external score updates (from cricket API)
router.post('/webhook', async (req, res) => {
  try {
    const { matchId, scores, commentary } = req.body;
    
    // Validate webhook signature in production
    // const signature = req.headers['x-webhook-signature'];
    
    // Update cache
    const cacheKey = `match_${matchId}`;
    const existing = scoresCache.get(cacheKey);
    
    if (existing) {
      // Update with new data
      const updated = { ...existing, ...scores, lastCommentary: commentary };
      scoresCache.set(cacheKey, updated);
      
      // Broadcast to connected clients
      const io = req.app.get('io');
      io.emit('match:update', { matchId, ...scores });
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error processing webhook:', error);
    res.status(500).json({ error: 'Failed to process update' });
  }
});

// Sync player points from match
router.post('/sync-points', async (req, res) => {
  try {
    const { matchId, playerStats } = req.body;
    
    // Update player_points table
    for (const stat of playerStats) {
      await pool.query(`
        INSERT INTO player_points 
          (player_id, match_id, points, runs, wickets, catches, strike_rate, economy)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (player_id, match_id) 
        DO UPDATE SET
          points = EXCLUDED.points,
          runs = EXCLUDED.runs,
          wickets = EXCLUDED.wickets,
          catches = EXCLUDED.catches,
          strike_rate = EXCLUDED.strike_rate,
          economy = EXCLUDED.economy
      `, [
        stat.playerId,
        matchId,
        stat.points,
        stat.runs,
        stat.wickets,
        stat.catches,
        stat.strikeRate,
        stat.economy
      ]);
    }
    
    // Recalculate team totals
    // This would trigger team point recalculation
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error syncing points:', error);
    res.status(500).json({ error: 'Failed to sync points' });
  }
});

module.exports = router;
