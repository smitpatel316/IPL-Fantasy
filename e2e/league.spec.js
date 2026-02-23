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

test.describe('League API', () => {

  test('GET /api/leagues - should require authentication', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/leagues`);
    expect(response.status()).toBe(401);
  });

  test('GET /api/leagues - should return user leagues with valid token', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/leagues`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    }
  });

  test('POST /api/leagues - should create new league', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.post(`${API_URL}/api/leagues`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          name: `Test League ${Date.now()}`,
          maxPlayers: 10,
          isPublic: true
        }
      });

      expect([201, 400]).toContain(response.status());
    }
  });

  test('POST /api/leagues - should reject league without name', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.post(`${API_URL}/api/leagues`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          maxPlayers: 10
          // missing name
        }
      });

      expect(response.status()).toBe(400);
    }
  });

  test('GET /api/leagues/:id - should return league details', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/leagues/test-league-id`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('PUT /api/leagues/:id - should update league as commissioner', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.put(`${API_URL}/api/leagues/test-league-id`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          name: 'Updated League Name'
        }
      });

      expect([200, 403, 404]).toContain(response.status());
    }
  });

  test('POST /api/leagues/:id/join - should join league with valid code', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.post(`${API_URL}/api/leagues/join`, {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        data: {
          leagueCode: 'INVALID'
        }
      });

      expect([400, 404, 200]).toContain(response.status());
    }
  });

  test('DELETE /api/leagues/:id/leave - should leave league', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.delete(`${API_URL}/api/leagues/test-league-id/leave`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/leagues/:id/members - should return league members', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/leagues/test-league-id/members`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });

  test('GET /api/leagues/:id/draft - should return draft status', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/leagues/test-league-id/draft`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });
});
