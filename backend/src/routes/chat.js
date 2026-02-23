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

// Verify user is a member of the league
const verifyLeagueMember = async (leagueId, userId) => {
  const result = await pool.query(
    'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
    [leagueId, userId]
  );
  return result.rows.length > 0;
};

// Get chat messages for league
router.get('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { limit = 50, before } = req.query;

    // Verify user is a member
    const isMember = await verifyLeagueMember(leagueId, req.userId);
    if (!isMember) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    let query = `
      SELECT m.id, m.message, m.message_type, m.created_at,
             u.id as user_id, u.display_name, u.avatar_url
      FROM league_chat_messages m
      JOIN users u ON m.user_id = u.id
      WHERE m.league_id = $1
    `;
    
    const params = [leagueId];
    
    if (before) {
      query += ' AND m.created_at < $2';
      params.push(before);
    }
    
    query += ' ORDER BY m.created_at DESC LIMIT $' + (params.length + 1);
    params.push(parseInt(limit));

    const result = await pool.query(query, params);

    // Get reactions for these messages
    const messageIds = result.rows.map(row => row.id);
    let reactionsMap = {};
    
    if (messageIds.length > 0) {
      const reactionsResult = await pool.query(
        `SELECT cr.message_id, cr.emoji, u.display_name, u.id as user_id
         FROM chat_reactions cr
         JOIN users u ON cr.user_id = u.id
         WHERE cr.message_id = ANY($1)`,
        [messageIds]
      );
      
      reactionsResult.rows.forEach(r => {
        if (!reactionsMap[r.message_id]) {
          reactionsMap[r.message_id] = [];
        }
        reactionsMap[r.message_id].push({
          emoji: r.emoji,
          userId: r.user_id,
          displayName: r.display_name
        });
      });
    }

    const messages = result.rows.map(row => ({
      id: row.id,
      message: row.message,
      messageType: row.message_type,
      timestamp: row.created_at,
      user: {
        id: row.user_id,
        displayName: row.display_name,
        avatarUrl: row.avatar_url
      },
      reactions: reactionsMap[row.id] || []
    }));

    res.json(messages.reverse());
  } catch (error) {
    console.error('Get messages error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Send message to league
router.post('/league/:leagueId', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;
    const { text, messageType = 'text' } = req.body;

    if (!text?.trim()) {
      return res.status(400).json({ error: 'Message cannot be empty' });
    }

    // Verify user is a member
    const isMember = await verifyLeagueMember(leagueId, req.userId);
    if (!isMember) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    // Validate message type
    const validTypes = ['text', 'announcement', 'system'];
    if (!validTypes.includes(messageType)) {
      return res.status(400).json({ error: 'Invalid message type' });
    }

    // Get user info
    const userResult = await pool.query(
      'SELECT display_name, avatar_url FROM users WHERE id = $1',
      [req.userId]
    );
    
    const user = userResult.rows[0];

    // Store message in database
    const messageResult = await pool.query(
      `INSERT INTO league_chat_messages (league_id, user_id, message, message_type) 
       VALUES ($1, $2, $3, $4) 
       RETURNING *`,
      [leagueId, req.userId, text.trim(), messageType]
    );

    const message = messageResult.rows[0];

    // Broadcast to league room via Socket.IO
    const io = req.app.get('io');
    io.to(`league-${leagueId}`).emit('chat:message', {
      id: message.id,
      leagueId,
      message: message.message,
      messageType: message.message_type,
      timestamp: message.created_at,
      user: {
        id: req.userId,
        displayName: user.display_name,
        avatarUrl: user.avatar_url
      },
      reactions: []
    });

    res.json({ 
      success: true, 
      message: {
        id: message.id,
        message: message.message,
        messageType: message.message_type,
        timestamp: message.created_at,
        user: {
          id: req.userId,
          displayName: user.display_name,
          avatarUrl: user.avatar_url
        },
        reactions: []
      }
    });
  } catch (error) {
    console.error('Send message error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// React to a message
router.post('/message/:messageId/react', auth, async (req, res) => {
  try {
    const { messageId } = req.params;
    const { emoji } = req.body;

    if (!emoji) {
      return res.status(400).json({ error: 'Emoji is required' });
    }

    // Get the message to find the league
    const messageResult = await pool.query(
      'SELECT league_id, user_id FROM league_chat_messages WHERE id = $1',
      [messageId]
    );

    if (messageResult.rows.length === 0) {
      return res.status(404).json({ error: 'Message not found' });
    }

    const message = messageResult.rows[0];
    const leagueId = message.league_id;

    // Verify user is a member
    const isMember = await verifyLeagueMember(leagueId, req.userId);
    if (!isMember) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    // Add or update reaction
    await pool.query(
      `INSERT INTO chat_reactions (message_id, user_id, emoji)
       VALUES ($1, $2, $3)
       ON CONFLICT (message_id, user_id, emoji) DO NOTHING`,
      [messageId, req.userId, emoji]
    );

    // Get updated reactions
    const reactionsResult = await pool.query(
      `SELECT cr.emoji, u.id as user_id, u.display_name
       FROM chat_reactions cr
       JOIN users u ON cr.user_id = u.id
       WHERE cr.message_id = $1`,
      [messageId]
    );

    const reactions = reactionsResult.rows.map(r => ({
      emoji: r.emoji,
      userId: r.user_id,
      displayName: r.display_name
    }));

    // Broadcast reaction update
    const io = req.app.get('io');
    io.to(`league-${leagueId}`).emit('chat:reaction', {
      messageId,
      reactions
    });

    res.json({ success: true, reactions });
  } catch (error) {
    console.error('React to message error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Remove reaction from a message
router.delete('/message/:messageId/react', auth, async (req, res) => {
  try {
    const { messageId } = req.params;
    const { emoji } = req.query;

    if (!emoji) {
      return res.status(400).json({ error: 'Emoji is required' });
    }

    // Get the message to find the league
    const messageResult = await pool.query(
      'SELECT league_id FROM league_chat_messages WHERE id = $1',
      [messageId]
    );

    if (messageResult.rows.length === 0) {
      return res.status(404).json({ error: 'Message not found' });
    }

    const leagueId = messageResult.rows[0].league_id;

    // Remove reaction
    await pool.query(
      'DELETE FROM chat_reactions WHERE message_id = $1 AND user_id = $2 AND emoji = $3',
      [messageId, req.userId, emoji]
    );

    // Get updated reactions
    const reactionsResult = await pool.query(
      `SELECT cr.emoji, u.id as user_id, u.display_name
       FROM chat_reactions cr
       JOIN users u ON cr.user_id = u.id
       WHERE cr.message_id = $1`,
      [messageId]
    );

    const reactions = reactionsResult.rows.map(r => ({
      emoji: r.emoji,
      userId: r.user_id,
      displayName: r.display_name
    }));

    // Broadcast reaction update
    const io = req.app.get('io');
    io.to(`league-${leagueId}`).emit('chat:reaction', {
      messageId,
      reactions
    });

    res.json({ success: true, reactions });
  } catch (error) {
    console.error('Remove reaction error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Delete a message (only by message author or league commissioner)
router.delete('/message/:messageId', auth, async (req, res) => {
  try {
    const { messageId } = req.params;

    // Get the message
    const messageResult = await pool.query(
      'SELECT * FROM league_chat_messages WHERE id = $1',
      [messageId]
    );

    if (messageResult.rows.length === 0) {
      return res.status(404).json({ error: 'Message not found' });
    }

    const message = messageResult.rows[0];

    // Check if user is the author or commissioner
    const isAuthor = message.user_id === req.userId;
    
    const leagueResult = await pool.query(
      'SELECT commissioner_id FROM leagues WHERE id = $1',
      [message.league_id]
    );
    
    const isCommissioner = leagueResult.rows.length > 0 && 
                           leagueResult.rows[0].commissioner_id === req.userId;

    if (!isAuthor && !isCommissioner) {
      return res.status(403).json({ error: 'Not authorized to delete this message' });
    }

    // Delete message (cascades to reactions)
    await pool.query('DELETE FROM league_chat_messages WHERE id = $1', [messageId]);

    // Broadcast deletion
    const io = req.app.get('io');
    io.to(`league-${message.league_id}`).emit('chat:deleted', {
      messageId
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Delete message error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get online users in league chat
router.get('/league/:leagueId/online', auth, async (req, res) => {
  try {
    const { leagueId } = req.params;

    // Verify user is a member
    const isMember = await verifyLeagueMember(leagueId, req.userId);
    if (!isMember) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    // This would be tracked via Socket.IO rooms in production
    // For now, return an empty list - frontend would track via socket
    res.json([]);
  } catch (error) {
    console.error('Get online users error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
