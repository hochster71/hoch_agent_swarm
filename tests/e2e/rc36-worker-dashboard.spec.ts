import { test, expect } from '@playwright/test';

test.describe('RC36 Worker Visibility & Utilization Dashboard E2E tests', () => {
  test('navigates to PERT Command Center and validates dynamic worker visibility and statuses', async ({ page }) => {
    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // Verify workers table body exists
    const tableBody = page.locator('#workers-table-body');
    await expect(tableBody).toBeVisible();

    // Verify MacBook Pro worker details
    const macbookRow = tableBody.locator('tr:has-text("michaels-macbook-pro")');
    await expect(macbookRow).toBeVisible();
    await expect(macbookRow).toContainText('primary_control_runtime');
    await expect(macbookRow).toContainText('100.103.155.4');

    // Verify hoch-relay-001 worker details
    const relayRow = tableBody.locator('tr:has-text("hoch-relay-001")');
    await expect(relayRow).toBeVisible();
    await expect(relayRow).toContainText('private_relay_worker');
    await expect(relayRow).toContainText('100.87.18.15');

    // Verify iPhone worker details
    const iphoneRow = tableBody.locator('tr:has-text("iphone-15-pro-max")');
    await expect(iphoneRow).toBeVisible();
    await expect(iphoneRow).toContainText('operator_mobile_monitor');
    await expect(iphoneRow).toContainText('100.102.221.87');
  });
});
