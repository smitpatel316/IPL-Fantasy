const request = require('supertest');
const jwt = require('jsonwebtoken');

// Mock the database pool
jest.mock('../src/db/pool', () => ({
  query: jest.fn()
}));

const pool = require('../src/db/pool');
const app = require('../src/index');

// Helper to generate test token
const generateToken = (userId = 'test-user-id') => {
  return jwt.sign({ id: userId, email: 'test@example.com' }, 'test-secret', { expiresIn: '1h' });
};

describe('Auth API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('POST /api/auth/register', () => {
    it('should register a new user', async () => {
      pool.query
        .mockResolvedValueOnce({ rows: [] }) // Check existing user - none found
        .mockResolvedValueOnce({ // Insert user
          rows: [{
            id: 'new-user-id',
            email: 'test@example.com',
            display_name: 'Test User',
            created_at: new Date()
          }]
        });

      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'test@example.com',
          password: 'password123',
          displayName: 'Test User'
        });

      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('token');
      expect(response.body.user.email).toBe('test@example.com');
    });

    it('should reject duplicate email', async () => {
      pool.query.mockResolvedValueOnce({
        rows: [{ id: 'existing-user' }]
      });

      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'existing@example.com',
          password: 'password123',
          displayName: 'Test User'
        });

      expect(response.status).toBe(400);
      expect(response.body.error).toContain('already registered');
    });
  });

  describe('POST /api/auth/login', () => {
    it('should login with correct credentials', async () => {
      const hashedPassword = require('bcryptjs').hashSync('password123', 10);
      
      pool.query.mockResolvedValueOnce({
        rows: [{
          id: 'user-id',
          email: 'test@example.com',
          password_hash: hashedPassword,
          display_name: 'Test User',
          avatar_url: null,
          created_at: new Date()
        }]
      });

      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'test@example.com',
          password: 'password123'
        });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('token');
    });

    it('should reject invalid password', async () => {
      const hashedPassword = require('bcryptjs').hashSync('password123', 10);
      
      pool.query.mockResolvedValueOnce({
        rows: [{
          id: 'user-id',
          email: 'test@example.com',
          password_hash: hashedPassword
        }]
      });

      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'test@example.com',
          password: 'wrongpassword'
        });

      expect(response.status).toBe(400);
    });
  });
});

describe('Leagues API', () => {
  const token = generateToken('test-user');

  describe('GET /api/leagues', () => {
    it('should return user leagues', async () => {
      pool.query.mockResolvedValueOnce({
        rows: [{
          id: 'league-1',
          name: 'Test League',
          code: 'ABC123',
          commissioner_id: 'test-user',
          max_teams: 10,
          auction_budget: '100.00',
          status: 'open',
          created_at: new Date(),
          team_name: 'My Team',
          is_commissioner: true
        }]
      });

      const response = await request(app)
        .get('/api/leagues')
        .set('Authorization', `Bearer ${token}`);

      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
    });

    it('should reject unauthorized request', async () => {
      const response = await request(app)
        .get('/api/leagues');

      expect(response.status).toBe(401);
    });
  });

  describe('POST /api/leagues', () => {
    it('should create a new league', async () => {
      // Mock league creation
      pool.query
        .mockResolvedValueOnce({ rows: [{ id: 'new-league' }] }) // Insert league
        .mockResolvedValueOnce({ rows: [{ id: 'member-id' }] }) // Add member
        .mockResolvedValueOnce({ rows: [{ id: 'team-id' }] }); // Create team

      const response = await request(app)
        .post('/api/leagues')
        .set('Authorization', `Bearer ${token}`)
        .send({
          name: 'New League',
          maxTeams: 10,
          auctionBudget: 100
        });

      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('code');
    });
  });
});

describe('Players API', () => {
  describe('GET /api/players', () => {
    it('should return all players', async () => {
      pool.query.mockResolvedValueOnce({
        rows: [
          { id: 'p1', name: 'Virat Kohli', role: 'batsman', team: 'RCB', base_price: '18.00', is_overseas: false },
          { id: 'p2', name: 'Jasprit Bumrah', role: 'bowler', team: 'MI', base_price: '18.00', is_overseas: false }
        ]
      });

      const response = await request(app)
        .get('/api/players');

      expect(response.status).toBe(200);
      expect(response.body.length).toBe(2);
      expect(response.body[0].name).toBe('Virat Kohli');
    });

    it('should filter by team', async () => {
      pool.query.mockResolvedValueOnce({
        rows: [
          { id: 'p1', name: 'Virat Kohli', role: 'batsman', team: 'RCB', base_price: '18.00' }
        ]
      });

      const response = await request(app)
        .get('/api/players?team=RCB');

      expect(response.status).toBe(200);
      expect(pool.query).toHaveBeenCalledWith(
        expect.stringContaining('AND team = $'),
        expect.arrayContaining(['RCB'])
      );
    });

    it('should filter by role', async () => {
      pool.query.mockResolvedValueOnce({ rows: [] });

      await request(app)
        .get('/api/players?role=bowler');

      expect(pool.query).toHaveBeenCalledWith(
        expect.stringContaining('AND role = $'),
        expect.arrayContaining(['bowler'])
      );
    });

    it('should search by name', async () => {
      pool.query.mockResolvedValueOnce({ rows: [] });

      await request(app)
        .get('/api/players?search=Kohli');

      expect(pool.query).toHaveBeenCalledWith(
        expect.stringContaining('name ILIKE $'),
        expect.arrayContaining(['%Kohli%'])
      );
    });
  });
});

describe('Validation Tests', () => {
  it('should validate email format', async () => {
    const response = await request(app)
      .post('/api/auth/register')
      .send({
        email: 'invalid-email',
        password: 'password123',
        displayName: 'Test'
      });

    expect(response.status).toBe(400);
  });

  it('should require email on register', async () => {
    const response = await request(app)
      .post('/api/auth/register')
      .send({
        password: 'password123',
        displayName: 'Test'
      });

    expect(response.status).toBe(400);
  });
});
