import { test, expect } from '@playwright/test';

test.describe('RC51 Swarm Execution Approval Queue and Safe Write Gates E2E Tests', () => {

    test('1. Verify Execution Approval Queue panel, proposals and zero-trust policies render', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // 1. Verify Swarm Execution Approval Queue panel exists
        const panel = page.locator('#hoch-execution-approval-panel');
        await expect(panel).toBeVisible();

        // 2. Verify Freshness Badge and Authority Badge
        const freshnessBadge = page.locator('#approval-queue-freshness-badge');
        await expect(freshnessBadge).toBeVisible();
        const freshnessText = await freshnessBadge.innerText();
        expect(['FRESH', 'STALE', 'DEGRADED', 'UNKNOWN']).toContain(freshnessText.trim());

        const authorityBadge = page.locator('#execution-authority-badge');
        await expect(authorityBadge).toBeVisible();
        const authorityText = await authorityBadge.innerText();
        expect(['HEALTHY', 'STALE', 'DEGRADED', 'UNKNOWN']).toContain(authorityText.trim());

        // 3. Verify proposals rendering (Active & Quarantined)
        const activeProposals = page.locator('#execution-proposals-container > .proposal-card');
        await expect(activeProposals.first()).toBeVisible();

        const quarantinedProposals = page.locator('#quarantined-actions-container > .proposal-card');
        await expect(quarantinedProposals.first()).toBeVisible();

        // 4. Verify specific content in proposals
        // Check for "Scan Codebase for Secrets Exposure" (Low Risk, READ_ONLY)
        const cyberProposal = page.locator('#execution-proposals-container').filter({ hasText: 'Scan Codebase for Secrets Exposure' });
        await expect(cyberProposal).toBeVisible();
        await expect(cyberProposal).toContainText('LOW RISK');
        await expect(cyberProposal).toContainText('READ_ONLY');

        // Check for "Deploy Production Image to Cloud Run" (Critical Risk, DEPLOYMENT)
        const deployProposal = page.locator('#execution-proposals-container').filter({ hasText: 'Deploy Production Image to Cloud Run' });
        await expect(deployProposal).toBeVisible();
        await expect(deployProposal).toContainText('CRITICAL RISK');
        await expect(deployProposal).toContainText('DEPLOYMENT');
        await expect(deployProposal).toContainText('Michael Hoch Sign-off REQUIRED');

        // Check for "Purge Historical Database Log Archives" (Destructive Action - Quarantined/Rejected)
        const destructiveProposal = page.locator('#quarantined-actions-container').filter({ hasText: 'Purge Historical Database Log Archives' });
        await expect(destructiveProposal).toBeVisible();
        await expect(destructiveProposal).toContainText('CRITICAL RISK');
        await expect(destructiveProposal).toContainText('DESTRUCTIVE');
        await expect(destructiveProposal).toContainText('REJECTED');
        await expect(destructiveProposal).toContainText('Blocked: Destructive database purge actions are denied by default under safe-write policy');

        // 5. Verify rollback and verification plans
        await expect(panel).toContainText('Rollback Plan:');
        await expect(panel).toContainText('Verification:');

        // 6. Verify policy link exists
        const policyLink = panel.locator('a[href*="safe-write-policy.md"]');
        await expect(policyLink).toBeVisible();

        // 7. Verify regressions of earlier enclaves
        // RC50 AI Executive Leadership & Finance Cards
        await expect(page.locator('#ai-executive-leadership-panel')).toBeVisible();
        await expect(page.locator('#finance-operations-panel')).toBeVisible();
        // RC50.1 Soccer Panel
        await expect(page.locator('#hoch-hasf-soccer-pipeline-panel')).toBeVisible();
        // RC49 Pod Scheduler
        await expect(page.locator('#hoch-pod-scheduler-panel')).toBeVisible();
        // RC48 HOCH PODS Theater
        await expect(page.locator('#hoch-pods-theater-panel')).toBeVisible();

        // 8. Verify no duplicate percent signs (%%)
        const pageText = await page.innerText('body');
        expect(pageText).not.toContain('%%');
    });
});
