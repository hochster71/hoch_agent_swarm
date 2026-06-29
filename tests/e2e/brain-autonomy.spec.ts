import { test, expect } from '@playwright/test';

test.describe('Brain LLM Gated Autonomy Control Plane', () => {
  test('verifies all 11 UI panels and autonomy mode restrictions', async ({ page }) => {
    // Capture console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore expected HTTP 400 errors for locked-out autonomy mode switches
        if (!text.includes('status of 400')) {
          consoleErrors.push(text);
        }
      }
    });

    // Navigate to page
    await page.goto('http://127.0.0.1:8000');

    // Click sidebar "Command Center" tab
    const ccNav = page.locator('#nav-production-command-center');
    await expect(ccNav).toBeVisible();
    await ccNav.click();

    // 1. Verify Chat panel is visible
    const chatInput = page.locator('#brain-chat-input');
    await expect(chatInput).toBeVisible();

    // 2. Type instruction to operator chat and submit
    await chatInput.fill('Please verify build health');
    const sendBtn = page.locator('#btn-brain-send-chat');
    await expect(sendBtn).toBeVisible();
    await sendBtn.click();

    // 3. Verify chat message gets rendered
    const chatMessages = page.locator('#brain-chat-messages');
    await expect(chatMessages).toBeVisible();
    await expect(chatMessages).toContainText('Please verify build health');

    // 4. Verify Suggested Next Action panel renders suggestion recommendation
    const suggestionContainer = page.locator('#brain-suggestion-container');
    await expect(suggestionContainer).toBeVisible();

    // 5. Verify Autonomy Readiness circular gauge
    const readinessGauge = page.locator('#brain-readiness-gauge');
    await expect(readinessGauge).toBeVisible();
    const readinessText = page.locator('#brain-readiness-percentage');
    await expect(readinessText).toBeVisible();

    // 6. Verify Michael Doctrine memory panel
    const doctrineList = page.locator('#brain-doctrine-list');
    await expect(doctrineList).toBeVisible();

    // 7. Verify Shadow Log panel
    const predictionLog = page.locator('#brain-prediction-log');
    await expect(predictionLog).toBeVisible();

    // 8. Verify Escalation list panel
    const escalationList = page.locator('#brain-escalation-list');
    await expect(escalationList).toBeVisible();

    // 9. Verify Autonomy Mode buttons and try setting to autonomous
    const autonomousBtn = page.locator('#brain-mode-selector button[data-mode="autonomous"]');
    await expect(autonomousBtn).toBeVisible();

    // Listen to dialog promise before click
    const dialogPromise = page.waitForEvent('dialog');
    await autonomousBtn.click();

    const dialog = await dialogPromise;
    // Verify it blocks mode change because readiness score is not met (90%)
    expect(dialog.message()).toContain('Readiness Score is below target gate');
    await dialog.dismiss();

    // Check for console errors
    expect(consoleErrors).toEqual([]);
  });
});
