import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../support/epic-fury-auth';

test.describe('Epic Fury Smoke Tests', () => {
  test('1. Verify dashboard feed renders core components', async ({ page }) => {
    // Log in as admin
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com', 'admin');  // real magic-link auth (no demo bypass)
    await page.goto('http://localhost:3003/dashboard');

    // Confirm that the feed layout is visible
    const layoutHeader = page.locator('text=EPIC FURY').first();
    await expect(layoutHeader).toBeVisible();

    // Verify sidebar navigation links exist
    const settingsLink = page.locator('a[href="/dashboard/settings"]');
    await expect(settingsLink).toBeVisible();
  });
});
