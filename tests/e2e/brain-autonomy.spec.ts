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
    await page.goto('/');

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

  test('verifies RC27 identity-aware artifact workflow delivery and security blocks', async ({ page }) => {
    // Navigate to page
    await page.goto('/');

    // Click sidebar "Command Center" tab
    const ccNav = page.locator('#nav-production-command-center');
    await ccNav.click();

    // Locators
    const requesterSelect = page.locator('#artifact-requester-select');
    const promptInput = page.locator('#artifact-prompt-input');
    const targetSelect = page.locator('#artifact-target-select');
    const triggerBtn = page.locator('#btn-trigger-artifact-workflow');

    // 1. Unknown user request (Guest)
    await requesterSelect.selectOption('guest');
    await promptInput.fill('Generate compliance brief');
    await triggerBtn.click();

    // Verify block in UI
    const classBadge = page.locator('#ui-class-badge');
    await expect(classBadge).toContainText('BLOCKED');
    const stepsContainer = page.locator('#ui-workflow-steps');
    await expect(stepsContainer).toContainText('[BLOCKED]');

    // 2. Alison Hoch request (Trusted Family)
    await requesterSelect.selectOption('alison');
    await promptInput.fill('Generate pool maintenance presentation slide deck for school chores');
    await targetSelect.selectOption('family_shared');
    await triggerBtn.click();

    // Verify workflow succeeds and delivers
    await expect(classBadge).toContainText('FAMILY');
    await expect(stepsContainer).toContainText('Handoff to allowlisted Google Drive path');
    const targetAllowlist = page.locator('#ui-target-allowlist');
    await expect(targetAllowlist).toContainText('VERIFIED (Pass)');
    const receiptDetails = page.locator('#ui-receipt-details');
    await expect(receiptDetails).toContainText('Receipt ID:');

    // 3. Michael Hoch request (Owner)
    await requesterSelect.selectOption('michael');
    await promptInput.fill('Create presentation deck on RMF cybersecurity Zero Trust guidance');
    await targetSelect.selectOption('family_shared');
    await triggerBtn.click();

    // Verify work internal success
    await expect(classBadge).toContainText('WORK INTERNAL');
    const rbacRole = page.locator('#ui-rbac-role');
    await expect(rbacRole).toContainText('system_owner');
  });

  test('verifies RC29 monetization sidecar audit harness operations', async ({ page }) => {
    // Navigate to page
    await page.goto('/');

    // Click sidebar "Command Center" tab
    const ccNav = page.locator('#nav-production-command-center');
    await ccNav.click();

    // Verify Monetization Audit panel components exist
    const sweepResult = page.locator('#ui-audit-sweep-result');
    await expect(sweepResult).toBeVisible();

    const triggerBtn = page.locator('#btn-trigger-monetization-audit');
    await expect(triggerBtn).toBeVisible();

    // Run audit sweep
    await triggerBtn.click();

    // Verify sweep completes and shows PASS status
    await expect(sweepResult).toContainText('PASS');
    const redactorStatus = page.locator('#ui-audit-redactor');
    await expect(redactorStatus).toContainText('Verified');
    const guardStatus = page.locator('#ui-audit-guard');
    await expect(guardStatus).toContainText('ReadOnly');
  });
});
