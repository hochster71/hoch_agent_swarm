import { test, expect } from '@playwright/test';

test.use({
  extraHTTPHeaders: {
    'x-vercel-protection-bypass': 'dlA54TQbDACNTPc8B9DUyyKqhtD3BCD9'
  }
});

test.describe('Epic Fury Staging Asset Loading Tests', () => {
  test('Verify staging homepage and static assets load successfully without TLS or console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    const failedAssets: string[] = [];

    // Capture console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Capture network requests and verify response statuses
    page.on('response', (response) => {
      const url = response.url();
      const status = response.status();
      if (url.includes('/_next/static') && (status < 200 || status >= 400)) {
        failedAssets.push(`${url} returned status ${status}`);
      }
    });

    // Go to staging URL
    const targetUrl = 'https://epic-fury-2026-4hjkgwv9v-us-is-ir-war-2026.vercel.app';
    await page.goto(targetUrl);

    // Verify the page title
    await expect(page).toHaveTitle(/EPIC FURY/i);

    // Verify no static asset load failures
    expect(failedAssets).toEqual([]);

    // Verify no console errors for static files
    const staticConsoleErrors = consoleErrors.filter(err => err.includes('_next/static'));
    expect(staticConsoleErrors).toEqual([]);
  });
});
