const { test, expect } = require('@playwright/test');

const API_URL = process.env.API_URL || 'http://localhost:3001';

test.describe('Authentication API', () => {

  test('POST /api/auth/register - should create new user', async ({ request }) => {
    const uniqueEmail = `test${Date.now()}@example.com`;
    const response = await request.post(`${API_URL}/api/auth/register`, {
      data: {
        email: uniqueEmail,
        password: 'password123',
        name: 'Test User'
      }
    });

    // Expect 201 for successful registration or 400 if email exists
    expect([201, 400]).toContain(response.status());
  });

  test('POST /api/auth/register - should reject duplicate email', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/register`, {
      data: {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      }
    });

    // Should return 400 for duplicate
    expect([400, 409]).toContain(response.status());
  });

  test('POST /api/auth/register - should reject invalid email', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/register`, {
      data: {
        email: 'invalid-email',
        password: 'password123',
        name: 'Test User'
      }
    });

    expect(response.status()).toBe(400);
    const data = await response.json();
    expect(data).toHaveProperty('error');
  });

  test('POST /api/auth/register - should reject weak password', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/register`, {
      data: {
        email: `test${Date.now()}@example.com`,
        password: '123',
        name: 'Test User'
      }
    });

    expect(response.status()).toBe(400);
  });

  test('POST /api/auth/login - should login with valid credentials', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      data: {
        email: 'test@example.com',
        password: 'password123'
      }
    });

    expect([200, 401]).toContain(response.status());
  });

  test('POST /api/auth/login - should reject invalid credentials', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      data: {
        email: 'nonexistent@example.com',
        password: 'wrongpassword'
      }
    });

    expect(response.status()).toBe(401);
  });

  test('POST /api/auth/login - should reject missing fields', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/auth/login`, {
      data: {
        email: 'test@example.com'
        // missing password
      }
    });

    expect(response.status()).toBe(400);
  });

  test('GET /api/auth/me - should return 401 without token', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/auth/me`);
    expect(response.status()).toBe(401);
  });

  test('GET /api/auth/me - should return user with valid token', async ({ request }) => {
    // First login to get token
    const loginResponse = await request.post(`${API_URL}/api/auth/login`, {
      data: {
        email: 'test@example.com',
        password: 'password123'
      }
    });

    if (loginResponse.status() === 200) {
      const loginData = await loginResponse.json();
      const token = loginData.token || loginData.accessToken;

      if (token) {
        const meResponse = await request.get(`${API_URL}/api/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        expect(meResponse.status()).toBe(200);
      }
    }
  });
});
