import { test, expect } from '@playwright/test';

test.describe('PERT E2E Build and Critical Path Visualizer', () => {
  test('navigates to PERT E2E Build cockpit and verifies graph, critical path, duration, and gates', async ({ page }) => {
    // Capture console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to page
    await page.goto('http://127.0.0.1:8000');

    // Wait for sidebar nav item to load
    const pertNav = page.locator('#nav-pert-e2e-build');
    await expect(pertNav).toBeVisible();

    // Click the nav item
    await pertNav.click();

    // Verify view container becomes visible
    const pertView = page.locator('#view-pert-e2e-build');
    await expect(pertView).toBeVisible();

    // Verify all major elements are present
    const networkGraph = page.locator('#pert-e2e-network-graph');
    await expect(networkGraph).toBeVisible();

    const criticalPathLane = page.locator('#pert-critical-path-lane');
    await expect(criticalPathLane).toBeVisible();

    const durationTable = page.locator('#pert-task-duration-table');
    await expect(durationTable).toBeVisible();

    const slackTable = page.locator('#pert-slack-table');
    await expect(slackTable).toBeVisible();

    const gapBoard = page.locator('#pert-gap-board');
    await expect(gapBoard).toBeVisible();

    const buildTestGates = page.locator('#pert-build-test-gates');
    await expect(buildTestGates).toBeVisible();

    const runtimeGate = page.locator('#pert-runtime-gate');
    await expect(runtimeGate).toBeVisible();

    const financeGate = page.locator('#pert-finance-gate');
    await expect(financeGate).toBeVisible();

    const productionGate = page.locator('#pert-production-command-gate');
    await expect(productionGate).toBeVisible();

    const dockerGate = page.locator('#pert-docker-24x7-gate');
    await expect(dockerGate).toBeVisible();

    const evidenceCoverage = page.locator('#pert-evidence-coverage');
    await expect(evidenceCoverage).toBeVisible();

    const decision = page.locator('#pert-go-no-go-decision');
    await expect(decision).toBeVisible();

    // Check for console errors
    expect(consoleErrors).toEqual([]);
  });
});
