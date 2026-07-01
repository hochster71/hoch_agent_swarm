import { test, expect } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';

test.describe('RC40 Compute Utilization Gap & PERT Recalibration E2E Tests', () => {
    
    test('1. Verify /api/pert/data returns correct telemetry-wrapped metrics', async ({ request }) => {
        const resp = await request.get(`${BASE_URL}/api/pert/data`);
        expect(resp.status()).toBe(200);
        
        const data = await resp.json();
        
        // Assert top-level telemetry-wrapped metrics
        const requiredMetrics = [
            'compute_utilization_percent',
            'idle_compute_percent',
            'safe_jobs_available',
            'safe_jobs_completed',
            'safe_jobs_failed',
            'relay_compute_utilization_percent',
            'macbook_compute_utilization_percent',
            'monitor_only_clients',
            'approval_required_jobs',
            'public_exposure_violations',
            'quota_saved_minutes',
            'pert_remaining_minutes',
            'goal_completion_percent',
            'w12_blocker_status',
            'minutes_saved',
            'evidence_generated'
        ];
        
        for (const metric of requiredMetrics) {
            expect(data).toHaveProperty(metric);
            const wrapped = data[metric];
            expect(typeof wrapped).toBe('object');
            expect(wrapped).toHaveProperty('value');
            expect(wrapped).toHaveProperty('source');
            expect(wrapped).toHaveProperty('last_updated');
            expect(wrapped).toHaveProperty('freshness');
            expect(wrapped).toHaveProperty('confidence');
            expect(wrapped).toHaveProperty('fallback_state');
        }
    });

    test('2. Verify dashboard UI renders the 5 new panels', async ({ page }) => {
        await page.goto(BASE_URL);
        
        // Assert panel elements exist
        await expect(page.locator('#compute-gap-analysis-panel')).toBeVisible();
        await expect(page.locator('#safe-job-backlog-panel')).toBeVisible();
        await expect(page.locator('#worker-utilization-ledger-panel')).toBeVisible();
        await expect(page.locator('#pert-recalibration-panel')).toBeVisible();
        await expect(page.locator('#compute-goal-acceleration-panel')).toBeVisible();
    });

    test('3. Verify iPhone remains monitor-only and does not run compute', async ({ page, request }) => {
        // Check API
        const resp = await request.get(`${BASE_URL}/api/pert/data`);
        const data = await resp.json();
        
        const workers = data.tailnet_workers || [];
        const iphone = workers.find((w: any) => w.machine === 'iphone-15-pro-max');
        
        expect(iphone).toBeDefined();
        expect(iphone.role).toBe('operator_mobile_monitor');
        expect(iphone.cores).toBe(2); // physical hardware cores are fine, but allowed jobs must be limited
        expect(iphone.allowed_jobs).not.toContain('build_execution');
        expect(iphone.allowed_jobs).not.toContain('destructive_commands');
        expect(iphone.blocked_jobs).toContain('build_execution');
        expect(iphone.blocked_jobs).toContain('destructive_commands');
        
        // Check UI Table
        await page.goto(BASE_URL);
        const iphoneRow = page.locator('#worker-utilization-ledger-panel tbody tr', { hasText: 'iphone-15-pro-max' });
        await expect(iphoneRow).toBeVisible();
        
        // Allowed jobs cell should show dashboard_view, approval_review
        await expect(iphoneRow).toContainText('dashboard_view, approval_review');
        // Est. utilization should be 0.0%
        await expect(iphoneRow).toContainText('0.0%');
        // Goal contribution should be Low
        await expect(iphoneRow).toContainText('10% (Low)');
    });
});
