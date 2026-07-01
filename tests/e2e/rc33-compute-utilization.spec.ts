import { test, expect } from '@playwright/test';
import * as net from 'net';

test.describe('RC33 Compute Utilization Swarm Scheduler E2E tests', () => {
  test('navigates to PERT Command Center and validates Swarm Scheduler panel and metrics', async ({ page }) => {
    // Capture console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // 1. Verify Swarm Scheduler Panel is visible
    const schedulerPanel = page.locator('#swarm-scheduler-panel');
    await expect(schedulerPanel).toBeVisible();
    await expect(schedulerPanel).toContainText('Compute Swarm Scheduler');

    // 2. Verify state badge
    const stateBadge = page.locator('#scheduler-state');
    await expect(stateBadge).toBeVisible();
    const stateText = await stateBadge.innerText();
    expect(['ACTIVE', 'IDLE']).toContain(stateText);

    // 3. Verify resource metrics
    const utilization = page.locator('#swarm-utilization');
    await expect(utilization).toBeVisible();
    await expect(utilization).toContainText('%');

    const activeWorkers = page.locator('#swarm-active-workers');
    await expect(activeWorkers).toBeVisible();
    await expect(activeWorkers).toContainText('/ 5');

    const cores = page.locator('#swarm-cores');
    await expect(cores).toBeVisible();
    await expect(cores).toContainText('Cores');

    const memory = page.locator('#swarm-memory');
    await expect(memory).toBeVisible();
    await expect(memory).toContainText('GB');

    // Ensure no console errors occurred during dashboard load
    expect(consoleErrors).toEqual([]);
  });

  test('proves that public port 3012 remains unreachable (HOCH-200 constraint)', async () => {
    const checkPort = (): Promise<boolean> => {
      return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(2000);
        socket.on('connect', () => {
          socket.destroy();
          resolve(true); // exposed
        });
        socket.on('timeout', () => {
          socket.destroy();
          resolve(false); // unreachable
        });
        socket.on('error', () => {
          socket.destroy();
          resolve(false); // unreachable
        });
        socket.connect(3012, '50.116.41.183');
      });
    };

    const isExposed = await checkPort();
    expect(isExposed).toBe(false);
  });
});
