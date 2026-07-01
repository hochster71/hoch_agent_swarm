import { test, expect } from '@playwright/test';

test.describe('RC37 Job Dispatch & Goal Contribution Metrics E2E tests', () => {
  test('navigates to PERT Command Center and validates dynamic job dispatch records', async ({ page }) => {
    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // Verify job dispatch panel is visible
    const dispatchPanel = page.locator('#job-dispatch-panel');
    await expect(dispatchPanel).toBeVisible();
    await expect(dispatchPanel).toContainText('Job Dispatch & Goal Contribution');

    // Verify dispatch table body exists
    const dispatchTableBody = page.locator('#dispatch-table-body');
    await expect(dispatchTableBody).toBeVisible();

    // Verify at least one row is rendered or default empty text is displayed
    const rowsCount = await dispatchTableBody.locator('tr').count();
    if (rowsCount > 0) {
      const firstRow = dispatchTableBody.locator('tr').first();
      await expect(firstRow).toContainText('%');
    } else {
      await expect(dispatchTableBody).toContainText('No jobs dispatched yet');
    }
  });
});
