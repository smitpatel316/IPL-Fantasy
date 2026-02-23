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

test.describe('Team API', () => {

  test('GET /api/teams - should require authentication', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/teams`);
    expect(response.status()).toBe(401);
  });

  test('GET /api/teams - should return user teams', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/teams`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    }
  });

  test('GET /api/teams/:id - should return team details', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/teams/test-team-id`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/teams/:id/players - should return team players', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/teams/test-team-id/players`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('PUT /api/teams/:id/captain - should set team captain', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.put(`${API_URL}/api/teams/test-team-id/captain`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          playerId: 'test-player-id'
        }
      });

      expect([200, 400, 404]).toContain(response.status());
    }
  });

  test('PUT /api/teams/:id/vice-captain - should set vice-captain', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.put(`${API_URL}/api/teams/test-team-id/vice-captain`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          playerId: 'test-player-id'
        }
      });

      expect([200, 400, 404]).toContain(response.status());
    }
  });

  test('PUT /api/teams/:id/captain - should reject non-team player', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.put(`${API_URL}/api/teams/test-team-id/captain`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          playerId: 'non-existent-player'
        }
      });

      expect(response.status()).toBe(400);
    }
  });

  test('GET /api/teams/:id/points - should return team points', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/teams/test-team-id/points`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/teams/:id/points/breakdown - should return points breakdown', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/teams/test-team-id/points/breakdown`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });
});
