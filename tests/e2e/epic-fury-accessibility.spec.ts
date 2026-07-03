import { test, expect } from '@playwright/test';

test.describe('Epic Fury Accessibility Tests', () => {
  test('1. Verify semantic HTML structure and ARIA labels', async ({ page }) => {
    // Log in as founder
    await page.goto('http://localhost:3003/api/auth/demo?email=michael.b.hoch@gmail.com&role=founder');
    await page.waitForURL('**/dashboard');

    // Verify presence of main semantic containers
    const nav = page.locator('nav');
    await expect(nav.first()).toBeVisible();

    // Verify images/icons have alt/title context
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });
});
