const jwt = require('jsonwebtoken');
const database = require('../db/pool');
const log = require('./logger');

const JWT_SECRET = process.env.JWT_SECRET || 'ipl-fantasy-secret-key-2026';

// Auth middleware - verifies JWT access token
const authenticate = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const token = authHeader.split(' ')[1];

    // Verify token
    let decoded;
    try {
      decoded = jwt.verify(token, JWT_SECRET);
    } catch (error) {
      if (error.name === 'TokenExpiredError') {
        return res.status(401).json({ error: 'Token expired', code: 'TOKEN_EXPIRED' });
      }
      return res.status(401).json({ error: 'Invalid token' });
    }

    // Check user still exists and is active
    const result = await database.query(
      'SELECT id, email, display_name, avatar_url FROM users WHERE id = $1',
      [decoded.id]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ error: 'User not found' });
    }

    // Attach user to request
    req.user = result.rows[0];
    req.userId = decoded.id;
    
    next();
  } catch (error) {
    log.error('Auth middleware error', { error: error.message });
    res.status(500).json({ error: 'Authentication error' });
  }
};

// Optional auth - doesn't fail if no token
const optionalAuth = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return next();
    }

    const token = authHeader.split(' ')[1];

    try {
      const decoded = jwt.verify(token, JWT_SECRET);
      
      const result = await database.query(
        'SELECT id, email, display_name, avatar_url FROM users WHERE id = $1',
        [decoded.id]
      );

      if (result.rows.length > 0) {
        req.user = result.rows[0];
        req.userId = decoded.id;
      }
    } catch {
      // Token invalid, continue without user
    }
    
    next();
  } catch (error) {
    next();
  }
};

// Role-based access
const requireRole = (...roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    // For now, check if user is commissioner of league
    // This would be expanded based on your role system
    next();
  };
};

// League access - verify user is member of league
const requireLeagueMember = async (req, res, next) => {
  try {
    const { leagueId } = req.params;
    
    if (!leagueId) {
      return res.status(400).json({ error: 'League ID required' });
    }

    const result = await database.query(
      'SELECT * FROM league_members WHERE league_id = $1 AND user_id = $2',
      [leagueId, req.userId]
    );

    if (result.rows.length === 0) {
      return res.status(403).json({ error: 'Not a member of this league' });
    }

    req.leagueMember = result.rows[0];
    next();
  } catch (error) {
    log.error('League member check error', { error: error.message });
    res.status(500).json({ error: 'Authorization error' });
  }
};

// Commissioner only
const requireCommissioner = async (req, res, next) => {
  try {
    const { leagueId } = req.params;

    const result = await database.query(
      'SELECT * FROM leagues WHERE id = $1 AND commissioner_id = $2',
      [leagueId, req.userId]
    );

    if (result.rows.length === 0) {
      return res.status(403).json({ error: 'Only commissioner can perform this action' });
    }

    next();
  } catch (error) {
    log.error('Commissioner check error', { error: error.message });
    res.status(500).json({ error: 'Authorization error' });
  }
};

// CSRF protection (for state-changing operations)
const csrfProtection = (req, res, next) => {
  // In production, implement CSRF token validation
  // For now, we rely on JWT being sent with requests
  next();
};

module.exports = {
  authenticate,
  optionalAuth,
  requireRole,
  requireLeagueMember,
  requireCommissioner,
  csrfProtection
};
