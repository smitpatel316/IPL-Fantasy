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

// Get trades for user's leagues
router.get('/', auth, async (req, res) => {
  try {
    // Would query trades table in production
    res.json([]);
  } catch (error) {
    console.error('Get trades error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Propose trade
router.post('/propose', auth, async (req, res) => {
  try {
    const { leagueId, offeredPlayerIds, requestedPlayerIds, offeredCash = 0, requestedCash = 0 } = req.body;
    const io = req.app.get('io');
    
    // In production, would insert into trades table
    // Broadcast to league
    io.to(`league-${leagueId}`).emit('trade:proposed', {
      id: Date.now().toString(),
      fromUserId: req.userId,
      offeredPlayerIds,
      requestedPlayerIds,
      offeredCash,
      requestedCash
    });
    
    res.json({ success: true });
  } catch (error) {
    console.error('Propose trade error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Accept trade
router.post('/:tradeId/accept', auth, async (req, res) => {
  try {
    const { tradeId } = req.params;
    const io = req.app.get('io');
    
    // In production, would update trade status and swap players
    res.json({ success: true });
  } catch (error) {
    console.error('Accept trade error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Reject trade
router.post('/:tradeId/reject', auth, async (req, res) => {
  try {
    const { tradeId } = req.params;
    res.json({ success: true });
  } catch (error) {
    console.error('Reject trade error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
