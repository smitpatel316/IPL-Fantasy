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

// Get chat messages for league
router.get('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { limit = 50 } = req.query;

    // In production, would have a chat_messages table
    // For now, return empty array
    res.json([]);
  } catch (error) {
    console.error('Get messages error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Send message to league
router.post('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { text } = req.body;

    if (!text?.trim()) {
      return res.status(400).json({ error: 'Message cannot be empty' });
    }

    // In production, would insert into chat_messages table
    const io = req.app.get('io');
    
    // Broadcast to league room
    io.to(`league-${leagueId}`).emit('chat:message', {
      id: Date.now().toString(),
      leagueId,
      userId: req.userId,
      text: text.trim(),
      timestamp: new Date().toISOString()
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Send message error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
