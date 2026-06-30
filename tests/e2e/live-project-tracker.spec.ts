import { test, expect } from '@playwright/test';

test.describe('HAS Live Project Tracker Command Center', () => {
  test('verifies the unified project tracker cockpit and tab routing', async ({ page }) => {
    // Navigate to page
    await page.goto('/');

    // Click sidebar "Project Tracker" tab
    const trackerNav = page.locator('#nav-live-project-tracker');
    await expect(trackerNav).toBeVisible();
    await trackerNav.click();

    // 1. Sticky Top Status Bar
    const topBar = page.locator('h2:has-text("HAS Live Project Tracker")');
    await expect(topBar).toBeVisible();
    const readinessScore = page.locator('#topbar-readiness');
    await expect(readinessScore).toContainText('100%');

    // 2. RC Timeline
    const timelineContainer = page.locator('#timeline-rc30');
    await expect(timelineContainer).toBeVisible();
    await expect(timelineContainer).toContainText('RC30: Unified Project Tracker');

    // 3. Animated Flow Graph Canvas
    const canvasContainer = page.locator('#tracker-canvas-container');
    await expect(canvasContainer).toBeVisible();
    
    const svgEdges = page.locator('#tracker-svg-edges');
    await expect(svgEdges).toBeAttached();

    // 4. Panel telemetry
    const laneRuntime = page.locator('#lane-runtime-status');
    await expect(laneRuntime).toContainText('Active');
    const laneBrain = page.locator('#lane-brain-status');
    await expect(laneBrain).toContainText('Gated');

    // 5. Gate Matrix & Monetization sidecar
    const noDriftGate = page.locator('h4:has-text("No-Drift Gate")');
    await expect(noDriftGate).toBeVisible();

    const monetizationPanel = page.locator('#view-live-project-tracker h4:has-text("Monetization Sidecar")');
    await expect(monetizationPanel).toBeVisible();

    // 6. Interactive filter dropdown
    const filterSelect = page.locator('#tracker-filter-select');
    await expect(filterSelect).toBeVisible();
    await filterSelect.selectOption('p0');

    // 7. Human Escalation Queue
    const approvalQueue = page.locator('#tracker-approvals-queue');
    await expect(approvalQueue).toBeVisible();

    // 8. Event Console Tab Switch
    const testTabBtn = page.locator('#tab-tracker-tests');
    await expect(testTabBtn).toBeVisible();
    await testTabBtn.click();

    const consoleFeed = page.locator('#tracker-console-feed');
    await expect(consoleFeed).toContainText('test_monetization_audit');
  });
});
