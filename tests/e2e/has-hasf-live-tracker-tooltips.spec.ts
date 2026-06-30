import { test, expect } from '@playwright/test';

test.use({
  httpCredentials: {
    username: 'admin',
    password: 'change-this-password',
  },
});

test.describe('HAS/HASF Live Project Tracker Tooltips & Drawer E2E', () => {
  test('verifies tooltips and detail drawer interactions', async ({ page }) => {
    // Navigate directly to local tracker
    const url = 'http://localhost:3001/';
    await page.goto(url);

    // Verify page loads and title is correct
    await expect(page).toHaveTitle('HAS/HASF Live Project Tracker');

    // Wait for the api/truth request to finish and DOM to render rows
    await page.waitForSelector('.agent-name-cell');

    // 1. API endpoint verification using page.request
    const healthRes = await page.request.get('http://localhost:3001/api/health');
    expect(healthRes.status()).toBe(200);
    const healthJson = await healthRes.json();
    expect(healthJson.ok).toBe(true);

    const truthRes = await page.request.get('http://localhost:3001/api/truth');
    expect(truthRes.status()).toBe(200);
    const truthJson = await truthRes.json();
    expect(truthJson.projection).toBeDefined();
    expect(truthJson.tasks).toBeDefined();

    // 2. Agent hover shows tooltip
    const agentNameCell = page.locator('.agent-name-cell').first();
    await expect(agentNameCell).toBeVisible();
    await agentNameCell.hover();
    
    // Check tooltip is visible and has role="tooltip"
    const tooltip = page.locator('#tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toHaveAttribute('role', 'tooltip');
    await expect(agentNameCell).toHaveAttribute('aria-describedby', 'tooltip');

    // Escape key closes tooltip
    await page.keyboard.press('Escape');
    await expect(tooltip).not.toBeVisible();

    // 3. Task hover shows tooltip
    const taskNameCell = page.locator('.task-name-cell').first();
    await expect(taskNameCell).toBeVisible();
    await taskNameCell.hover();
    await expect(tooltip).toBeVisible();
    await expect(taskNameCell).toHaveAttribute('aria-describedby', 'tooltip');
    
    // Move mouse away to prevent hover interference on subsequent keyboard test
    await page.keyboard.press('Escape');
    await expect(tooltip).not.toBeVisible();
    await page.mouse.move(0, 0);

    // Focus trigger shows tooltip
    await taskNameCell.focus();
    await expect(tooltip).toBeVisible();
    
    // Blur hides tooltip
    await taskNameCell.blur();
    await expect(tooltip).not.toBeVisible();

    // 4. Build hover shows tooltip
    const buildNameCell = page.locator('.build-name-cell').first();
    await expect(buildNameCell).toBeVisible();
    await buildNameCell.hover();
    await expect(tooltip).toBeVisible();
    
    // Move mouse away again
    await page.keyboard.press('Escape');
    await page.mouse.move(0, 0);

    // 5. Row click opens detail drawer
    const taskRow = page.locator('#taskRows tr').first();
    await taskRow.click();

    const drawer = page.locator('#drawer');
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText('Task ID:');

    // Close button works (click top-right 'x' button)
    const closeBtn = drawer.locator('button').first();
    await closeBtn.click();
    await expect(drawer).not.toBeVisible();

    // Reopen and check Escape closes drawer
    await taskRow.click();
    await expect(drawer).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(drawer).not.toBeVisible();
  });
});
