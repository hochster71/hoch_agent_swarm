import { test, expect } from '@playwright/test';

test.describe('RC49 HOCH PODS Compute Scheduler & Node Health E2E Tests', () => {
    
    test('1. Verify /api/pert/data returns correct HOCH PODS compute nodes, health and schedule', async ({ request }) => {
        const response = await request.get('http://127.0.0.1:8765/api/pert/data');
        expect(response.ok()).toBeTruthy();
        
        const data = await response.json();
        
        // Assert compute nodes registry
        expect(data.hoch_compute_nodes).toBeDefined();
        expect(Array.isArray(data.hoch_compute_nodes)).toBeTruthy();
        expect(data.hoch_compute_nodes.length).toBeGreaterThanOrEqual(5);
        
        const mbp = data.hoch_compute_nodes.find(n => n.node_id === 'm5-pro-mbp');
        expect(mbp).toBeDefined();
        expect(mbp.display_name).toBe('M5-Pro-MBP');
        expect(mbp.allowed_workload_classes).toContain('security');
        
        // Assert compute node health authority
        expect(data.hoch_compute_node_health).toBeDefined();
        expect(Array.isArray(data.hoch_compute_node_health)).toBeTruthy();
        expect(data.hoch_compute_node_health.length).toBeGreaterThanOrEqual(5);
        
        const mbpHealth = data.hoch_compute_node_health.find(h => h.node_id === 'm5-pro-mbp');
        expect(mbpHealth).toBeDefined();
        expect(mbpHealth.status).toBe('ONLINE');
        
        // Assert pod schedule
        expect(data.hoch_pod_schedule).toBeDefined();
        expect(Array.isArray(data.hoch_pod_schedule)).toBeTruthy();
        expect(data.hoch_pod_schedule.length).toBe(7);
        
        const cyberSched = data.hoch_pod_schedule.find(s => s.pod_id === 'pod-cyber');
        expect(cyberSched).toBeDefined();
        expect(cyberSched.status).toBe('SCHEDULED');
        expect(cyberSched.assigned_node_id).toBe('m5-pro-mbp');
    });

    test('2. Verify Dashboard UI renders scheduler panel and elements correctly', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');
        
        // Assert scheduler panel exists
        const schedulerPanel = page.locator('#hoch-pod-scheduler-panel');
        await expect(schedulerPanel).toBeVisible();
        
        // Check for node entries
        const nodesTable = page.locator('#hoch-nodes-table-body');
        await expect(nodesTable).toBeVisible();
        
        // Verify we render at least 5 nodes
        const rows = nodesTable.locator('tr');
        const rowCount = await rows.count();
        expect(rowCount).toBeGreaterThanOrEqual(5);
        
        // Verify specific nodes and status are visible
        await expect(nodesTable).toContainText('M5-Pro-MBP');
        await expect(nodesTable).toContainText('M4-MBP');
        await expect(nodesTable).toContainText('iMac-24');
        await expect(nodesTable).toContainText('Dell-Neo');
        await expect(nodesTable).toContainText('ONLINE');
        await expect(nodesTable).toContainText('DEGRADED');
        
        // Verify evidence links are present
        const healthEvidenceLink = page.locator('a[href*="hoch-compute-node-health.md"]');
        const schedEvidenceLink = page.locator('a[href*="hoch-pod-scheduler-evidence.md"]');
        await expect(healthEvidenceLink).toBeVisible();
        await expect(schedEvidenceLink).toBeVisible();
        
        // Verify scheduling rationale container
        const rationaleContainer = page.locator('#hoch-scheduler-rationale-container');
        await expect(rationaleContainer).toBeVisible();
        await expect(rationaleContainer).toContainText('Cyber Pod');
        await expect(rationaleContainer).toContainText('BLOCKED_COMPUTE');
        await expect(rationaleContainer).toContainText('DORMANT');
        
        // Verify no placeholder indicators
        const bodyText = await page.textContent('body');
        expect(bodyText).not.toContain('[PLACEHOLDER]');
        expect(bodyText).not.toContain('%%'); // No duplicate percent signs
        
        // Verify RC48 Theater still renders correctly
        const theaterPanel = page.locator('#hoch-pods-theater-panel');
        await expect(theaterPanel).toBeVisible();
        
        const podsContainer = page.locator('#hoch-pods-container');
        await expect(podsContainer).toBeVisible();
        const podCards = podsContainer.locator('.pod-card');
        expect(await podCards.count()).toBe(7);
    });
});
