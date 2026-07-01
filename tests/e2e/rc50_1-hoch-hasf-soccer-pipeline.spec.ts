import { test, expect } from '@playwright/test';

test.describe('RC50.1 HOCH HASF Soccer Pipeline E2E Tests', () => {

    test('1. Verify HOCH HASF Soccer onboarding pipeline panel renders and contains all required data', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // Verify optional panel exists
        const soccerPanel = page.locator('#hoch-hasf-soccer-pipeline-panel');
        await expect(soccerPanel).toBeVisible();

        // 1. Verify title
        await expect(soccerPanel).toContainText('HOCH HASF Soccer Intelligence Platform Onboarding Pipeline');

        // 2. Verify source path is visible
        await expect(soccerPanel).toContainText('/Users/michaelhoch/Downloads/hoch_hasf_soccer');

        // 3. Verify current stage is intake_audit
        const stageBadge = page.locator('#soccer-stage-badge');
        await expect(stageBadge).toBeVisible();
        await expect(stageBadge).toContainText('intake_audit');

        // 4. Verify readiness score renders (should be less than 100% since auth/stripe are missing, preventing fake green status)
        const readinessVal = page.locator('#soccer-readiness-val');
        await expect(readinessVal).toBeVisible();
        const readinessText = await readinessVal.innerText();
        expect(readinessText).toContain('%');
        expect(readinessText).not.toContain('100%');
        expect(readinessText).not.toContain('%%');

        // 5. Verify audit status renders
        const auditBadge = page.locator('#soccer-audit-status-badge');
        await expect(auditBadge).toBeVisible();
        await expect(auditBadge).not.toContainText('UNKNOWN');

        // 6. Verify blockers list renders blockers
        const blockersList = page.locator('#soccer-blockers-list');
        await expect(blockersList).toBeVisible();
        await expect(blockersList).toContainText('Monetization model not verified');
        await expect(blockersList).toContainText('Security posture not verified');

        // 7. Verify next critical action
        const nextAction = page.locator('#soccer-next-action-val');
        await expect(nextAction).toBeVisible();
        await expect(nextAction).not.toBeEmpty();

        // 8. Verify assigned AI owners are rendered
        const ownersList = page.locator('#soccer-owners-list');
        await expect(ownersList).toBeVisible();
        await expect(ownersList).toContainText('AI Product Officer');
        await expect(ownersList).toContainText('HASF Product Finance Manager');
        await expect(ownersList).toContainText('AI Security & Compliance Officer');

        // 9. Verify evidence and strategic model links exist
        const linksContainer = page.locator('#soccer-links-container');
        await expect(linksContainer).toBeVisible();
        
        const auditLink = page.locator('#soccer-links-container >> text=Onboarding Audit');
        await expect(auditLink).toBeVisible();
        await expect(auditLink).toHaveAttribute('href', '/view-doc?path=docs/evidence/business/hoch-hasf-soccer-onboarding-audit.md');

        const gapLink = page.locator('#soccer-links-container >> text=Gap Analysis');
        await expect(gapLink).toBeVisible();
        await expect(gapLink).toHaveAttribute('href', '/view-doc?path=docs/evidence/business/hoch-hasf-soccer-gap-analysis.md');

        const pertLink = page.locator('#soccer-links-container >> text=PERT Model');
        await expect(pertLink).toBeVisible();
        await expect(pertLink).toHaveAttribute('href', '/view-doc?path=docs/evidence/business/hoch-hasf-soccer-pert-model.md');

        const strategyLink = page.locator('#soccer-links-container >> text=Product Model Strategy');
        await expect(strategyLink).toBeVisible();
        await expect(strategyLink).toHaveAttribute('href', '/view-doc?path=docs/business/hoch-hasf-soccer-product-model.md');

        // 10. Verify regressions
        // Existing RC50 Panels
        await expect(page.locator('#ai-executive-leadership-panel')).toBeVisible();
        await expect(page.locator('#authority-boundaries-panel')).toBeVisible();
        await expect(page.locator('#finance-operations-panel')).toBeVisible();
        await expect(page.locator('#epic-fury-roi-panel')).toBeVisible();

        // Existing RC49 Panels
        await expect(page.locator('#hoch-pod-scheduler-panel')).toBeVisible();

        // Existing RC48 Panels
        await expect(page.locator('#hoch-pods-theater-panel')).toBeVisible();
    });
});
