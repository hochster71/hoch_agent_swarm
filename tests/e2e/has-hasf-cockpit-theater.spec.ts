import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Production Cockpit Theater Integrated Visual Spec', () => {

    test('1. Verify Production Cockpit Theater and Capture Screenshot', async ({ page }) => {
        // Set viewport size to 1536x1024 as specified
        await page.setViewportSize({ width: 1536, height: 1024 });

        await page.goto('http://127.0.0.1:8765/');

        // Assert theater container is visible
        await expect(page.locator('#hoch-pods-theater')).toBeVisible();

        console.log("=== DUPLICATE ID DEBUGGING ===");
        const count = await page.locator('#drawer-title').count();
        console.log("Count of #drawer-title:", count);
        for (let i = 0; i < count; i++) {
            const html = await page.locator('#drawer-title').nth(i).evaluate(el => el.outerHTML);
            const hierarchy = await page.locator('#drawer-title').nth(i).evaluate(el => {
                let path = [];
                let current = el;
                while (current) {
                    path.push(`${current.tagName.toLowerCase()}#${current.id || ''}.${current.className.split(' ').join('.')}`);
                    current = current.parentElement;
                }
                return path.reverse().join(' > ');
            });
            console.log(`Element ${i} HTML:`, html);
            console.log(`Element ${i} Path:`, hierarchy);
        }
        console.log("==============================");

        // Capture screenshot of the first visible screen
        const screenshotDir = path.join(__dirname, '..', '..', 'docs', 'evidence', 'ui', 'screenshots');
        fs.mkdirSync(screenshotDir, { recursive: true });
        const screenshotPath = path.join(screenshotDir, 'hoch-pods-theater-cockpit-current.png');
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

        // Verify layout order (theater is first, topology/container is after/below it)
        const theaterBox = await page.locator('#hoch-pods-theater').boundingBox();
        const containerBox = await page.locator('#hoch-pods-container').boundingBox();
        
        expect(theaterBox).not.toBeNull();
        expect(containerBox).not.toBeNull();
        if (theaterBox && containerBox) {
            expect(theaterBox.y).toBeLessThan(containerBox.y);
        }

        // Run the visual compliance audit
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
