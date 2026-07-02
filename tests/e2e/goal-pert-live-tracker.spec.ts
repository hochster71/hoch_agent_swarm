import { test, expect } from '@playwright/test';

test.describe('/GOAL Digital PERT Live Tracker E2E Verification', () => {
    
    test('1. Verify /api/v1/goal/pert returns correct data model and formulas', async ({ request }) => {
        const response = await request.get('http://127.0.0.1:8765/api/v1/goal/pert');
        expect(response.ok()).toBeTruthy();
        
        const data = await response.json();
        
        expect(data.goal_id).toBe('HAS-HASF-GOAL');
        expect(data.goal_name).toBe('/GOAL');
        expect(data.status).toBe('NO-GO');
        expect(data.final_verifier).toBe('BLOCKED');
        expect(data.readiness_score).toBe(50);
        expect(data.active_blocker).toBe('NO_ACTIVE_RELEASE_GO');
        
        // Expected completion should sum to 600.0 minutes
        expect(data.expected_completion_minutes).toBe(600.0);
        
        // Critical path
        expect(data.critical_path).toEqual(['A', 'E', 'B', 'D', 'G', 'H']);
        
        // Validate PERT calculations for lane A: optimistic=45, ml=90, pessimistic=180
        // expected = (45 + 4*90 + 180)/6 = 97.5
        const laneA = data.lanes.find(l => l.id === 'A');
        expect(laneA).toBeDefined();
        expect(laneA.expected_minutes).toBe(97.5);
    });

    test('2. Verify Moonshot UI displays DIGITAL PERT /GOAL TRACKER', async ({ page }) => {
        // Go to Moonshot UI
        await page.goto('http://127.0.0.1:8765/ui-moonshot');
        
        // Assert header / section title is visible
        const header = page.locator('h2:has-text("DIGITAL PERT /GOAL TRACKER")');
        await expect(header).toBeVisible();
        
        // Assert North Star Goal container is visible and has correct goal content
        const northStar = page.locator('#pertNorthStar');
        await expect(northStar).toBeVisible();
        await expect(northStar).toContainText('Complete HAS/HASF as an operational, verified, AI-assisted command system');

        // Assert GO/NO-GO status and blocker are visible
        const status = page.locator('#pertStatus');
        await expect(status).toBeVisible();
        await expect(status).toContainText('NO-GO');
        
        const blockerPill = page.locator('#pertBlockerPill');
        await expect(blockerPill).toBeVisible();
        await expect(blockerPill).toContainText('NO_ACTIVE_RELEASE_GO');

        // Assert Expected completion time is visible
        const expectedTime = page.locator('#pertExpectedTime');
        await expect(expectedTime).toBeVisible();
        await expect(expectedTime).toContainText('600 min');

        // Assert HELM is listed as owner and details are shown
        const lanesTable = page.locator('#goalPertRows');
        await expect(lanesTable).toBeVisible();
        await expect(lanesTable).toContainText('Michael AI Model / HELM');
        await expect(lanesTable).toContainText('HELM');
        await expect(lanesTable).toContainText('97.5');
    });
});
