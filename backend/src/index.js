const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const http = require('http');
const { Server } = require('socket.io');
require('dotenv').config();

const database = require('./db/pool');
const log = require('./middleware/logger');
const { authenticate, optionalAuth } = require('./middleware/auth');
const { errorHandler, notFoundHandler } = require('./middleware/validation');

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
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", "wss:", "ws:"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  message: { error: 'Too many requests, please try again later' }
});
app.use('/api/', limiter);

const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  message: { error: 'Too many authentication attempts' }
});
app.use('/api/auth/', authLimiter);

// Body parsing
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Initialize database
database.initialize();

// Health check (no auth required)
app.get('/api/health', async (req, res) => {
  const dbHealth = await database.healthCheck();
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: process.env.APP_VERSION || '1.0.0',
    database: dbHealth
  });
});

// Socket.io setup
const io = new Server(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
    methods: ['GET', 'POST'],
    credentials: true
  },
  pingTimeout: 60000,
  pingInterval: 25000
});

app.set('io', io);

// Socket authentication
io.use((socket, next) => {
  const token = socket.handshake.auth.token;
  if (!token) {
    return next(new Error('Authentication required'));
  }
  
  try {
    const jwt = require('jsonwebtoken');
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'ipl-fantasy-secret-key-2026');
    socket.user = decoded;
    next();
  } catch (error) {
    next(new Error('Invalid token'));
  }
});

io.on('connection', (socket) => {
  log.info(`User connected: ${socket.user.id}`);
  
  socket.on('join:league', (data) => {
    const { leagueId } = data;
    socket.join(`league-${leagueId}`);
    log.info(`User ${socket.user.id} joined league ${leagueId}`);
  });
  
  socket.on('leave:league', (data) => {
    const { leagueId } = data;
    socket.leave(`league-${leagueId}`);
  });
  
  socket.on('disconnect', () => {
    log.info(`User disconnected: ${socket.user.id}`);
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/leagues', authenticate, leagueRoutes);
app.use('/api/players', optionalAuth, playerRoutes);
app.use('/api/drafts', authenticate, draftRoutes);
app.use('/api/teams', authenticate, teamRoutes);
app.use('/api/matches', authenticate, matchRoutes);
app.use('/api/chat', authenticate, chatRoutes);
app.use('/api/trades', authenticate, tradesRoutes);
app.use('/api/scores', optionalAuth, scoresRoutes);
app.use('/api/analytics', authenticate, analyticsRoutes);

// Error handling
app.use(notFoundHandler);
app.use(errorHandler);

const PORT = process.env.PORT || 3001;

server.listen(PORT, () => {
  log.info(`
╔═══════════════════════════════════════════════════════════╗
║   IPL Fantasy Pro API Server                             ║
║   Version: ${process.env.APP_VERSION || '1.0.0'}                                    ║
║   Environment: ${process.env.NODE_ENV || 'development'}                               ║
║   Port: ${PORT}                                              ║
╚═══════════════════════════════════════════════════════════╝
  `);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  log.info('SIGTERM received, shutting down...');
  await database.shutdown();
  server.close(() => {
    log.info('Server shut down');
    process.exit(0);
  });
});

module.exports = { app, server, io };
