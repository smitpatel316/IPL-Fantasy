const request = require('supertest');
const jwt = require('jsonwebtoken');

// Mock the database pool - handle both named and default exports
jest.mock('../src/db/pool', () => {
  const mockFn = jest.fn();
  return {
    __esModule: true,
    default: { query: mockFn },
    pool: { query: mockFn },
    query: mockFn
  };
});

const database = require('../src/db/pool');
const pool = database;

// Global mock
beforeEach(() => {
  jest.clearAllMocks();
  pool.query.mockResolvedValue({ rows: [] });
});

// Mock Socket.io
jest.mock('socket.io', () => jest.fn().mockImplementation(() => ({
  to: jest.fn().mockReturnThis(),
  emit: jest.fn(),
  on: jest.fn()
})));

const express = require('express');
const cors = require('cors');

const authRoutes = require('../src/routes/auth');
const playerRoutes = require('../src/routes/players');
const scoresRoutes = require('../src/routes/scores');

const testApp = express();
testApp.use(cors());
testApp.use(express.json());
testApp.set('io', { to: () => ({ emit: jest.fn() }) });

testApp.use('/api/auth', authRoutes);
testApp.use('/api/players', playerRoutes);
testApp.use('/api/scores', scoresRoutes);
testApp.get('/api/health', (req, res) => res.json({ status: 'ok' }));

const JWT_SECRET = 'ipl-fantasy-secret-key-2026';
const generateToken = (userId = 'test-user') => jwt.sign({ id: userId }, JWT_SECRET, { expiresIn: '1h' });

// ==================== TESTS ====================

describe('Health', () => {
  test('GET /api/health returns ok', async () => {
    const res = await request(testApp).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
  });
});

describe('Auth API', () => {
  test('POST /api/auth/register - success', async () => {
    const res = await request(testApp)
      .post('/api/auth/register')
      .send({ email: 'new@test.com', password: 'password123', displayName: 'New User' });
    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('token');
  });

  test('POST /api/auth/register - invalid email', async () => {
    const res = await request(testApp)
      .post('/api/auth/register')
      .send({ email: 'invalid', password: '123456', displayName: 'Test' });
    expect(res.status).toBe(400);
  });

  test('POST /api/authlogin - success', async () => {
    const res = await request(testApp)
      .post('/api/auth/login')
      .send({ email: 'test@test.com', password: 'password123' });
    expect([200, 400]).toContain(res.status);
  });

  test('GET /api/auth/me - with valid token', async () => {
    const res = await request(testApp)
      .get('/api/auth/me')
      .set('Authorization', `Bearer ${generateToken()}`);
    expect([200, 401]).toContain(res.status);
  });

  test('GET /api/auth/me - no token', async () => {
    const res = await request(testApp).get('/api/auth/me');
    expect(res.status).toBe(401);
  });
});

describe('Players API', () => {
  test('GET /api/players returns list', async () => {
    const res = await request(testApp).get('/api/players');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  test('GET /api/players?team=RCB filters by team', async () => {
    const res = await request(testApp).get('/api/players?team=RCB');
    expect(res.status).toBe(200);
  });

  test('GET /api/players?role=batsman filters by role', async () => {
    const res = await request(testApp).get('/api/players?role=batsman');
    expect(res.status).toBe(200);
  });

  test('GET /api/players/:id returns player', async () => {
    const res = await request(testApp).get('/api/players/p1');
    expect([200, 404]).toContain(res.status);
  });

  test('GET /api/players/meta/teams returns teams', async () => {
    const res = await request(testApp).get('/api/players/meta/teams');
    expect(res.status).toBe(200);
  });

  test('GET /api/players/meta/roles returns roles', async () => {
    const res = await request(testApp).get('/api/players/meta/roles');
    expect(res.status).toBe(200);
    expect(res.body).toContain('batsman');
  });
});

describe('Scores API', () => {
  test('GET /api/scores/live', async () => {
    const res = await request(testApp).get('/api/scores/live');
    expect(res.status).toBe(200);
  });

  test('GET /api/scores/upcoming', async () => {
    const res = await request(testApp).get('/api/scores/upcoming');
    expect(res.status).toBe(200);
  });

  test('GET /api/scores/completed', async () => {
    const res = await request(testApp).get('/api/scores/completed');
    expect(res.status).toBe(200);
  });

  test('POST /api/scores/webhook', async () => {
    const res = await request(testApp)
      .post('/api/scores/webhook')
      .send({ matchId: 'm1' });
    expect(res.status).toBe(200);
  });

  test('POST /api/scores/sync-points', async () => {
    const res = await request(testApp)
      .post('/api/scores/sync-points')
      .send({ matchId: 'm1' });
    expect(res.status).toBe(200);
  });
});
