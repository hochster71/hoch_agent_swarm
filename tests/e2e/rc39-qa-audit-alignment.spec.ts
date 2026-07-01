import { test, expect } from '@playwright/test';

test.describe('RC39 QA/Audit Remediation E2E tests', () => {
  test('navigates to PERT Command Center and validates QA/Audit alignment details', async ({ page }) => {
    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // 1. Verify Goal Completion Score is dynamic and lists 90% (since W12 is pending)
    const readinessScoreEl = page.locator('#readiness-score');
    await expect(readinessScoreEl).toBeVisible();
    await expect(readinessScoreEl).toContainText('Goal Completion: 90%');

    // 2. Verify Goal Completion Formula card/container
    const formulaContainer = page.locator('#goal-formula-container');
    await expect(formulaContainer).toBeVisible();
    await expect(formulaContainer).toContainText('Goal Progress = Sum(Weights of Completed Tasks)');
    await expect(formulaContainer).toContainText('W12 (Monetization): 10.0% (PENDING)');

    // 3. Verify Worker Metrics Breakdown categories
    const workerMetricsEl = page.locator('#swarm-active-workers');
    await expect(workerMetricsEl).toBeVisible();
    await expect(workerMetricsEl.locator('#worker-visible')).toBeVisible();
    await expect(workerMetricsEl.locator('#worker-build')).toBeVisible();
    await expect(workerMetricsEl.locator('#worker-relay')).toBeVisible();
    await expect(workerMetricsEl.locator('#worker-monitor')).toBeVisible();
    await expect(workerMetricsEl.locator('#worker-offline')).toBeVisible();

    // 4. Verify separate Evidence Coverage and Stripe Sandbox state in Monetization panel
    const monetizationPanel = page.locator('#monetization-readiness-panel');
    await expect(monetizationPanel).toBeVisible();
    
    const evidenceCoverageEl = monetizationPanel.locator('#evidence-coverage');
    await expect(evidenceCoverageEl).toBeVisible();
    // Gaps: 0 files now because RC30 and RC32 were added, so coverage is 100%
    await expect(evidenceCoverageEl).toContainText('100%');
    
    const stripeStateEl = monetizationPanel.locator('#stripe-sandbox-state');
    await expect(stripeStateEl).toBeVisible();
    const stripeText = await stripeStateEl.innerText();
    expect(['NOT_CONFIGURED / APPROVAL_REQUIRED', 'TEST_CONFIGURED']).toContain(stripeText);
    
    // Monetization Readiness score should be capped at 50% since Stripe sandbox is NOT_CONFIGURED, or 100% if configured
    const monetizationScoreEl = monetizationPanel.locator('#monetization-score');
    const scoreText = await monetizationScoreEl.innerText();
    expect(['50%', '100%']).toContain(scoreText);

    // 5. Verify parsed Test Telemetry (should display Playwright test summary instead of global 1/0)
    const testsEl = page.locator('#metric-tests');
    await expect(testsEl).toBeVisible();
    // It should contain "Playwright E2E" or "passing" or "skipped" or "failing"
    await expect(testsEl).toContainText('Playwright E2E');
  });
});
