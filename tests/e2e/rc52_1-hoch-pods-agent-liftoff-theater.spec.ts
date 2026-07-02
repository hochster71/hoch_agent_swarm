import { test, expect } from '@playwright/test';

test.describe('RC52.1 HOCH PODS Agent Lift-Off & Integration Movie Board E2E Tests', () => {

    test('1. Verify Cinematic Rendering Order and DOM ID Presence', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // Verify required DOM structures and IDs exist
        await expect(page.locator('#hoch-pods-theater')).toBeVisible();
        await expect(page.locator('#hoch-agent-liftoff-movie-board')).toBeVisible();
        await expect(page.locator('#hoch-agent-lifecycle-grid')).toBeVisible();
        await expect(page.locator('#hoch-agent-profile-snapshot')).toBeVisible();
        await expect(page.locator('#hoch-destination-confirmed-strip')).toBeVisible();
        await expect(page.locator('#hoch-theater-system-status')).toBeVisible();
        await expect(page.locator('#hoch-agent-movie-detail-drawer')).not.toBeNull();
        await expect(page.locator('#hoch-theater-control-bar')).toBeVisible();
        await expect(page.locator('#hoch-stale-quarantine-layer')).not.toBeNull();

        // Verify legacy elements still exist for backward compatibility
        await expect(page.locator('#hoch-pods-theater-panel')).toBeVisible();
        await expect(page.locator('#hoch-pods-container')).toBeVisible();

        // Verify cinematic rendering order: theater loads before other panels in viewport
        const theaterBox = await page.locator('#hoch-pods-theater').boundingBox();
        const topologyBox = await page.locator('#hoch-pods-topology-panel').boundingBox();
        
        expect(theaterBox).not.toBeNull();
        expect(topologyBox).not.toBeNull();
        if (theaterBox && topologyBox) {
            expect(theaterBox.y).toBeLessThan(topologyBox.y);
        }
    });

    test('2. Verify Lifecycle Grid, Profile Snapshot, and Control Interaction', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // Assert 15 lifecycle steps/clips exist
        const lifecycleGrid = page.locator('#hoch-agent-lifecycle-grid');
        const clips = lifecycleGrid.locator('.lifecycle-clip');
        await expect(clips).toHaveCount(15);

        // Hover or click a clip to test details drawer
        const firstClip = clips.first();
        await firstClip.click();

        // Detail drawer should become active
        const detailDrawer = page.locator('#hoch-agent-movie-detail-drawer');
        await expect(detailDrawer).toHaveClass(/active/);
        await expect(detailDrawer).toContainText('CLIP 01');

        // Test Profile Snapshot visibility toggle
        const toggleProfilesBtn = page.locator('#toggle-show-profiles');
        const profileSnapshot = page.locator('#hoch-agent-profile-snapshot');
        
        await expect(profileSnapshot).toBeVisible();
        await toggleProfilesBtn.click();
        await expect(profileSnapshot).not.toBeVisible();
        await toggleProfilesBtn.click(); // restore

        // Test Motion Reduction
        const toggleMotionBtn = page.locator('#toggle-reduce-motion');
        await toggleMotionBtn.click();
        await expect(page.locator('body')).toHaveClass(/reduce-motion-active/);
        await toggleMotionBtn.click(); // restore

        // Replay Movie sequence trigger
        const replayBtn = page.locator('#replay-movie');
        await expect(replayBtn).toBeVisible();
        await replayBtn.click();
    });
});
