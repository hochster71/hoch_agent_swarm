import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test('Verify HomeMesh Spatial Graph UI', async ({ page }) => {
    // Set standard viewport size
    await page.setViewportSize({ width: 1280, height: 800 });

    // Navigate to the HomeMesh UI
    await page.goto('http://127.0.0.1:8000/prototype/homemesh');

    // Wait for the page content and fetch requests to finish
    await page.waitForTimeout(2000);

    // Assert heading shows HomeMesh Spatial Graph
    const heading = page.locator('header h1');
    await expect(heading).toContainText('HomeMesh Spatial Graph');

    // Assert sidebar navigation exists
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toBeVisible();

    // Verify tabs list contains required items (6 tabs + 3 Swarm Hub links)
    const navItems = page.locator('.nav-item');
    await expect(navItems).toHaveCount(9);


    // Verify at least one node is present
    const nodes = page.locator('.node-element');
    const nodeCount = await nodes.count();
    console.log(`Discovered ${nodeCount} nodes on the topology graph.`);
    expect(nodeCount).toBeGreaterThan(0);

    // Save screenshot
    const screenshotDir = path.join(__dirname, '..', '..', 'docs', 'evidence', 'ui', 'screenshots');
    fs.mkdirSync(screenshotDir, { recursive: true });
    const screenshotPath = path.join(screenshotDir, 'homemesh-spatial-graph-current.png');
    await page.screenshot({ path: screenshotPath });
    console.log(`Saved HomeMesh UI screenshot to: ${screenshotPath}`);
});
