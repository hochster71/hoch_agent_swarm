import { test, expect } from '@playwright/test';

test.describe('RC50 HOCH HAS/HASF AI Executive Leadership & Finance Operations E2E Tests', () => {

    test('1. Verify AI Leadership, Finance, ROI, and Authority Boundaries panels exist and render data', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // 1. Verify AI Executive Leadership Panel
        const leadershipPanel = page.locator('#ai-executive-leadership-panel');
        await expect(leadershipPanel).toBeVisible();
        await expect(leadershipPanel).toContainText('Michael Hoch');
        await expect(leadershipPanel).toContainText('Founder / Owner / Final Approval Authority');
        
        // Check organization hierarchy details
        await expect(leadershipPanel).toContainText('AI Chief Operating Officer');
        await expect(leadershipPanel).toContainText('AI Chief Financial Officer');

        // Check dynamic executives rendering
        const execCards = leadershipPanel.locator('#ai-executives-container > div');
        expect(await execCards.count()).toBeGreaterThanOrEqual(10); // 10 roles

        // 2. Verify Authority Boundaries Panel
        const boundariesPanel = page.locator('#authority-boundaries-panel');
        await expect(boundariesPanel).toBeVisible();
        await expect(boundariesPanel).toContainText('Authority & Governance Boundaries');
        await expect(boundariesPanel).toContainText('Autonomous Execution Allowed');
        await expect(boundariesPanel).toContainText('Human Approval REQUIRED');

        // 3. Verify Finance Operations Panel
        const financePanel = page.locator('#finance-operations-panel');
        await expect(financePanel).toBeVisible();
        await expect(financePanel).toContainText('Finance Manager & Analyst Assignments');
        await expect(financePanel).toContainText('Stripe / W12 Monetization Dependency');
        
        // Verify Stripe status pill exists
        const stripePill = page.locator('#fin-stripe-status-pill');
        await expect(stripePill).toBeVisible();
        
        // Verify assignments render
        const assignmentCards = financePanel.locator('#finance-agents-container > div');
        expect(await assignmentCards.count()).toBeGreaterThanOrEqual(8);

        // 4. Verify Epic Fury ROI Projections Panel
        const roiPanel = page.locator('#epic-fury-roi-panel');
        await expect(roiPanel).toBeVisible();
        await expect(roiPanel).toContainText('Epic Fury ROI Model Scenarios');

        // Verify scenarios rendering (at least 4 scenarios: Conservative, Realistic, Strong, Breakout)
        const scenarioRows = page.locator('#roi-scenarios-table-body > tr');
        expect(await scenarioRows.count()).toBe(4);
        await expect(page.locator('#roi-scenarios-table-body')).toContainText('Conservative');
        await expect(page.locator('#roi-scenarios-table-body')).toContainText('Realistic');
        await expect(page.locator('#roi-scenarios-table-body')).toContainText('Strong');
        await expect(page.locator('#roi-scenarios-table-body')).toContainText('Breakout');

        // 5. Verify no duplicate percent signs on conversion rate and ROI
        const textContent = await page.locator('#roi-scenarios-table-body').innerText();
        // Check for double percent signs like '%%'
        expect(textContent).not.toContain('%%');

        // 6. Verify regressions for RC48 and RC49
        // RC48 HOCH PODS Theater
        await expect(page.locator('#hoch-pods-theater-panel')).toBeVisible();
        // RC49 Scheduler Panel
        await expect(page.locator('#hoch-pod-scheduler-panel')).toBeVisible();
    });
});
