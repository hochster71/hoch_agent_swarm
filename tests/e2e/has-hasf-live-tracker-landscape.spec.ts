import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Load secrets from ~/.hoch-secrets/has-tracker.env if it exists
const secretsPath = path.join(process.env.HOME || '', '.hoch-secrets', 'has-tracker.env');
let username = 'admin';
let password = 'change-this-password';
let port = '3001';

if (fs.existsSync(secretsPath)) {
  const content = fs.readFileSync(secretsPath, 'utf8');
  content.split(/\r?\n/).forEach(line => {
    const idx = line.indexOf('=');
    if (idx !== -1) {
      const key = line.slice(0, idx).trim();
      const val = line.slice(idx + 1).trim();
      if (key === 'TRACKER_USER') username = val;
      if (key === 'TRACKER_PASSWORD') password = val;
      if (key === 'TRACKER_PORT') port = val;
    }
  });
}

test.use({
  baseURL: `http://localhost:${port}`,
  httpCredentials: {
    username,
    password
  }
});

test.describe('HAS/HASF Live Project Tracker Landscape E2E', () => {
  test('verifies landscape view renders and interacts correctly', async ({ page }) => {
    // Navigate directly to local tracker
    await page.goto('/');

    // Verify page loads
    await expect(page).toHaveTitle('HAS/HASF Live Project Tracker');

    // Click on the Landscape tab button
    const landscapeTabBtn = page.locator('#tab-landscape');
    await expect(landscapeTabBtn).toBeVisible();
    await landscapeTabBtn.click();

    // Verify landscape tab view becomes visible
    const landscapeView = page.locator('#view-landscape');
    await expect(landscapeView).toBeVisible();

    // Verify Landscape endpoint responds OK
    const landscapeRes = await page.request.get('/api/landscape');
    expect(landscapeRes.status()).toBe(200);
    const landscapeJson = await landscapeRes.json();
    expect(landscapeJson.northstar).toBeDefined();
    expect(landscapeJson.domains).toBeDefined();

    // Verify Northstar strip is visible
    const verdict = page.locator('#ls-verdict');
    await expect(verdict).toBeVisible();
    
    // Verify Domain Lanes grid
    const lanesContainer = page.locator('#landscapeLanes');
    await expect(lanesContainer).toBeVisible();
    const laneCols = lanesContainer.locator('.lane-col');
    await expect(laneCols.first()).toBeVisible();

    // Hover over the first domain lane to verify tooltips
    const firstLane = laneCols.first();
    await firstLane.hover();
    const tooltip = page.locator('#tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toHaveAttribute('role', 'tooltip');
    await expect(firstLane).toHaveAttribute('aria-describedby', 'tooltip');

    // Dismiss tooltip
    await page.keyboard.press('Escape');
    await expect(tooltip).not.toBeVisible();
    await page.mouse.move(0, 0);

    // Click on domain lane to open details drawer
    await firstLane.click();
    const drawer = page.locator('#drawer');
    await expect(drawer).toBeVisible();

    // Close details drawer
    const closeBtn = drawer.locator('button').first();
    await closeBtn.click();
    await expect(drawer).not.toBeVisible();
  });
});
