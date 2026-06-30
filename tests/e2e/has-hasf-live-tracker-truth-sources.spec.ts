import { test, expect } from '@playwright/test';

test.use({
  httpCredentials: {
    username: 'admin',
    password: 'change-this-password',
  },
});

test.describe('HAS/HASF Live Project Tracker Truth Sources E2E', () => {
  test('verifies truth source badges, tooltips, and drawer cockpit integration', async ({ page }) => {
    // Navigate directly to local tracker
    const url = 'http://localhost:3001/';
    await page.goto(url);

    // Verify page loads and title is correct
    await expect(page).toHaveTitle('HAS/HASF Live Project Tracker');

    // Wait for the api/truth request to finish and DOM to render badge
    await page.waitForSelector('#truthSourceBadge');

    // 1. API endpoint verification
    const healthRes = await page.request.get('http://localhost:3001/api/health');
    expect(healthRes.status()).toBe(200);
    const healthJson = await healthRes.json();
    expect(healthJson.ok).toBe(true);

    const sourcesRes = await page.request.get('http://localhost:3001/api/truth-sources');
    expect(sourcesRes.status()).toBe(200);
    const sourcesJson = await sourcesRes.json();
    expect(sourcesJson.chosen_source).toBeDefined();
    expect(sourcesJson.fallback_chain).toBeDefined();

    // 2. Verify Badge Visibility and Text
    const badge = page.locator('#truthSourceBadge');
    await expect(badge).toBeVisible();
    
    const chosenSource = sourcesJson.chosen_source;
    await expect(badge).toHaveText(chosenSource);

    // 3. Hovering badge shows truth source tooltip
    const badgeContainer = page.locator('#truthSourceBadgeContainer');
    await badgeContainer.hover();
    
    const tooltip = page.locator('#tooltip');
    await expect(tooltip).toBeVisible();
    await expect(tooltip).toContainText('Active Truth Source:');

    // Escape closes tooltip
    await page.keyboard.press('Escape');
    await expect(tooltip).not.toBeVisible();

    // 4. Clicking badge opens drawer details
    await badgeContainer.click();
    
    const drawer = page.locator('#drawer');
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText('Active Truth Source Details');
    await expect(drawer).toContainText(chosenSource);

    // Close button works (click top-right 'x' button)
    const closeBtn = drawer.locator('button').first();
    await closeBtn.click();
    await expect(drawer).not.toBeVisible();
  });
});
