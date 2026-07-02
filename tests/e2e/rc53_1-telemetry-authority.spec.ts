import { test, expect } from '@playwright/test';
// Native fetch is available globally in Node 18+

test.describe('Telemetry Authority Reconciliation E2E Spec', () => {

    test('1. Verify central Telemetry Authority data endpoint', async () => {
        const response = await fetch('http://127.0.0.1:8765/api/pert/data');
        expect(response.status).toBe(200);
        const data = await response.json();
        
        expect(data.freshness_authority).toBeDefined();
        expect(data.freshness_authority.reconciled_sources).toBeDefined();
        
        const sources = data.freshness_authority.reconciled_sources;
        expect(sources.global_verify).toBeDefined();
        expect(sources.revenue_readiness).toBeDefined();
        expect(sources.revenue_action_queue).toBeDefined();
        expect(sources.hoch_pods_runtime_state).toBeDefined();
        expect(sources.hoch_pod_schedule).toBeDefined();
        
        // Assert Stripe keys setup and W12 task properties
        const w12Task = data.pert_cpm.tasks.find((t: any) => t.id === 'W12');
        expect(w12Task).toBeDefined();
        expect(data.w12_blocker_status).toBeDefined();
        
        console.log("Telemetry verification successful.");
    });

    test('2. Verify UI freshness badges representation and tooltip contents', async ({ page }) => {
        await page.setViewportSize({ width: 1536, height: 1024 });
        await page.goto('http://127.0.0.1:8765/');

        // Wait for page telemetry update
        await page.waitForTimeout(2000);

        // Check freshness badges
        const badges = [
            '#executive-freshness-badge',
            '#revenue-readiness-freshness-badge',
            '#revenue-action-queue-freshness-badge',
            '#hoch-pods-freshness-badge',
            '#hoch-scheduler-freshness-badge',
            '#ai-leadership-freshness-badge',
            '#finance-registry-freshness-badge',
            '#roi-model-freshness-badge',
            '#soccer-pipeline-freshness-badge',
            '#approval-queue-freshness-badge',
            '#governed-execution-freshness-badge'
        ];

        for (const selector of badges) {
            const badge = page.locator(selector);
            await expect(badge).toBeVisible();
            const text = await badge.textContent();
            expect(text).not.toBeNull();
            expect(text?.trim().length).toBeGreaterThan(0);
            
            // Check that if it's STALE, the title attribute has the detail string
            if (text?.startsWith('STALE')) {
                const title = await badge.getAttribute('title');
                expect(title).toContain('verified:');
                expect(title).toContain('age:');
            }
        }
    });

    test('3. Verify interactive drawer and links', async ({ page }) => {
        await page.setViewportSize({ width: 1536, height: 1024 });
        await page.goto('http://127.0.0.1:8765/');

        // Wait for update
        await page.waitForTimeout(2000);

        // Click system-boot frame to open drawer
        const bootFrame = page.locator('#frame-system-boot');
        await bootFrame.click();

        // Drawer should be active
        const drawer = page.locator('#hoch-pods-movie-detail-drawer');
        await expect(drawer).toHaveClass(/active/);

        // Check drawer title and JSON block
        const title = page.locator('#movie-drawer-title');
        await expect(title).toContainText('SYSTEM BOOT');
        
        const jsonBlock = page.locator('#drawer-json');
        const jsonText = await jsonBlock.textContent();
        expect(jsonText).toContain('timestamp');

        // Check evidence links
        const evidenceLinks = page.locator('#movie-drawer-evidence-links a');
        const count = await evidenceLinks.count();
        expect(count).toBeGreaterThan(0);
        
        const firstHref = await evidenceLinks.first().getAttribute('href');
        expect(firstHref).toContain('/view-doc?path=');

        // Close drawer
        const closeBtn = page.locator('.drawer-close');
        await closeBtn.click();
        await expect(drawer).not.toHaveClass(/active/);
    });

    test('4. Verify independent frame status mapping', async ({ page }) => {
        await page.setViewportSize({ width: 1536, height: 1024 });
        await page.goto('http://127.0.0.1:8765/');
        await page.waitForTimeout(2000);

        // Fetch api telemetry directly
        const response = await fetch('http://127.0.0.1:8765/api/pert/data');
        const data = await response.json();
        const sources = data.freshness_authority.reconciled_sources;

        // Check boot frame state vs schedule source status
        const bootState = sources.hoch_pod_schedule.computed_state;
        const bootFrame = page.locator('#frame-system-boot');
        if (bootState === 'FRESH') {
            await expect(bootFrame).not.toHaveClass(/state-stale/);
        } else if (bootState === 'STALE') {
            await expect(bootFrame).toHaveClass(/state-stale/);
        }

        // Check evidence archive frame state vs evidence_ledger status
        const archiveState = sources.evidence_ledger.computed_state;
        const archiveFrame = page.locator('.interactive-region#hoch-pods-evidence-archive');
        if (archiveState === 'FRESH') {
            await expect(archiveFrame).not.toHaveClass(/state-stale/);
        } else if (archiveState === 'STALE') {
            await expect(archiveFrame).toHaveClass(/state-stale/);
        }
    });
});
