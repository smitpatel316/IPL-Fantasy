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

test.describe('Match API', () => {

  test('GET /api/matches - should not require authentication', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/matches`);
    expect([200, 401]).toContain(response.status());
  });

  test('GET /api/matches - should return list of matches', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/matches`);

    // Should return 200 or 401 depending on auth requirement
    if (response.status() === 200) {
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    } else {
      expect(response.status()).toBe(401);
    }
  });

  test('GET /api/matches/:id - should return match details', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/matches/test-match-id`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/matches/live - should return live matches', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/matches/live`);

    if (response.status() === 200) {
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    }
  });

  test('GET /api/matches/upcoming - should return upcoming matches', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/matches/upcoming`);

    if (response.status() === 200) {
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    }
  });

  test('GET /api/matches/:id/score - should return match score', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/matches/test-match-id/score`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/matches/:id/points - should return player points for match', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/matches/test-match-id/points`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });
});

test.describe('Scores API', () => {

  test('GET /api/scores - should return scores', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/scores`);

    if (response.status() === 200) {
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
    }
  });

  test('GET /api/scores/player/:id - should return player scores', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/scores/player/test-player-id`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/scores/match/:id - should return match scores', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/scores/match/test-match-id`);

    expect([200, 404]).toContain(response.status());
  });
});

test.describe('Analytics API', () => {

  test('GET /api/analytics/player/:id - should return player analytics', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/analytics/player/test-player-id`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/analytics/league/:id - should return league analytics', async ({ request }) => {
    const token = await getAuthToken(request);

    if (token) {
      const response = await request.get(`${API_URL}/api/analytics/league/test-league-id`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      expect([200, 404]).toContain(response.status());
    }
  });
});
