import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../support/epic-fury-auth';

// D4 (founder-ratified 2026-07-13): behavioral contracts, not brittle presentation selectors.
// Product identity via stable metadata; no exact visible-heading string; no removed routes.
test.describe('Epic Fury Smoke Tests', () => {
  test('1. Authenticated dashboard renders the app shell (product identity via metadata)', async ({ page }) => {
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com', 'admin'); // real session, real JWT, real middleware
    await page.goto('http://localhost:3003/dashboard', { waitUntil: 'domcontentloaded' });

    // D4 item 1 — authenticated navigation: reaches the supported route, no auth loop / no error page.
    expect(page.url()).toContain('/dashboard');
    await expect(page.locator('body')).toBeVisible();
    // no auth-loop back to /login, no server-error surface
    expect(page.url()).not.toContain('/login');
    await expect(page.locator('text=/Application error|500|Internal Server Error/i')).toHaveCount(0);

    // D4 item 2 — product identity through stable metadata (the configured product name),
    // NOT an exact visible heading string.
    await expect(page).toHaveTitle(/epic fury/i);

    // D4 item 4 — an entitled (admin) identity is NOT shown the public upgrade/paywall CTA.
    await expect(page.locator('text=Unlock Full Intelligence Access')).toHaveCount(0);
  });
});
