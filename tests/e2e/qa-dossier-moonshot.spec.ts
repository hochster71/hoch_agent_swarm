import { test, expect } from '@playwright/test';

test.describe('Moonshot QA Dossier Command Center E2E Specs', () => {

    test('1. Verify /api/v1/qa/dossiers/summary returns summary stats', async ({ request }) => {
        const response = await request.get('http://127.0.0.1:8765/api/v1/qa/dossiers/summary');
        expect(response.ok()).toBeTruthy();
        
        const summary = await response.json();
        expect(summary.total_teams).toBe(16);
        expect(summary.passing_teams).toBe(16);
        expect(summary.failing_teams).toBe(0);
        expect(summary.partial_teams).toBe(0);
    });

    test('2. Verify Moonshot UI renders QA Command Center', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/ui-moonshot');
        
        // Assert section title exists
        const panel = page.locator('#qa-dossier-command-center');
        await expect(panel).toBeVisible();
        await expect(panel.locator('h2')).toContainText('HAS/HASF QA DOSSIER COMMAND CENTER');
        
        // Assert summary stats
        await expect(page.locator('#qaPassingTeams')).toContainText('16');
        await expect(page.locator('#qaPartialTeams')).toContainText('0');
        await expect(page.locator('#qaFailingTeams')).toContainText('0');
        await expect(page.locator('#qaRevenueReady')).toContainText('READY');
        
        // Assert table rows are populated
        const rows = page.locator('#qaDossierRows tr');
        expect(await rows.count()).toBe(16);
        
        // Assert specific team is listed
        await expect(page.locator('#qaDossierRows')).toContainText('remoteops_qa');
        await expect(page.locator('#qaDossierRows')).toContainText('revenue_qa');
    });
});
