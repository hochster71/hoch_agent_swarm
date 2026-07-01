import { test, expect } from '@playwright/test';

test.describe('RC38 Goal Forecast & Monetization E2E tests', () => {
  test('navigates to PERT Command Center and validates Goal Forecast & Monetization panels', async ({ page }) => {
    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // Verify Goal Forecast panel visibility
    const forecastPanel = page.locator('#goal-forecast-panel');
    await expect(forecastPanel).toBeVisible();
    await expect(forecastPanel).toContainText('Goal Completion Forecast');
    await expect(forecastPanel).toContainText('Remaining Work Ledger');
    await expect(forecastPanel).toContainText('Safe Next Actions Queue');

    // Verify Monetization Readiness panel visibility
    const monetizationPanel = page.locator('#monetization-readiness-panel');
    await expect(monetizationPanel).toBeVisible();
    await expect(monetizationPanel).toContainText('Monetization Readiness Sidecar');
    await expect(monetizationPanel).toContainText('Evidence Gap Matrix');
    await expect(monetizationPanel).toContainText('Compliance & Guardrail Ledger');

    // Verify guardrails values
    await expect(monetizationPanel.locator('#guardrail-export')).toContainText('FUTURE_NOT_NOW');
    await expect(monetizationPanel.locator('#guardrail-paid')).toContainText('FALSE');
    await expect(monetizationPanel.locator('#guardrail-ports')).toContainText('FALSE');

    // Verify remaining work ledger has table elements
    const remainingTable = forecastPanel.locator('#remaining-work-tbody');
    await expect(remainingTable).toBeVisible();

    // Verify evidence gap matrix table
    const matrixTable = monetizationPanel.locator('#evidence-matrix-tbody');
    await expect(matrixTable).toBeVisible();
  });
});
