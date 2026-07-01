import { test, expect } from '@playwright/test';

test.describe('RC39 Telemetry Truth E2E tests', () => {
  test('navigates to PERT Command Center and validates Telemetry Provenance tooltips', async ({ page }) => {
    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // Helper to verify title contains provenance details (using toHaveAttribute to auto-retry)
    const checkProvenanceTooltip = async (selector: string) => {
      const element = page.locator(selector);
      await expect(element).toBeVisible();
      await expect(element).toHaveAttribute('title', /Source:.*Freshness:/);
    };

    // Check widgets
    await checkProvenanceTooltip('#readiness-score');
    await checkProvenanceTooltip('#metric-tests');
    await checkProvenanceTooltip('#metric-evidence');
    await checkProvenanceTooltip('#metric-accountability');
    await checkProvenanceTooltip('#metric-time-saved');
    await checkProvenanceTooltip('#backend-status');
    await checkProvenanceTooltip('#relay-status');
    await checkProvenanceTooltip('#port-status');
    await checkProvenanceTooltip('#guardrail-export');

    // Check tailnet workers table status tooltip
    const workerStatus = page.locator('#workers-table-body td span').first();
    await expect(workerStatus).toBeVisible();
    await expect(workerStatus).toHaveAttribute('title', /Source:.*Freshness:/);
  });
});
