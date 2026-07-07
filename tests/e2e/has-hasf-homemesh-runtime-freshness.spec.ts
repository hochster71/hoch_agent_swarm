import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test('Verify HomeMesh Spatial Graph UI Freshness', async ({ page }) => {
    // Set standard viewport size
    await page.setViewportSize({ width: 1280, height: 800 });

    // Navigate to the HomeMesh UI
    await page.goto('http://127.0.0.1:8000/prototype/homemesh');

    // Click Refresh Discovery to ensure fresh state
    const refreshBtn = page.locator('button:has-text("Refresh Discovery")');
    await expect(refreshBtn).toBeVisible();
    
    // Accept dialog when clicking refresh
    page.once('dialog', async dialog => {
        await dialog.accept();
    });
    await refreshBtn.click();
    await page.waitForTimeout(2000);

    // Fetch live API data to verify counts
    const assetsResponse = await page.request.get('http://127.0.0.1:8000/api/homemesh/assets');
    const assets = await assetsResponse.json();

    const unknownsResponse = await page.request.get('http://127.0.0.1:8000/api/homemesh/unknown-devices');
    const unknowns = await unknownsResponse.json();

    // Verify last updated timestamp is visible and updated
    const lastUpdated = page.locator('#graph-last-updated');
    await expect(lastUpdated).toBeVisible();
    const updatedText = await lastUpdated.innerText();
    expect(updatedText).not.toBe('Never');

    // Verify Total Devices count matches assets length
    const totalDevicesStat = page.locator('#stat-total-devices');
    await expect(totalDevicesStat).toHaveText(String(assets.length));

    // Verify Untrusted/Unknown count matches unknowns length
    const unknownDevicesStat = page.locator('#stat-unknown-devices');
    await expect(unknownDevicesStat).toHaveText(String(unknowns.length));

    // Fetch source-status details to check source statuses
    const statusResponse = await page.request.get('http://127.0.0.1:8000/api/homemesh/source-status');
    const statuses = await statusResponse.json();

    const udmStatus = statuses.find(s => s.source_name === 'udm').status.toUpperCase();
    const haStatus = statuses.find(s => s.source_name === 'home_assistant').status.toUpperCase();

    // Verify Controller Sources status displays in the UI
    const udmEl = page.locator('#status-udm');
    const haEl = page.locator('#status-ha');
    await expect(udmEl).toHaveText(udmStatus);
    await expect(haEl).toHaveText(haStatus);

    // Verify Persistence is active
    const persistenceEl = page.locator('#status-persistence');
    await expect(persistenceEl).toHaveText('ACTIVE');

    // Verify Classification Breakdown counts
    const liveCount = assets.filter(d => d.source_classification && d.source_classification.startsWith('live_') && d.online_status === 'online').length;
    const manualCount = assets.filter(d => d.source_classification === 'manual_declared').length;
    const mockCount = assets.filter(d => d.source_classification === 'sample_mock').length;
    const staleCount = assets.filter(d => d.online_status === 'stale').length;
    const failClosedCount = assets.filter(d => d.automation_allowed === false).length;

    await expect(page.locator('#stat-live-count')).toHaveText(String(liveCount));
    await expect(page.locator('#stat-manual-count')).toHaveText(String(manualCount));
    await expect(page.locator('#stat-mock-count')).toHaveText(String(mockCount));
    await expect(page.locator('#stat-stale-count')).toHaveText(String(staleCount));
    await expect(page.locator('#stat-fail-closed')).toHaveText(String(failClosedCount));

    // Hover on a device node element to reveal hover card details
    const firstNode = page.locator('.device-node').first();
    await expect(firstNode).toBeVisible();
    await firstNode.hover();
    await page.waitForTimeout(500);

    // Verify hover card is visible and has required elements
    const hoverCard = page.locator('#node-hover-card');
    await expect(hoverCard).toBeVisible();
    await expect(hoverCard).toContainText('Classification:');
    await expect(hoverCard).toContainText('Evidence:');
    await expect(hoverCard).toContainText('Last Seen:');

    // Save screenshot
    const screenshotDir = path.join(__dirname, '..', '..', 'docs', 'evidence', 'ui', 'screenshots');
    fs.mkdirSync(screenshotDir, { recursive: true });
    const screenshotPath = path.join(screenshotDir, 'homemesh-runtime-freshness.png');
    await page.screenshot({ path: screenshotPath });
    console.log(`Saved HomeMesh UI Freshness screenshot to: ${screenshotPath}`);
});
