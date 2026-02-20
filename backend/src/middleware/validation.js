const { body, validationResult } = require('express-validator');

// MARK: - Validation Helpers

// Custom validation middleware
const validate = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      error: 'Validation failed',
      details: errors.array().map(e => ({
        field: e.path,
        message: e.msg
      }))
    });
  }
  next();
};

// MARK: - Auth Validators
const authValidators = {
  register: [
    body('email')
      .isEmail()
      .normalizeEmail()
      .withMessage('Valid email is required'),
    body('password')
      .isLength({ min: 8 })
      .withMessage('Password must be at least 8 characters'),
    body('displayName')
      .trim()
      .isLength({ min: 2, max: 50 })
      .withMessage('Display name must be 2-50 characters'),
    validate
  ],
  
  login: [
    body('email')
      .isEmail()
      .normalizeEmail()
      .withMessage('Valid email is required'),
    body('password')
      .notEmpty()
      .withMessage('Password is required'),
    validate
  ]
};

// MARK: - League Validators
const leagueValidators = {
  create: [
    body('name')
      .trim()
      .isLength({ min: 3, max: 100 })
      .withMessage('League name must be 3-100 characters'),
    body('maxTeams')
      .isInt({ min: 4, max: 20 })
      .withMessage('Teams must be 4-20'),
    body('auctionBudget')
      .isFloat({ min: 20, max: 200 })
      .withMessage('Budget must be 20-200 Cr'),
    validate
  ],
  
  join: [
    body('code')
      .trim()
      .isLength({ min: 6, max: 10 })
      .withMessage('Invalid league code'),
    body('teamName')
      .trim()
      .isLength({ min: 2, max: 50 })
      .withMessage('Team name must be 2-50 characters'),
    validate
  ]
};

// MARK: - Draft Validators
const draftValidators = {
  bid: [
    body('amount')
      .isFloat({ min: 0.5 })
      .withMessage('Bid must be at least 0.5 Cr'),
    validate
  ]
};

// MARK: - Team Validators
const teamValidators = {
  captain: [
    body('captainId')
      .isUUID()
      .withMessage('Invalid player ID'),
    body('viceCaptainId')
      .optional()
      .isUUID()
      .withMessage('Invalid player ID'),
    validate
  ],
  
  lineup: [
    body('playingIds')
      .isArray({ min: 1, max: 11 })
      .withMessage('Must select 1-11 players'),
    body('playingIds.*')
      .isUUID()
      .withMessage('Invalid player ID'),
    validate
  ]
};

// MARK: - Chat Validators
const chatValidators = {
  message: [
    body('text')
      .trim()
      .isLength({ min: 1, max: 500 })
      .withMessage('Message must be 1-500 characters'),
    validate
  ]
};

// MARK: - Trade Validators
const tradeValidators = {
  propose: [
    body('leagueId')
      .isUUID()
      .withMessage('Invalid league ID'),
    body('offeredPlayerIds')
      .isArray({ min: 1 })
      .withMessage('Must offer at least 1 player'),
    body('offeredPlayerIds.*')
      .isUUID()
      .withMessage('Invalid player ID'),
    body('offeredCash')
      .optional()
      .isFloat({ min: 0 })
      .withMessage('Cash must be positive'),
    validate
  ]
};

// MARK: - Sanitization Helpers

const sanitizeInput = (input) => {
  if (typeof input !== 'string') return input;
  
  // Remove potential XSS vectors
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

const sanitizeObject = (obj) => {
  if (typeof obj !== 'object' || obj === null) return obj;
  
  const sanitized = {};
  for (const [key, value] of Object.entries(obj)) {
    sanitized[key] = sanitizeInput(value);
  }
  return sanitized;
};

// MARK: - Rate Limiting Helpers

const createRateLimiter = (options = {}) => {
  const {
    windowMs = 15 * 60 * 1000,
    max = 100,
    message = 'Too many requests'
  } = options;
  
  const requests = new Map();
  
  return (req, res, next) => {
    const key = req.ip || req.connection.remoteAddress;
    const now = Date.now();
    
    // Clean old entries
    for (const [k, v] of requests) {
      if (now - v.start > windowMs) {
        requests.delete(k);
      }
    }
    
    const request = requests.get(key) || { start: now, count: 0 };
    request.count++;
    
    if (request.count > max) {
      return res.status(429).json({ error: message });
    }
    
    requests.set(key, request);
    next();
  };
};

// MARK: - Error Handler

const errorHandler = (err, req, res, next) => {
  console.error('Error:', {
    message: err.message,
    stack: process.env.NODE_ENV === 'development' ? err.stack : undefined,
    path: req.path,
    method: req.method,
    ip: req.ip
  });
  
  // Known error types
  if (err.name === 'ValidationError') {
    return res.status(400).json({ error: err.message });
  }
  
  if (err.name === 'UnauthorizedError') {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  if (err.code === '23505') { // PostgreSQL unique violation
    return res.status(409).json({ error: 'Resource already exists' });
  }
  
  if (err.code === '23503') { // PostgreSQL foreign key violation
    return res.status(400).json({ error: 'Invalid reference' });
  }
  
  // Generic error
  res.status(err.status || 500).json({
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal server error' 
      : err.message
  });
};

// MARK: - Not Found Handler

const notFoundHandler = (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
};

// MARK: - Request ID Middleware

const requestId = (req, res, next) => {
  req.id = require('crypto').randomUUID();
  res.setHeader('X-Request-ID', req.id);
  next();
};

// MARK: - Timeout Handler

const timeoutHandler = (req, res, next) => {
  req.setTimeout(30000, () => {
    res.status(503).json({ error: 'Request timeout' });
  });
  next();
};

module.exports = {
  validate,
  authValidators,
  leagueValidators,
  draftValidators,
  teamValidators,
  chatValidators,
  tradeValidators,
  sanitizeInput,
  sanitizeObject,
  createRateLimiter,
  errorHandler,
  notFoundHandler,
  requestId,
  timeoutHandler
};
