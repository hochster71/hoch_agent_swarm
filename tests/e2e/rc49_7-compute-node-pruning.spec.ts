import { test, expect } from '@playwright/test';

test.describe('RC49.7 Compute Node Pruning E2E tests', () => {
  test('navigates to PERT Command Center and validates pruned compute nodes', async ({ page }) => {
    // Capture console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // 1. Wait for dashboard elements to load
    await page.waitForSelector('#hoch-pods-compute-rail');

    // 2. Verify active nodes are present in the Compute Rail
    const m5ProRail = page.locator('#compute-rail-node-m5-pro-mbp');
    await expect(m5ProRail).toBeVisible();

    const dockerRuntimeRail = page.locator('#compute-rail-node-docker-runtime');
    await expect(dockerRuntimeRail).toBeVisible();

    const remoteVpsRail = page.locator('#compute-rail-node-optional-remote-vps');
    await expect(remoteVpsRail).toBeVisible();

    // 3. Verify active nodes are present in the Scheduler Node Card Matrix
    const m5ProMatrix = page.locator('#scheduler-node-card-m5-pro-mbp');
    await expect(m5ProMatrix).toBeVisible();

    const dockerRuntimeMatrix = page.locator('#scheduler-node-card-docker-runtime');
    await expect(dockerRuntimeMatrix).toBeVisible();

    const remoteVpsMatrix = page.locator('#scheduler-node-card-optional-remote-vps');
    await expect(remoteVpsMatrix).toBeVisible();

    // 4. Verify retired/pruned nodes are NOT present in the Compute Rail
    const m4MbpRail = page.locator('#compute-rail-node-m4-mbp');
    await expect(m4MbpRail).not.toBeAttached();

    const imacRail = page.locator('#compute-rail-node-imac-24');
    await expect(imacRail).not.toBeAttached();

    const dellRail = page.locator('#compute-rail-node-dell-neo');
    await expect(dellRail).not.toBeAttached();

    const localModelsRail = page.locator('#compute-rail-node-local-models');
    await expect(localModelsRail).not.toBeAttached();

    // 5. Verify retired/pruned nodes are NOT present in the Scheduler Matrix
    const m4MbpMatrix = page.locator('#scheduler-node-card-m4-mbp');
    await expect(m4MbpMatrix).not.toBeAttached();

    const imacMatrix = page.locator('#scheduler-node-card-imac-24');
    await expect(imacMatrix).not.toBeAttached();

    const dellMatrix = page.locator('#scheduler-node-card-dell-neo');
    await expect(dellMatrix).not.toBeAttached();

    const localModelsMatrix = page.locator('#scheduler-node-card-local-models');
    await expect(localModelsMatrix).not.toBeAttached();

    // Ensure no console errors occurred during dashboard load
    expect(consoleErrors).toEqual([]);
  });
});
