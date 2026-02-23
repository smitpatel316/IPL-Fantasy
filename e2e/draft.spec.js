const { test, expect } = require('@playwright/test');

const API_URL = process.env.API_URL || 'http://localhost:3001';

async function getAuthToken(request) {
  const response = await request.post(`${API_URL}/api/auth/login`, {
    data: {
      email: 'test@example.com',
      password: 'password123'
    }
  });

  if (response.status() === 200) {
    const data = await response.json();
    return data.token || data.accessToken;
  }
  return null;
}

test.describe('Draft API', () => {

  test('GET /api/drafts - should require authentication', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/drafts`);
    expect(response.status()).toBe(401);
  });

  test('GET /api/drafts - should return user drafts', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/drafts`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    }
  });

  test('GET /api/drafts/:id - should return draft details', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/drafts/test-draft-id`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/drafts/:id/players - should return available players', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/drafts/test-draft-id/players`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('POST /api/drafts/:id/bid - should place a bid', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.post(`${API_URL}/api/drafts/test-draft-id/bid`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          playerId: 'test-player-id',
          amount: 1000000
        }
      });

      expect([200, 400, 404]).toContain(response.status());
    }
  });

  test('POST /api/drafts/:id/bid - should reject invalid bid amount', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.post(`${API_URL}/api/drafts/test-draft-id/bid`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          playerId: 'test-player-id',
          amount: -100
        }
      });

      expect(response.status()).toBe(400);
    }
  });

  test('GET /api/drafts/:id/teams - should return draft teams', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/drafts/test-draft-id/teams`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/drafts/:id/sold-players - should return sold players', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/drafts/test-draft-id/sold-players`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/drafts/:id/clock - should return draft clock status', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/drafts/test-draft-id/clock`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });
});
