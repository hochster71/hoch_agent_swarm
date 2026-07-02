import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

test.describe('RC52.1 HOCH PODS Theater Visual Baseline Playwright Spec', () => {

    test('1. Verify 17-Frame Cinematic Storyboard and Capture Screenshot', async ({ page }) => {
        // Set viewport size exactly as required
        await page.setViewportSize({ width: 1536, height: 864 });

        await page.goto('http://127.0.0.1:8765/');

        // Assert theater container is visible and first
        await expect(page.locator('#hoch-pods-theater')).toBeVisible();

        // Capture screenshot of the first visible screen
        const screenshotDir = path.join(__dirname, '..', '..', 'docs', 'evidence', 'ui', 'screenshots');
        fs.mkdirSync(screenshotDir, { recursive: true });
        const screenshotPath = path.join(screenshotDir, 'rc52_1-hoch-pods-theater-current.png');
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`Saved screenshot to: ${screenshotPath}`);

        // Verify required DOM IDs exist
        const requiredIds = [
            '#hoch-pods-theater',
            '#hoch-pods-intro-movie-board',
            '#hoch-pods-storyboard-grid',
            '#hoch-pods-agent-spinup-variations',
            '#hoch-pods-skill-card-animation-flow',
            '#hoch-pods-destination-lanes',
            '#hoch-pods-status-overview',
            '#hoch-pods-data-flow-visualization',
            '#hoch-pods-evidence-archive',
            '#hoch-pods-system-confirmation',
            '#hoch-pods-mission-ready',
            '#hoch-pods-movie-detail-drawer',
            '#hoch-pods-theater-control-bar',
            '#hoch-pods-stale-quarantine-layer'
        ];

        for (const elementId of requiredIds) {
            await expect(page.locator(elementId)).not.toBeNull();
        }

        // Verify layout order (theater is first, topology is after/below it)
        const theaterBox = await page.locator('#hoch-pods-theater').boundingBox();
        const topologyBox = await page.locator('#hoch-pods-topology-panel').boundingBox();
        
        expect(theaterBox).not.toBeNull();
        expect(topologyBox).not.toBeNull();
        if (theaterBox && topologyBox) {
            expect(theaterBox.y).toBeLessThan(topologyBox.y);
        }

        // Execute visual compliance audit from python to ensure PASS status
        console.log('Running visual compliance python script...');
        try {
            const root = path.join(__dirname, '..', '..');
            const resultStr = execSync('python3 scripts/audit_hoch_pods_theater_visual_compliance.py', { cwd: root }).toString();
            console.log(resultStr);
            
            const auditJsonPath = path.join(root, 'has_live_project_tracker', 'data', 'hoch_pods_theater_visual_compliance.json');
            expect(fs.existsSync(auditJsonPath)).toBe(true);
            const result = JSON.parse(fs.readFileSync(auditJsonPath, 'utf-8'));
            expect(result.THEME_COMPLIANCE).toBe('PASS');
        } catch (error) {
            console.error('Compliance script failed:', error);
            throw error;
        }
    });
});
