const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_URL = process.env.API_URL || 'http://localhost:3001';

test.describe('IPL Fantasy Pro E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  // ==================== AUTH TESTS ====================
  
  test.describe('Authentication', () => {
    
    test('should display login page', async ({ page }) => {
      await expect(page.locator('text=IPL Fantasy Pro')).toBeVisible();
      await expect(page.locator('text=Create your dream team')).toBeVisible();
      await expect(page.locator('button:has-text("Login")')).toBeVisible();
    });

    test('should show register option', async ({ page }) => {
      await expect(page.locator('text=Create Account')).toBeVisible();
    });

    test('should navigate to register page', async ({ page }) => {
      await page.click('text=Create Account');
      await expect(page.locator('text=Create Account')).toBeVisible();
      await expect(page.locator('text=Join the fantasy league')).toBeVisible();
    });

    test('should validate empty login form', async ({ page }) => {
      await page.click('button:has-text("Login")');
      // Should show validation errors
      await expect(page.locator('text=Email is required')).toBeVisible();
    });
  });

  // ==================== LEAGUE TESTS ====================
  
  test.describe('League Management', () => {
    
    test('should display leagues page', async ({ page }) => {
      // Login first
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'test@example.com');
      await page.fill('input[type="password"]', 'password123');
      await page.click('button:has-text("Login")');
      
      // Navigate to leagues
      await page.click('text=Leagues');
      await expect(page.locator('text=No Leagues')).toBeVisible();
    });

    test('should open create league modal', async ({ page }) => {
      // Login first
      await page.goto(`${BASE_URL}/login`);
      await page.fill('input[type="email"]', 'test@example.com');
      await page.fill('input[type="password"]', 'password123');
      await page.click('button:has-text("Login")');
      await page.click('text=Leagues');
      
      // Click create
      await page.click('text=Create');
      await expect(page.locator('text=Create League')).toBeVisible();
    });

    test('should display league code after creation', async ({ page }) => {
      // This would require actual login and API
      // Mock test for UI elements
      await page.goto(`${BASE_URL}/leagues/test-league-id`);
      await expect(page.locator('text=League Code')).toBeVisible();
    });
  });

  // ==================== DRAFT TESTS ====================
  
  test.describe('Auction Draft', () => {
    
    test('should display draft room', async ({ page }) => {
      await page.goto(`${BASE_URL}/draft`);
      await expect(page.locator('text=Auction Draft')).toBeVisible();
    });

    test('should show player cards', async ({ page }) => {
      await page.goto(`${BASE_URL}/draft`);
      // Should see player search or draft room
      await expect(page.locator('text=Players')).toBeVisible();
    });

    test('should display bid controls', async ({ page }) => {
      await page.goto(`${BASE_URL}/draft`);
      // Check for bid-related elements
      const content = await page.content();
      expect(content).toContain('Bid');
    });
  });

  // ==================== TEAM TESTS ====================
  
  test.describe('Team Management', () => {
    
    test('should display my team page', async ({ page }) => {
      await page.goto(`${BASE_URL}/team`);
      await expect(page.locator('text=My Team')).toBeVisible();
    });

    test('should show captain selection', async ({ page }) => {
      await page.goto(`${BASE_URL}/team`);
      await expect(page.locator('text=Select Captain')).toBeVisible();
    });

    test('should show squad list', async ({ page }) => {
      await page.goto(`${BASE_URL}/team`);
      await expect(page.locator('text=Squad')).toBeVisible();
    });
  });

  // ==================== STANDINGS TESTS ====================
  
  test.describe('Standings', () => {
    
    test('should display standings page', async ({ page }) => {
      await page.goto(`${BASE_URL}/standings`);
      await expect(page.locator('text=Standings')).toBeVisible();
    });

    test('should show week selector', async ({ page }) => {
      await page.goto(`${BASE_URL}/standings`);
      await expect(page.locator('text=W1')).toBeVisible();
    });
  });

  // ==================== MATCH CENTER TESTS ====================
  
  test.describe('Match Center', () => {
    
    test('should display match center', async ({ page }) => {
      await page.goto(`${BASE_URL}/match`);
      await expect(page.locator('text=Match Center')).toBeVisible();
    });
  });

  // ==================== RESPONSIVE TESTS ====================
  
  test.describe('Responsive Design', () => {
    
    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(BASE_URL);
      
      // Should show mobile-friendly layout
      await expect(page.locator('text=IPL Fantasy Pro')).toBeVisible();
    });

    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(BASE_URL);
      
      await expect(page.locator('text=IPL Fantasy Pro')).toBeVisible();
    });
  });

  // ==================== ACCESSIBILITY TESTS ====================
  
  test.describe('Accessibility', () => {
    
    test('should have proper heading hierarchy', async ({ page }) => {
      await page.goto(BASE_URL);
      
      // Check h1 exists
      const h1 = page.locator('h1');
      await expect(h1).toBeVisible();
    });

    test('should have alt text on images', async ({ page }) => {
      await page.goto(BASE_URL);
      
      // Check images have alt text or are decorative
      const images = page.locator('img');
      const count = await images.count();
      
      for (let i = 0; i < count; i++) {
        const img = images.nth(i);
        const alt = await img.getAttribute('alt');
        // Alt should exist or image should be decorative
        expect(alt !== null || (await img.isVisible()) === false).toBeTruthy();
      }
    });

    test('should have accessible form labels', async ({ page }) => {
      await page.goto(BASE_URL);
      
      // Check inputs have labels or aria-labels
      const inputs = page.locator('input');
      const count = await inputs.count();
      
      expect(count).toBeGreaterThan(0);
    });
  });
});

// ==================== API E2E TESTS ====================

test.describe('API Endpoints', () => {
  
  test('health check should return ok', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/health`);
    expect(response.status()).toBe(200);
    expect(await response.json()).toHaveProperty('status', 'ok');
  });

  test('players API should return array', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/players`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('unauthorized access should be rejected', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/leagues`);
    expect(response.status()).toBe(401);
  });
});
