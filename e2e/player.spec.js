const { test, expect } = require('@playwright/test');

const API_URL = process.env.API_URL || 'http://localhost:3001';

test.describe('Players API', () => {

  test('GET /api/players - should not require authentication', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players`);
    expect(response.status()).toBe(200);
  });

  test('GET /api/players - should return array of players', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players`);

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('GET /api/players - should support pagination', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players?page=1&limit=10`);

    expect(response.status()).toBe(200);
  });

  test('GET /api/players/:id - should return player details', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players/test-player-id`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/players/search - should search players', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players/search?q=Virat`);

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('GET /api/players/team/:teamId - should return players by team', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players/team/rcb`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/players/role/:role - should filter by role', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players/role/batsman`);

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('GET /api/players/:id/stats - should return player stats', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players/test-player-id/stats`);

    expect([200, 404]).toContain(response.status());
  });

  test('GET /api/players/:id/points - should return player points', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players/test-player-id/points`);

    expect([200, 404]).toContain(response.status());
  });
});

test.describe('Health Check', () => {

  test('GET /api/health - should return ok status', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/health`);

    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('status', 'ok');
  });
});
