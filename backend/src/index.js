const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const http = require('http');
const { Server } = require('socket.io');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const authRoutes = require('./routes/auth');
const leagueRoutes = require('./routes/leagues');
const playerRoutes = require('./routes/players');
const draftRoutes = require('./routes/drafts');
const teamRoutes = require('./routes/teams');
const matchRoutes = require('./routes/matches');
const chatRoutes = require('./routes/chat');
const tradesRoutes = require('./routes/trades');
const scoresRoutes = require('./routes/scores');
const analyticsRoutes = require('./routes/analytics');

const app = express();
const server = http.createServer(app);

// Security middleware
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: { error: 'Too many requests, please try again later' }
});
app.use('/api/', limiter);

// Stricter rate limit for auth endpoints
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  message: { error: 'Too many authentication attempts' }
});
app.use('/api/auth/', authLimiter);

// Body parsing with size limits
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Request logging
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} ${res.statusCode} ${duration}ms`);
  });
  next();
});

// Health check (no auth required)
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: process.env.APP_VERSION || '1.0.0'
  });
});

// Socket.io setup with CORS
const io = new Server(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
    methods: ['GET', 'POST'],
    credentials: true
  },
  pingTimeout: 60000,
  pingInterval: 25000
});

// Make io accessible to routes
app.set('io', io);

// JWT Authentication middleware
const authenticateSocket = (socket, next) => {
  const token = socket.handshake.auth.token;
  if (!token) {
    return next(new Error('Authentication required'));
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    socket.user = decoded;
    next();
  } catch (error) {
    next(new Error('Invalid token'));
  }
};

// Socket connection handling
io.use(authenticateSocket);

io.on('connection', (socket) => {
  console.log(`User connected: ${socket.user.id}`);
  
  // Join league room
  socket.on('join:league', (data) => {
    const { leagueId } = data;
    socket.join(`league-${leagueId}`);
    console.log(`User ${socket.user.id} joined league ${leagueId}`);
  });
  
  // Leave league room
  socket.on('leave:league', (data) => {
    const { leagueId } = data;
    socket.leave(`league-${leagueId}`);
  });
  
  // Handle disconnect
  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.user.id}`);
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/leagues', leagueRoutes);
app.use('/api/players', playerRoutes);
app.use('/api/drafts', draftRoutes);
app.use('/api/teams', teamRoutes);
app.use('/api/matches', matchRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/trades', tradesRoutes);
app.use('/api/scores', scoresRoutes);
app.use('/api/analytics', analyticsRoutes);

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err.message);
  
  // Don't leak error details in production
  const message = process.env.NODE_ENV === 'production' 
    ? 'Internal server error' 
    : err.message;
  
  res.status(err.status || 500).json({ 
    error: message,
    ...(process.env.NODE_ENV !== 'production' && { stack: err.stack })
  });
});

const PORT = process.env.PORT || 3001;

server.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════╗
║   IPL Fantasy Pro API Server                             ║
║   Version: ${process.env.APP_VERSION || '1.0.0'}                                    ║
║   Environment: ${process.env.NODE_ENV || 'development'}                               ║
║   Port: ${PORT}                                              ║
╚═══════════════════════════════════════════════════════════╝
  `);
});

module.exports = { app, server, io };
