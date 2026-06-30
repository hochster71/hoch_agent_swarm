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

test.describe('HAS/HASF Live Project Tracker Gap Analysis E2E', () => {
  test('verifies gap analysis tab renders and interacts correctly', async ({ page }) => {
    // Navigate directly to local tracker
    await page.goto('/');

    // Verify page loads
    await expect(page).toHaveTitle('HAS/HASF Live Project Tracker');

    // Click on the Gap Analysis tab button
    const gapsTabBtn = page.locator('#tab-gaps');
    await expect(gapsTabBtn).toBeVisible();
    await gapsTabBtn.click();

    // Verify gap view container becomes visible
    const gapsView = page.locator('#view-gaps');
    await expect(gapsView).toBeVisible();

    // Verify Gaps endpoint responds OK
    const gapsRes = await page.request.get('/api/gaps');
    expect(gapsRes.status()).toBe(200);
    const gapsJson = await gapsRes.json();
    expect(gapsJson.gaps).toBeDefined();
    expect(gapsJson.coverage_matrix).toBeDefined();

    // Verify Gap Register table rows exist
    const gapsList = page.locator('#gapsListRows');
    await expect(gapsList).toBeVisible();
    const gapRows = gapsList.locator('tr');
    await expect(gapRows.first()).toBeVisible();

    // Verify Coverage Matrix capability cells exist
    const matrixRows = page.locator('#matrixRows');
    await expect(matrixRows).toBeVisible();
    const cell = matrixRows.locator('.matrix-cell').first();
    await expect(cell).toBeVisible();

    // Hover over a matrix cell to verify tooltips
    await cell.hover();
    const tooltip = page.locator('#tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toHaveAttribute('role', 'tooltip');

    // Dismiss tooltip
    await page.keyboard.press('Escape');
    await expect(tooltip).not.toBeVisible();
    await page.mouse.move(0, 0);

    // Click on risk register table row to open details drawer
    const risksRows = page.locator('#risksRows');
    await expect(risksRows).toBeVisible();
    const firstRisk = risksRows.locator('tr').first();
    await expect(firstRisk).toBeVisible();

    await firstRisk.click();
    const drawer = page.locator('#drawer');
    await expect(drawer).toBeVisible();

    // Close details drawer
    const closeBtn = drawer.locator('button').first();
    await closeBtn.click();
    await expect(drawer).not.toBeVisible();
  });
});
