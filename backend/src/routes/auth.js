const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { body, validationResult } = require('express-validator');
const crypto = require('crypto');
const database = require('../db/pool');
const log = require('../middleware/logger');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'ipl-fantasy-secret-key-2026';
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'refresh-secret-2026';

// Validation
const validate = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ error: 'Validation failed', details: errors.array() });
  }
  next();
};

// Generate tokens
const generateTokens = (user) => {
  const accessToken = jwt.sign(
    { id: user.id, email: user.email },
    JWT_SECRET,
    { expiresIn: '1h' } // 1 hour access token
  );

  const refreshToken = jwt.sign(
    { id: user.id, type: 'refresh' },
    JWT_REFRESH_SECRET,
    { expiresIn: '30d' } // 30 days refresh token
  );

  return { accessToken, refreshToken };
};

// Register
router.post('/register', [
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 8 }).withMessage('Password must be at least 8 characters'),
  body('displayName').trim().isLength({ min: 2, max: 50 }),
  validate
], async (req, res) => {
  try {
    const { email, password, displayName } = req.body;

    // Check if user exists
    const existingUser = await database.query(
      'SELECT id FROM users WHERE email = $1',
      [email]
    );

    if (existingUser.rows.length > 0) {
      log.security('Registration attempt with existing email', { email });
      return res.status(400).json({ error: 'Email already registered' });
    }

    // Hash password
    const salt = await bcrypt.genSalt(12);
    const passwordHash = await bcrypt.hash(password, salt);

    // Create user
    const result = await database.query(
      `INSERT INTO users (email, password_hash, display_name) 
       VALUES ($1, $2, $3) 
       RETURNING id, email, display_name, created_at`,
      [email, passwordHash, displayName]
    );

    const user = result.rows[0];
    const tokens = generateTokens(user);

    // Save refresh token
    await database.query(
      'UPDATE users SET refresh_token = $1, refresh_token_expires = NOW() + INTERVAL \'7 days\' WHERE id = $2',
      [tokens.refreshToken, user.id]
    );

    log.userAction(user.id, 'register');

    res.status(201).json({
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      user: {
        id: user.id,
        email: user.email,
        displayName: user.display_name,
        createdAt: user.created_at
      }
    });
  } catch (error) {
    log.error('Registration error', { error: error.message });
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

    // Find user
    const result = await database.query(
      'SELECT * FROM users WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      log.security('Login attempt with invalid email', { email });
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const user = result.rows[0];

    // Check password
    const isMatch = await bcrypt.compare(password, user.password_hash);
    if (!isMatch) {
      log.security('Login attempt with invalid password', { userId: user.id });
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Generate tokens
    const tokens = generateTokens(user);

    // Save refresh token
    await database.query(
      'UPDATE users SET refresh_token = $1, refresh_token_expires = NOW() + INTERVAL \'7 days\' WHERE id = $2',
      [tokens.refreshToken, user.id]
    );

    log.userAction(user.id, 'login');

    res.json({
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      user: {
        id: user.id,
        email: user.email,
        displayName: user.display_name,
        avatarUrl: user.avatar_url,
        createdAt: user.created_at
      }
    });
  } catch (error) {
    log.error('Login error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Refresh token
router.post('/refresh', [
  body('refreshToken').notEmpty(),
  validate
], async (req, res) => {
  try {
    const { refreshToken } = req.body;

    // Verify refresh token
    let decoded;
    try {
      decoded = jwt.verify(refreshToken, JWT_REFRESH_SECRET);
    } catch {
      return res.status(401).json({ error: 'Invalid refresh token' });
    }

    // Find user with matching token
    const result = await database.query(
      'SELECT * FROM users WHERE id = $1 AND refresh_token = $2 AND refresh_token_expires > NOW()',
      [decoded.id, refreshToken]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'Refresh token expired or invalid' });
    }

    const user = result.rows[0];
    const tokens = generateTokens(user);

    // Rotate refresh token
    await database.query(
      'UPDATE users SET refresh_token = $1, refresh_token_expires = NOW() + INTERVAL \'7 days\' WHERE id = $2',
      [tokens.refreshToken, user.id]
    );

    log.userAction(user.id, 'token_refresh');

    res.json({
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken
    });
  } catch (error) {
    log.error('Token refresh error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Logout
router.post('/logout', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    // Verify token to get user ID
    let decoded;
    try {
      decoded = jwt.verify(token, JWT_SECRET);
    } catch {
      return res.status(401).json({ error: 'Invalid token' });
    }

    // Clear refresh token
    await database.query(
      'UPDATE users SET refresh_token = NULL, refresh_token_expires = NULL WHERE id = $1',
      [decoded.id]
    );

    log.userAction(decoded.id, 'logout');

    res.json({ message: 'Logged out successfully' });
  } catch (error) {
    log.error('Logout error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Get current user
router.get('/me', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

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

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    const user = result.rows[0];
    res.json({
      id: user.id,
      email: user.email,
      displayName: user.display_name,
      avatarUrl: user.avatar_url,
      createdAt: user.created_at
    });
  } catch (error) {
    log.error('Get me error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Update profile
router.put('/profile', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    let decoded;
    try {
      decoded = jwt.verify(token, JWT_SECRET);
    } catch {
      return res.status(401).json({ error: 'Invalid token' });
    }

    const { displayName, avatarUrl } = req.body;

    // Verify current password if changing password
    if (req.body.password) {
      const { currentPassword, newPassword } = req.body;
      
      const userResult = await database.query(
        'SELECT password_hash FROM users WHERE id = $1',
        [decoded.id]
      );

      const isMatch = await bcrypt.compare(currentPassword, userResult.rows[0].password_hash);
      if (!isMatch) {
        return res.status(400).json({ error: 'Current password is incorrect' });
      }

      const salt = await bcrypt.genSalt(12);
      const newHash = await bcrypt.hash(newPassword, salt);
      
      await database.query(
        'UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2',
        [newHash, decoded.id]
      );

      log.security('Password changed', { userId: decoded.id });
    }

    const result = await database.query(
      `UPDATE users 
       SET display_name = COALESCE($1, display_name),
           avatar_url = COALESCE($2, avatar_url),
           updated_at = NOW()
       WHERE id = $3
       RETURNING id, email, display_name, avatar_url`,
      [displayName, avatarUrl, decoded.id]
    );

    const user = result.rows[0];
    log.userAction(decoded.id, 'profile_update');

    res.json({
      id: user.id,
      email: user.email,
      displayName: user.display_name,
      avatarUrl: user.avatar_url
    });
  } catch (error) {
    log.error('Update profile error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

// Change password
router.post('/change-password', async (req, res) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    let decoded;
    try {
      decoded = jwt.verify(token, JWT_SECRET);
    } catch {
      return res.status(401).json({ error: 'Invalid token' });
    }

    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
      return res.status(400).json({ error: 'Current and new password required' });
    }

    if (newPassword.length < 8) {
      return res.status(400).json({ error: 'New password must be at least 8 characters' });
    }

    // Get current hash
    const userResult = await database.query(
      'SELECT password_hash FROM users WHERE id = $1',
      [decoded.id]
    );

    // Verify current password
    const isMatch = await bcrypt.compare(currentPassword, userResult.rows[0].password_hash);
    if (!isMatch) {
      log.security('Password change attempt with wrong current password', { userId: decoded.id });
      return res.status(400).json({ error: 'Current password is incorrect' });
    }

    // Hash new password
    const salt = await bcrypt.genSalt(12);
    const newHash = await bcrypt.hash(newPassword, salt);

    // Update password
    await database.query(
      'UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2',
      [newHash, decoded.id]
    );

    // Invalidate all refresh tokens
    await database.query(
      'UPDATE users SET refresh_token = NULL, refresh_token_expires = NULL WHERE id = $1',
      [decoded.id]
    );

    log.security('Password changed successfully', { userId: decoded.id });
    log.userAction(decoded.id, 'password_change');

    res.json({ message: 'Password changed successfully. Please log in again.' });
  } catch (error) {
    log.error('Change password error', { error: error.message });
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
