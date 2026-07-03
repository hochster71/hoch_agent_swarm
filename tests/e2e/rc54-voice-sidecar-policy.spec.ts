import { test, expect } from '@playwright/test';

test.describe('RC54 Voice Sidecar Phase 1 Policy', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://127.0.0.1:8765/');
        await page.waitForTimeout(500);
    });

    test('Voice panel renders with correct defaults', async ({ page }) => {
        const panel = page.locator('#voice-sidecar-panel');
        await expect(panel).toBeVisible();
        const toggle = page.locator('#voice-enabled-toggle');
        await expect(toggle).not.toBeChecked();
        const status = page.locator('#voice-policy-status');
        await expect(status).toHaveText('DISABLED');
    });

    test('Voice disabled by default - test button does not speak', async ({ page }) => {
        const testBtn = page.locator('#voice-test-btn');
        await testBtn.click();
        // Mock SpeechSynthesis to verify no call
        const spoken = await page.evaluate(() => {
            return window.__lastUtterance || null;
        });
        expect(spoken).toBeNull();
    });

    test('Enabling voice allows LOCAL_TTS test event', async ({ page }) => {
        await page.locator('#voice-enabled-toggle').check();
        const testBtn = page.locator('#voice-test-btn');
        await testBtn.click();
        const lastSpoken = await page.locator('#voice-last-spoken').textContent();
        expect(lastSpoken).toContain('TEST_VOICE');
    });

    test('Sanitizer redacts secrets before speech', async ({ page }) => {
        await page.locator('#voice-enabled-toggle').check();
        await page.evaluate(() => {
            window.HASFVoiceSidecar.speakEvent('TEST', 'sk-1234567890abcdef secret key here');
        });
        const last = await page.locator('#voice-last-spoken').textContent();
        expect(last).toContain('[REDACTED]');
    });

    test('Existing visual baseline and theatrical elements unchanged', async ({ page }) => {
        const baseShell = page.locator('img.base-shell');
        await expect(baseShell).toHaveAttribute('src', /hoch-pods-theater-reference/);
        const podBay = page.locator('#hoch-pods-container, .pods-grid');
        await expect(podBay).toBeVisible();
    });

    test('Rate limit and severity gate work', async ({ page }) => {
        await page.locator('#voice-enabled-toggle').check();
        const result = await page.evaluate(() => {
            const policy = window.HASFVoiceSidecar.getPolicy();
            policy.EVENT_COUNT = 11; // exceed limit
            return window.HASFVoiceSidecar.speakEvent('INFO', 'should not speak');
        });
        expect(result).toBe(false);
    });
});
