import { test, expect } from '@playwright/test';

test.describe('RC52.1 HOCH PODS Space Swarm Theater E2E Tests', () => {

    test('1. Verify Space Swarm Theater structures, orbit field, launch bay, and controls', async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');

        // 1. Verify Swarm HUD components exist
        const theater = page.locator('#hoch-pods-container');
        await expect(theater).toBeVisible();

        const core = page.locator('#hoch-space-command-core');
        await expect(core).toBeVisible();

        const swarmField = page.locator('#hoch-orbital-swarm-field');
        await expect(swarmField).toBeVisible();

        const launchBay = page.locator('#hoch-pod-launch-bay');
        await expect(launchBay).toBeVisible();

        const profileDrawer = page.locator('#hoch-agent-profile-drawer');
        await expect(profileDrawer).not.toBeNull();

        // 2. Verify controls button presence
        await expect(page.locator('#toggle-theater-mode')).toBeVisible();
        await expect(page.locator('#toggle-data-mode')).toBeVisible();
        await expect(page.locator('#toggle-reduce-motion')).toBeVisible();
        await expect(page.locator('#toggle-show-stale')).toBeVisible();
        await expect(page.locator('#toggle-show-profiles')).toBeVisible();
        await expect(page.locator('#toggle-show-scorecards')).toBeVisible();

        // Find pod-cyber capsule (should be either in orbit or launch bay)
        const cyberPod = page.locator('#pod-card-pod-cyber');
        await expect(cyberPod).toBeVisible();

        // Click Cyber Pod to open the HUD inspector drawer
        await cyberPod.click({ force: true });
        await expect(profileDrawer).toHaveClass(/active/);

        // Verify the drawer is populated with pod details
        await expect(page.locator('#drawer-title')).toContainText('Cyber');
        await expect(page.locator('#drawer-role')).not.toContainText('UNKNOWN');
        
        // Verify scorecard metrics
        const scorecard = page.locator('#hoch-pod-scorecard-layer');
        await expect(scorecard).toBeVisible();
        await expect(page.locator('#scorecard-trust')).not.toContainText('0%');

        // 4. Verify Reduced Motion Toggle
        const reduceMotionBtn = page.locator('#toggle-reduce-motion');
        await reduceMotionBtn.click();
        await expect(theater).toHaveClass(/reduce-motion-active/);

        // Toggle it back off
        await reduceMotionBtn.click();
        await expect(theater).not.toHaveClass(/reduce-motion-active/);

        // 5. Verify Data Mode toggle (should empty the active orbit layers)
        const dataModeBtn = page.locator('#toggle-data-mode');
        await dataModeBtn.click();

        // Under Data Mode, all active capsules should render inside launch bay, and orbit pods layer should be empty
        const orbitPodsLayer = page.locator('#orbit-pods-container-layer');
        await expect(orbitPodsLayer.locator('.orbit-pod-container')).toHaveCount(0);

        // Click back to Theater Mode
        await page.locator('#toggle-theater-mode').click();

        // 6. Verify page is free from duplicate percent signs
        const bodyText = await page.innerText('body');
        expect(bodyText).not.toContain('%%');
    });
});
