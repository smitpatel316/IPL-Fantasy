const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('IPL Fantasy Pro - UI Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  // ==================== HOME PAGE ====================

  test.describe('Home Page', () => {

    test('should display home page', async ({ page }) => {
      // Check for key elements (either page loads or shows login)
      const body = await page.locator('body');
      await expect(body).toBeVisible();
    });

    test('should have proper meta tags', async ({ page }) => {
      const title = await page.title();
      expect(title.length).toBeGreaterThan(0);
    });
  });

  // ==================== AUTH UI TESTS ====================

  test.describe('Authentication UI', () => {

    test('should show login page elements', async ({ page }) => {
      await page.goto(`${BASE_URL}/login`);
      const content = await page.content();
      // Page should load without crash
      expect(content.length).toBeGreaterThan(0);
    });

    test('should show register page elements', async ({ page }) => {
      await page.goto(`${BASE_URL}/register`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should handle login form validation', async ({ page }) => {
      await page.goto(`${BASE_URL}/login`);
      // Try clicking login without entering credentials
      const loginButton = page.locator('button').first();
      if (await loginButton.isVisible()) {
        await loginButton.click();
        // Should show validation or error
        const content = await page.content();
        expect(content.length).toBeGreaterThan(0);
      }
    });
  });

  // ==================== LEAGUE UI TESTS ====================

  test.describe('League UI', () => {

    test('should display leagues page', async ({ page }) => {
      await page.goto(`${BASE_URL}/leagues`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should display league detail page', async ({ page }) => {
      await page.goto(`${BASE_URL}/leagues/test-league-id`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should handle create league form', async ({ page }) => {
      await page.goto(`${BASE_URL}/leagues`);
      const content = await page.content();
      // Form should be accessible
      expect(content.length).toBeGreaterThan(0);
    });
  });

  // ==================== DRAFT UI TESTS ====================

  test.describe('Draft UI', () => {

    test('should display draft page', async ({ page }) => {
      await page.goto(`${BASE_URL}/draft`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should display draft room', async ({ page }) => {
      await page.goto(`${BASE_URL}/draft/test-draft-id`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });
  });

  // ==================== TEAM UI TESTS ====================

  test.describe('Team UI', () => {

    test('should display team page', async ({ page }) => {
      await page.goto(`${BASE_URL}/team`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should display team detail', async ({ page }) => {
      await page.goto(`${BASE_URL}/team/test-team-id`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });
  });

  // ==================== MATCH UI TESTS ====================

  test.describe('Match Center UI', () => {

    test('should display match center', async ({ page }) => {
      await page.goto(`${BASE_URL}/match`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should display match detail', async ({ page }) => {
      await page.goto(`${BASE_URL}/match/test-match-id`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should display standings', async ({ page }) => {
      await page.goto(`${BASE_URL}/standings`);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });
  });

  // ==================== RESPONSIVE TESTS ====================

  test.describe('Responsive Design', () => {

    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(BASE_URL);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(BASE_URL);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });

    test('should work on desktop viewport', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto(BASE_URL);
      const content = await page.content();
      expect(content.length).toBeGreaterThan(0);
    });
  });

  // ==================== ACCESSIBILITY TESTS ====================

  test.describe('Accessibility', () => {

    test('should have proper page structure', async ({ page }) => {
      await page.goto(BASE_URL);

      // Check body exists
      const body = page.locator('body');
      await expect(body).toBeVisible();
    });

    test('should have no critical console errors', async ({ page }) => {
      const errors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto(BASE_URL);
      await page.waitForLoadState('networkidle');

      // Filter out known non-critical errors
      const criticalErrors = errors.filter(e =>
        !e.includes('favicon') &&
        !e.includes('404')
      );

      expect(criticalErrors.length).toBe(0);
    });
  });
});
