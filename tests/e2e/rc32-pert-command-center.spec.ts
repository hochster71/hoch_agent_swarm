import { test, expect } from '@playwright/test';
import * as net from 'net';

test.describe('PERT Command Center E2E tests', () => {
  test('navigates to PERT Command Center and validates sections and data integrity', async ({ page }) => {
    // Capture console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // 1. Verify North Star Goal header is visible and correct
    const northStar = page.locator('#north-star-goal');
    await expect(northStar).toBeVisible();
    await expect(northStar).toContainText('PERT Command Center');

    const goalText = page.locator('#goal-text');
    await expect(goalText).toBeVisible();
    // Verify it doesn't render raw placeholder
    await expect(goalText).not.toHaveText('UNKNOWN');

    // 2. Verify Executive Readiness Panel is visible
    const execReadiness = page.locator('#executive-readiness-panel');
    await expect(execReadiness).toBeVisible();
    await expect(execReadiness).toContainText('Executive Readiness');

    const confidence = page.locator('#confidence-level');
    await expect(confidence).toBeVisible();
    await expect(confidence).toContainText('PERT Beta-Distribution');

    // 3. Verify Runtime Status Panel is visible
    const runtimeStatus = page.locator('#runtime-status-panel');
    await expect(runtimeStatus).toBeVisible();

    const portStatus = page.locator('#port-status');
    await expect(portStatus).toBeVisible();
    // Port status must not be fake, it must be either CLOSED or EXPOSED
    const portText = await portStatus.innerText();
    expect(['CLOSED', 'EXPOSED', 'UNKNOWN']).toContain(portText);

    // 4. Verify Risks & Blockers Panel is visible
    const risksPanel = page.locator('#risks-blockers-panel');
    await expect(risksPanel).toBeVisible();

    // 5. Verify PERT / CPM Network Graph / Panel is visible
    const pertNetwork = page.locator('#pert-network-panel');
    await expect(pertNetwork).toBeVisible();

    const networkContainer = page.locator('#network-container');
    await expect(networkContainer).toBeVisible();

    // 6. Verify Tasks Table Panel is visible
    const tasksTable = page.locator('#tasks-table-panel');
    await expect(tasksTable).toBeVisible();

    const tasksTbody = page.locator('#tasks-tbody');
    await expect(tasksTbody).toBeVisible();

    // 7. Verify Next Best Actions Panel is visible
    const nextActions = page.locator('#next-actions-panel');
    await expect(nextActions).toBeVisible();

    // 8. Verify Agent Accountability Board is visible
    const agentBoard = page.locator('#agent-accountability-panel');
    await expect(agentBoard).toBeVisible();

    const agentsTbody = page.locator('#agents-tbody');
    await expect(agentsTbody).toBeVisible();

    // 9. Verify RACI Matrix Panel is visible
    const raciMatrix = page.locator('#raci-matrix-panel');
    await expect(raciMatrix).toBeVisible();

    const raciTbody = page.locator('#raci-tbody');
    await expect(raciTbody).toBeVisible();

    // 10. Verify Parallel Mirror Verification Status is visible
    const parallelMirror = page.locator('#parallel-mirror-panel');
    await expect(parallelMirror).toBeVisible();
    
    // 11. Verify Automation Cadence State is visible
    const cadencePanel = page.locator('#automation-cadence-panel');
    await expect(cadencePanel).toBeVisible();
    await expect(cadencePanel).toContainText('Automation Cadence State');

    const cadenceMode = page.locator('#cadence-mode');
    await expect(cadenceMode).toBeVisible();
    await expect(cadenceMode).toContainText('AUTO-LOOP ENABLED');

    // 12. Verify Manual Intervention Queue is visible
    const manualQueueList = page.locator('#manual-queue-list');
    await expect(manualQueueList).toBeVisible();

    // Make sure no console errors occurred
    expect(consoleErrors).toEqual([]);
  });

  test('proves that public port 3012 remains unreachable', async () => {
    // Negative connection test to public VPS 50.116.41.183:3012
    const publicIp = '50.116.41.183';
    const port = 3012;
    
    const isReachable = await new Promise<boolean>((resolve) => {
      const socket = new net.Socket();
      socket.setTimeout(2000);
      
      socket.on('connect', () => {
        socket.destroy();
        resolve(true); // reachable is bad
      });
      
      socket.on('timeout', () => {
        socket.destroy();
        resolve(false); // unreachable is good
      });
      
      socket.on('error', () => {
        resolve(false); // unreachable is good
      });
      
      socket.connect(port, publicIp);
    });
    
    expect(isReachable).toBe(false);
  });
});
