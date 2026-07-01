import { test, expect } from '@playwright/test';

test.describe('RC49.6 HOCH PODS Visual Fidelity & Cockpit Layout E2E Tests', () => {

    test('1. Verify Command Surface Cockpit zones and elements exist', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // 1. Verify Command Surface container
        const commandSurface = page.locator('#hoch-pods-command-surface');
        await expect(commandSurface).toBeVisible();

        // 2. Verify Header Rail and freshness badges
        const headerRail = page.locator('#hoch-pods-header-rail');
        await expect(headerRail).toBeVisible();
        await expect(headerRail).toContainText('HOCH PODS Command Surface');
        await expect(page.locator('#hoch-pods-freshness-badge')).toBeVisible();
        await expect(page.locator('#hoch-scheduler-freshness-badge')).toBeVisible();

        // 3. Verify Compute Pool Rail
        const computeRail = page.locator('#hoch-pods-compute-rail');
        await expect(computeRail).toBeVisible();

        // 4. Verify Topology Map
        const topologyMap = page.locator('#hoch-pods-topology-panel');
        await expect(topologyMap).toBeVisible();
        await expect(topologyMap).toContainText('Zero Trust Compliant Topology Map');

        // Verify topology cards and trust rails
        const zoneCards = page.locator('.topo-zone-card');
        expect(await zoneCards.count()).toBeGreaterThanOrEqual(7);
        await expect(page.locator('#topo-zone-operator')).toContainText('Operator Zone');
        await expect(page.locator('#topo-zone-management')).toContainText('Management Zone');
        await expect(page.locator('#topo-zone-model')).toContainText('Model Zone');
        await expect(page.locator('#topo-zone-runtime')).toContainText('Pod Runtime Zone');

        const trustRails = page.locator('.topo-trust-rail');
        expect(await trustRails.count()).toBeGreaterThanOrEqual(6);

        // 5. Verify Pod Theater Panel and capsules
        const theaterPanel = page.locator('#hoch-pods-theater-panel');
        await expect(theaterPanel).toBeVisible();

        const podsContainer = page.locator('#hoch-pods-container');
        await expect(podsContainer).toBeVisible();

        // Ensure pod cards are rendered as capsules
        const capsules = podsContainer.locator('.pod-capsule');
        await expect(capsules.first()).toBeVisible();
        expect(await capsules.count()).toBe(7);

        // Check for specific lifecycle classes presence
        const executingCapsules = podsContainer.locator('.pod-capsule.pod-state-executing');
        expect(await executingCapsules.count()).toBeGreaterThanOrEqual(1);

        const failedCapsules = podsContainer.locator('.pod-capsule.pod-state-failed');
        expect(await failedCapsules.count()).toBeGreaterThanOrEqual(1);

        // 6. Verify Hardening Guide Panel and rules
        const hardeningPanel = page.locator('#hoch-pods-hardening-panel');
        await expect(hardeningPanel).toBeVisible();
        await expect(hardeningPanel).toContainText('Zero trust by design');
        await expect(hardeningPanel).toContainText('No shortcuts. No exceptions. No fake green.');

        // 7. Verify Compliance Panel and mapping cards
        const compliancePanel = page.locator('#hoch-pods-compliance-panel');
        await expect(compliancePanel).toBeVisible();
        const complianceCards = compliancePanel.locator('.compliance-card');
        expect(await complianceCards.count()).toBeGreaterThanOrEqual(5);

        // 8. Verify Scheduler Panel and node card matrix
        const schedulerPanel = page.locator('#hoch-pod-scheduler-panel');
        await expect(schedulerPanel).toBeVisible();

        const nodeMatrix = page.locator('#hoch-nodes-card-matrix');
        await expect(nodeMatrix).toBeVisible();
        const nodeCards = nodeMatrix.locator('.compute-node-card');
        expect(await nodeCards.count()).toBeGreaterThanOrEqual(5);

        // Check that table rows exist
        const tableBody = page.locator('#hoch-nodes-table-body');
        await expect(tableBody).toBeVisible();
        const rows = tableBody.locator('tr');
        expect(await rows.count()).toBeGreaterThanOrEqual(5);

        // Verify evidence links
        const healthEvidenceLink = page.locator('a[href*="hoch-compute-node-health.md"]');
        const schedEvidenceLink = page.locator('a[href*="hoch-pod-scheduler-evidence.md"]');
        await expect(healthEvidenceLink).toBeVisible();
        await expect(schedEvidenceLink).toBeVisible();

        // 9. Verify no placeholder indicators are present
        const pageBody = await page.textContent('body');
        expect(pageBody).not.toContain('[PLACEHOLDER]');
        expect(pageBody).not.toContain('%%');
    });
});
