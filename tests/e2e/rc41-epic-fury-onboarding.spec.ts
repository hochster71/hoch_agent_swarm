import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('RC41 Epic Fury Onboarding E2E tests', () => {
  test('navigates to PERT cockpit and validates Epic Fury pipeline flowchart', async ({ page }) => {
    // 1. Verify LOCAL-003 exists in local project inventory
    const inventoryPath = path.join(__dirname, '../../has_live_project_tracker/data/local_project_inventory.json');
    expect(fs.existsSync(inventoryPath)).toBe(true);
    
    const inventory = JSON.parse(fs.readFileSync(inventoryPath, 'utf8'));
    const epicFuryItem = inventory.find(item => item.id === 'LOCAL-003');
    expect(epicFuryItem).toBeDefined();
    expect(epicFuryItem.name).toBe('Epic-fury-2026-main');

    // 2. Load the PERT cockpit
    await page.goto('http://127.0.0.1:8765/');

    // 3. Verify pipeline card is visible
    const pipelinePanel = page.locator('#epic-fury-pipeline-panel');
    await expect(pipelinePanel).toBeVisible();

    // 4. Verify all 6 pipeline stages are present
    const stages = pipelinePanel.locator('.pipeline-stage');
    await expect(stages).toHaveCount(6);

    // 5. Verify names of stages
    await expect(stages.nth(0)).toContainText('Source Discovery');
    await expect(stages.nth(1)).toContainText('Audit & Analysis');
    await expect(stages.nth(2)).toContainText('Environment Setup');
    await expect(stages.nth(3)).toContainText('CI Verification');
    await expect(stages.nth(4)).toContainText('PERT Integration');
    await expect(stages.nth(5)).toContainText('Pipeline Visuals');

    // 6. Verify tooltips exist
    const tooltips = pipelinePanel.locator('.tooltip');
    await expect(tooltips).toHaveCount(6);
  });
});
