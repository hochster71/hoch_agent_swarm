import { test, expect } from '@playwright/test';

const BASE = process.env.PERT_BASE_URL || 'http://127.0.0.1:8765';

test.describe('UI V2.1 Operator Console', () => {
  test('loads tabbed truth-first command center', async ({ page }) => {
    await page.goto(`${BASE}/ui-v2`, { waitUntil: 'networkidle' });

    await expect(page.getByRole('heading', { name: /HOCH HAS \/ HASF Operator Console V2\.1/i })).toBeVisible();

    for (const tab of ['Command', 'Pods', 'Revenue', 'Evidence', 'PERT', 'Watchdog']) {
      await expect(page.getByRole('button', { name: tab })).toBeVisible();
    }

    await expect(page.locator('text=Critical Telemetry Authority')).toBeVisible();
    await expect(page.locator('body')).not.toContainText('undefined');
  });

  test('all tabs switch without blank page or undefined fields', async ({ page }) => {
    await page.goto(`${BASE}/ui-v2`, { waitUntil: 'networkidle' });

    const tabs = ['Command', 'Pods', 'Revenue', 'Evidence', 'PERT', 'Watchdog'];

    for (const tab of tabs) {
      await page.getByRole('button', { name: tab }).click();
      await expect(page.locator('#app')).toBeVisible();
      await expect(page.locator('#app')).not.toContainText('undefined');
      await expect(page.locator('#app')).not.toContainText('API Error');
    }

    await expect(page.locator('text=Source Freshness Detail')).toBeVisible();
  });
});
