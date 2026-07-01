import { test, expect } from '@playwright/test';

test.describe('RC52 Governed Swarm Execution Runner Cockpit E2E Tests', () => {

    test('1. Verify governed execution runner panel, status, allowed safe and hard-blocked unsafe classes render', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // 1. Verify Swarm Governed Execution Runner Panel exists
        const panel = page.locator('#governed-execution-runner-panel');
        await expect(panel).toBeVisible();

        // 2. Verify Freshness Badge and Safety State Badge
        const freshnessBadge = page.locator('#governed-execution-freshness-badge');
        await expect(freshnessBadge).toBeVisible();
        const freshnessText = await freshnessBadge.innerText();
        expect(['FRESH', 'STALE', 'DEGRADED', 'UNKNOWN']).toContain(freshnessText.trim());

        const safetyStateBadge = page.locator('#governed-execution-status-badge');
        await expect(safetyStateBadge).toBeVisible();
        const safetyText = await safetyStateBadge.innerText();
        expect(['HEALTHY', 'STALE', 'DEGRADED', 'UNKNOWN']).toContain(safetyText.trim());

        // 3. Verify Permitted Safe Classes list
        await expect(panel).toContainText('Permitted Safe Classes');
        await expect(panel).toContainText('READ_ONLY');
        await expect(panel).toContainText('LOCAL_SAFE_WRITE');

        // 4. Verify Hard-Blocked Unsafe Classes rendering
        await expect(panel).toContainText('Hard-Blocked Unsafe Classes');
        await expect(panel).toContainText('❌ REPO_WRITE');
        await expect(panel).toContainText('❌ NETWORK_WRITE');
        await expect(panel).toContainText('❌ SECRET_ACCESS');
        await expect(panel).toContainText('❌ STRIPE_LIVE_CONFIG');
        await expect(panel).toContainText('❌ DEPLOYMENT');
        await expect(panel).toContainText('❌ DESTRUCTIVE');

        // 5. Verify Rollback plan links, safety model, and logs are visible
        const safetyModelLink = panel.locator('a[href*="governed-execution-safety-model.md"]');
        await expect(safetyModelLink).toBeVisible();

        const rollbackLink = panel.locator('a[href*="governed-execution-rollback-plan.md"]');
        await expect(rollbackLink).toBeVisible();

        const logLink = panel.locator('a[href*="governed-execution-log.md"]');
        await expect(logLink).toBeVisible();

        // 6. Verify regression enclaves still render
        // RC51 execution approval panel
        await expect(page.locator('#hoch-execution-approval-panel')).toBeVisible();
        await expect(page.locator('#hoch-execution-approval-panel')).toContainText('Michael Hoch Sign-off REQUIRED');

        // 7. Verify no duplicate percent signs
        const pageText = await page.innerText('body');
        expect(pageText).not.toContain('%%');
    });
});
