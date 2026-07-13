import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../support/epic-fury-auth';

test.describe('Epic Fury Mobile Viewport Tests', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('1. Verify mobile layout responsiveness', async ({ page }) => {
    // Log in as founder
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com', 'admin');  // real magic-link auth (no demo bypass)
    await page.goto('http://localhost:3003/dashboard');

    // Confirm that mobile HUD controls adjust safely
    const layoutHeader = page.locator('text=EPIC FURY').first();
    await expect(layoutHeader).toBeVisible();

    // Confirm upgrade CTA behaves safely on mobile width
    await page.goto('http://localhost:3003/dashboard');
    const banner = page.locator('#internal-access-banner');
    await expect(banner).toBeVisible();
  });
});
