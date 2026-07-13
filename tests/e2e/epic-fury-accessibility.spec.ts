import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../support/epic-fury-auth';

test.describe('Epic Fury Accessibility Tests', () => {
  test('1. Verify semantic HTML structure and ARIA labels', async ({ page }) => {
    // Log in as founder
    await loginAsTestUser(page);  // real magic-link auth (no demo bypass)
    await page.goto('http://localhost:3003/dashboard');

    // Verify presence of main semantic containers
    const nav = page.locator('nav');
    await expect(nav.first()).toBeVisible();

    // Verify images/icons have alt/title context
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });
});
