import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../support/epic-fury-auth';

// D4 (founder-ratified 2026-07-13): behavioral contracts on a mobile viewport.
test.describe('Epic Fury Mobile Viewport Tests', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('1. Authenticated dashboard renders responsively on mobile', async ({ page }) => {
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com', 'admin'); // real session
    await page.goto('http://localhost:3003/dashboard', { waitUntil: 'domcontentloaded' });

    // D4 item 1 — reaches the route, shell renders, no horizontal overflow blowout.
    expect(page.url()).toContain('/dashboard');
    await expect(page.locator('body')).toBeVisible();
    const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollW).toBeLessThanOrEqual(375 + 24); // no gross horizontal overflow at 375px

    // D4 item 2 — product identity via metadata.
    await expect(page).toHaveTitle(/epic fury/i);

    // D4 item 4 — entitled identity: no paywall CTA.
    await expect(page.locator('text=Unlock Full Intelligence Access')).toHaveCount(0);
  });
});
