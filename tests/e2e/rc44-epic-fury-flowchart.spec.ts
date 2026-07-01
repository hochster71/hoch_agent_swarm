import { test, expect } from '@playwright/test';

test.describe('RC44 Epic Fury dynamic flowchart E2E tests', () => {
  test('navigates to PERT Command Center and validates dynamic flowchart rendering', async ({ page }) => {
    // Navigate to local dashboard on port 8765
    await page.goto('http://127.0.0.1:8765/');

    // Locate the pipeline panel
    const pipelinePanel = page.locator('#epic-fury-pipeline-panel');
    await expect(pipelinePanel).toBeVisible();

    const flowContainer = page.locator('#epic-fury-flow-container');
    await expect(flowContainer).toBeVisible();

    // Verify exactly 6 stages are rendered dynamically
    const stages = flowContainer.locator('.pipeline-stage');
    await expect(stages).toHaveCount(6);

    // Verify first 5 stages are completed
    for (let i = 0; i < 5; i++) {
      const stage = stages.nth(i);
      await expect(stage).toHaveClass(/completed/);
      const dot = stage.locator('.stage-dot');
      await expect(dot).toContainText((i + 1).toString());
    }

    // Verify the 6th stage is active
    const activeStage = stages.nth(5);
    await expect(activeStage).toHaveClass(/active/);
    const activeDot = activeStage.locator('.stage-dot');
    await expect(activeDot).toContainText('6');

    // Verify active connectors (between completed stages)
    const connectors = flowContainer.locator('.pipeline-connector');
    await expect(connectors).toHaveCount(5);
    for (let i = 0; i < 5; i++) {
      const conn = connectors.nth(i);
      await expect(conn).toHaveClass(/active/);
    }

    // Verify tooltip on active stage
    const activeTooltip = activeStage.locator('.tooltip');
    await expect(activeTooltip).toContainText('Status: ACTIVE');
    await expect(activeTooltip).toContainText('Source: cockpit_ui');
  });
});
