const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { body, validationResult } = require('express-validator');
const database = require('../db/pool');
const log = require('../middleware/logger');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'ipl-fantasy-secret-key-2026';

const validate = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ error: 'Validation failed', details: errors.array() });
  }
  next();
};

// Generate token
const generateToken = (user) => {
  return jwt.sign({ id: user.id, email: user.email }, JWT_SECRET);
};

// Register
router.post('/register', [
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 6 }),
  body('displayName').trim().isLength({ min: 2, max: 50 }),
  validate
], async (req, res) => {
  try {
    const { email, password, displayName } = req.body;

    const existing = await database.query('SELECT id FROM users WHERE email = $1', [email]);
    if (existing.rows.length > 0) {
      return res.status(400).json({ error: 'Email already registered' });
    }

    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    const result = await database.query(
      `INSERT INTO users (email, password_hash, display_name) VALUES ($1, $2, $3) 
       RETURNING id, email, display_name`,
      [email, passwordHash, displayName]
    );

    const user = result.rows[0];
    const token = generateToken(user);
    log.userAction(user.id, 'register');

    res.status(201).json({ token, user: { id: user.id, email: user.email, displayName: user.display_name } });
  } catch (error) {
    log.error('Register error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Login
router.post('/login', [
  body('email').isEmail().normalizeEmail(),
  body('password').notEmpty(),
  validate
], async (req, res) => {
  try {
    const { email, password } = req.body;

    const result = await database.query('SELECT * FROM users WHERE email = $1', [email]);
    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const user = result.rows[0];
    const isMatch = await bcrypt.compare(password, user.password_hash);
    if (!isMatch) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = generateToken(user);
    log.userAction(user.id, 'login');
    res.json({ token, user: { id: user.id, email: user.email, displayName: user.display_name, avatarUrl: user.avatar_url } });
  } catch (error) {
    log.error('Login error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Google Sign In
router.post('/google', [
  body('idToken').notEmpty(),
  validate
], async (req, res) => {
  try {
    const { idToken } = req.body;

    // In production, verify with Google:
    // const ticket = await client.verifyIdToken({ idToken, audience: CLIENT_ID });
    // const payload = ticket.getPayload();

    // For now, decode token (mock - in production use Google OAuth library)
    // This is a simplified version - real implementation would verify with Google
    let payload;
    try {
      const parts = idToken.split('.');
      if (parts.length !== 3) throw new Error('Invalid token format');
      payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
    } catch (e) {
      return res.status(400).json({ error: 'Invalid Google token' });
    }

    const { email, name, picture } = payload;

    // Find or create user
    let user = await database.query('SELECT * FROM users WHERE email = $1', [email]);

    if (user.rows.length === 0) {
      // Create new user
      const displayName = name || email.split('@')[0];
      const result = await database.query(
        `INSERT INTO users (email, display_name, avatar_url, auth_provider) 
         VALUES ($1, $2, $3, 'google') RETURNING id, email, display_name, avatar_url`,
        [email, displayName, picture]
      );
      user = result;
      log.userAction(user.rows[0].id, 'google_register');
    } else {
      log.userAction(user.rows[0].id, 'google_login');
    }

    const token = generateToken(user.rows[0]);
    res.json({ 
      token, 
      user: { 
        id: user.rows[0].id, 
        email: user.rows[0].email, 
        displayName: user.rows[0].display_name, 
        avatarUrl: user.rows[0].avatar_url 
      } 
    });
  } catch (error) {
    log.error('Google auth error', { error: error.message });
    res.status(500).json({ error: 'Google authentication failed' });
  }
});

// Apple Sign In
router.post('/apple', [
  body('idToken').notEmpty(),
  validate
], async (req, res) => {
  try {
    const { idToken, fullName } = req.body;

    // In production, verify with Apple:
    // const payload = await verifyAppleIdToken(idToken);

    // Decode token (simplified)
    let payload;
    try {
      const parts = idToken.split('.');
      if (parts.length !== 3) throw new Error('Invalid token format');
      payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
    } catch (e) {
      return res.status(400).json({ error: 'Invalid Apple token' });
    }

    const email = payload.email;

    // Apple may not provide email on subsequent logins
    // Use sub (subject) as unique identifier
    const appleId = payload.sub;

    let user = await database.query('SELECT * FROM users WHERE apple_id = $1', [appleId]);

    if (user.rows.length === 0 && email) {
      // Try by email
      user = await database.query('SELECT * FROM users WHERE email = $1', [email]);
    }

    if (user.rows.length === 0) {
      // Create new user
      const displayName = fullName || 'Apple User';
      const result = await database.query(
        `INSERT INTO users (email, display_name, apple_id, auth_provider) 
         VALUES ($1, $2, $3, 'apple') RETURNING id, email, display_name`,
        [email || `${appleId}@apple.com`, displayName, appleId]
      );
      user = result;
      log.userAction(user.rows[0].id, 'apple_register');
    } else {
      log.userAction(user.rows[0].id, 'apple_login');
    }

    const token = generateToken(user.rows[0]);
    res.json({ 
      token, 
      user: { 
        id: user.rows[0].id, 
        email: user.rows[0].email, 
        displayName: user.rows[0].display_name, 
        avatarUrl: user.rows[0].avatar_url 
      } 
    });
  } catch (error) {
    log.error('Apple auth error', { error: error.message });
    res.status(500).json({ error: 'Apple authentication failed' });
  }
});

// Get current user
router.get('/me', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token' });

    let decoded;
    try {
      decoded = jwt.verify(token, JWT_SECRET);
    } catch {
      return res.status(401).json({ error: 'Invalid token' });
    }

    const result = await database.query(
      'SELECT id, email, display_name, avatar_url, created_at FROM users WHERE id = $1',
      [decoded.id]
    );

    if (result.rows.length === 0) return res.status(404).json({ error: 'User not found' });

    const user = result.rows[0];
    res.json({ id: user.id, email: user.email, displayName: user.display_name, avatarUrl: user.avatar_url });
  } catch (error) {
    log.error('Get me error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Update profile
router.put('/profile', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token' });

    let decoded;
    try {
      decoded = jwt.verify(token, JWT_SECRET);
    } catch {
      return res.status(401).json({ error: 'Invalid token' });
    }

    const { displayName, avatarUrl } = req.body;

    const result = await database.query(
      `UPDATE users SET display_name = COALESCE($1, display_name), avatar_url = COALESCE($2, avatar_url), updated_at = NOW() 
       WHERE id = $3 RETURNING id, email, display_name, avatar_url`,
      [displayName, avatarUrl, decoded.id]
    );

    const user = result.rows[0];
    res.json({ id: user.id, email: user.email, displayName: user.display_name, avatarUrl: user.avatar_url });
  } catch (error) {
    log.error('Update profile error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
