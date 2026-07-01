import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('RC46 Revenue Action Queue E2E Tests', () => {
  test('1. Verify Revenue Action Queue and elements render correctly', async ({ page }) => {
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));

    // Navigate to PERT Command Center
    await page.goto('http://127.0.0.1:8765/');

    // Validate both Revenue Readiness and Revenue Action Queue panels render
    const readinessPanel = page.locator('#revenue-readiness-panel');
    await expect(readinessPanel).toBeVisible();

    const actionQueuePanel = page.locator('#revenue-action-queue-panel');
    await expect(actionQueuePanel).toBeVisible();

    // Verify freshness badge
    const queueFreshnessBadge = page.locator('#revenue-action-queue-freshness-badge');
    await expect(queueFreshnessBadge).toBeVisible();
    const freshnessText = await queueFreshnessBadge.innerText();
    expect(['FRESH', 'STALE', 'DEGRADED', 'UNKNOWN']).toContain(freshnessText.trim());

    // Wait for elements to populate dynamically
    await expect(page.locator('#action-row-1')).toBeVisible();

    // Validate that at least 5 action items are rendered
    const rows = page.locator('#action-queue-tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(5);

    // Validate top-ranked action is visible and has rank-number-top and row highlight
    const topRow = page.locator('#action-queue-tbody tr.action-row-highlight');
    await expect(topRow).toBeVisible();

    const topRankCell = topRow.locator('.rank-number-top');
    await expect(topRankCell).toBeVisible();
    const topRankText = await topRankCell.innerText();
    expect(topRankText.trim()).toBe('1');

    // Verify that every action row has project, title, agent, status, and evidence links
    for (let i = 0; i < 5; i++) {
      const row = rows.nth(i);
      await expect(row.locator('td').nth(0)).toBeVisible(); // Rank
      await expect(row.locator('td').nth(1)).toBeVisible(); // Project
      await expect(row.locator('td').nth(2)).toBeVisible(); // Title & details
      await expect(row.locator('td').nth(3)).toBeVisible(); // Agent
      await expect(row.locator('td').nth(4)).toBeVisible(); // Rev impact
      await expect(row.locator('td').nth(5)).toBeVisible(); // Sec impact
      await expect(row.locator('td').nth(6)).toBeVisible(); // Dep impact
      await expect(row.locator('td').nth(7)).toBeVisible(); // Status
      await expect(row.locator('td').nth(8)).toBeVisible(); // Evidence links

      // Validate no double percent signs (%%)
      const revText = await row.locator('td').nth(4).innerText();
      const secText = await row.locator('td').nth(5).innerText();
      const depText = await row.locator('td').nth(6).innerText();
      expect(revText.trim()).not.toContain('%%');
      expect(secText.trim()).not.toContain('%%');
      expect(depText.trim()).not.toContain('%%');
      expect(revText.trim()).toMatch(/^\d+%$/);
    }
  });

  test('2. Verify degraded or missing queue state is visible', async ({ page }) => {
    // Navigate to PERT Command Center
    await page.goto('http://127.0.0.1:8765/');

    // Locate action queue container
    const queueTbody = page.locator('#action-queue-tbody');
    await expect(queueTbody).toBeVisible();

    // Temporarily rename the queue file to simulate missing file
    const projectRoot = path.dirname(path.dirname(path.dirname(__filename)));
    const queueFile = path.join(projectRoot, 'has_live_project_tracker', 'data', 'revenue_action_queue.json');
    const backupFile = queueFile + '.bak';

    if (fs.existsSync(queueFile)) {
      fs.renameSync(queueFile, backupFile);
    }

    try {
      // Reload page to fetch state without file
      await page.goto('http://127.0.0.1:8765/');

      // Verify freshness badge is DEGRADED
      const queueFreshnessBadge = page.locator('#revenue-action-queue-freshness-badge');
      await expect(queueFreshnessBadge).toHaveText('DEGRADED');

      // Verify that the table shows degraded warning row
      const warningRow = page.locator('#action-queue-tbody tr');
      await expect(warningRow).toContainText('DEGRADED / STALE');
    } finally {
      // Restore file
      if (fs.existsSync(backupFile)) {
        fs.renameSync(backupFile, queueFile);
      }
    }
  });
});
