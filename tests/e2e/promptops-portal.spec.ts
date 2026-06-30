import { test, expect } from "@playwright/test";

test.describe("PromptOps Portal E2E Validation", () => {
  test("verifies prompt scoring, rewriting, and closeout gates", async ({ page }) => {
    // 1. Go to main dashboard page
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Navigate to PromptOps tab
    const promptopsTab = page.locator("#nav-promptops");
    await expect(promptopsTab).toBeVisible();
    await promptopsTab.click();

    // Click the internal React component tab button for PromptOps Portal
    const reactTabBtn = page.locator("button:has-text('PromptOps Portal')");
    await expect(reactTabBtn).toBeVisible();
    await reactTabBtn.click();

    // 3. Test scenario 1: Weak Prompt Preset
    const weakPresetBtn = page.locator("button:has-text('⚠️ Weak / Broad Prompt')");
    await expect(weakPresetBtn).toBeVisible();
    await weakPresetBtn.click();

    const evaluateBtn = page.locator("button:has-text('EVALUATE AND GENERATE CONTRACT')");
    await expect(evaluateBtn).toBeVisible();
    await evaluateBtn.click();

    // Verify scorecard and risk levels
    const contractPanel = page.locator(".glass-panel:has-text('Contract Specification')");
    const riskBadge = contractPanel.locator("span:has-text('MEDIUM')").first();
    await expect(riskBadge).toBeVisible();

    const statusBadge = contractPanel.locator("span:has-text('BLOCKED_UNTIL_SCOPED')").first();
    await expect(statusBadge).toBeVisible();

    // 4. Test scenario 2: Strong Scoped Prompt Preset
    const strongPresetBtn = page.locator("button:has-text('✅ Strong Scoped Prompt')");
    await expect(strongPresetBtn).toBeVisible();
    await strongPresetBtn.click();
    await evaluateBtn.click();

    const strongStatusBadge = contractPanel.locator("span:has-text('EXECUTABLE')").first();
    await expect(strongStatusBadge).toBeVisible();

    const lowRiskBadge = contractPanel.locator("span:has-text('LOW')").first();
    await expect(lowRiskBadge).toBeVisible();

    // 5. Test scenario 3: Closeout Claim Rejection
    const closeoutClaimInput = page.locator("input[value='production ready']");
    await expect(closeoutClaimInput).toBeVisible();

    const submitClaimBtn = page.locator("button:has-text('SUBMIT CLAIM & VERIFY GATES')");
    await expect(submitClaimBtn).toBeVisible();
    await submitClaimBtn.click();

    // Verify rejection card displays
    const errorCard = page.locator("div:has-text('Closeout Gate: CLAIM REJECTED')").first();
    await expect(errorCard).toBeVisible();
  });
});
