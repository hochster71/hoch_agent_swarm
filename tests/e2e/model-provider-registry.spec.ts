import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("AI Model Provider Registry E2E", () => {
  test("registers, performs health checks, approves, and tests chat completions on a provider", async ({ page }) => {
    // Dismiss all alert/confirm dialogs automatically
    page.on("dialog", async dialog => {
      console.log(`Dialog opened: [${dialog.type()}] ${dialog.message()}`);
      await dialog.accept();
    });

    const consoleErrors: string[] = [];
    page.on("console", msg => {
      if (msg.type() === "error" && !msg.text().includes("WebSocket")) {
        consoleErrors.push(msg.text());
      }
    });

    // 1. Go to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Click Governance navigation link
    const navGov = page.locator("#nav-governance");
    await expect(navGov).toBeVisible();
    await navGov.click();

    // 3. Verify panels are visible
    const registryPanel = page.locator("#model-provider-registry-panel");
    const testPanel = page.locator("#inference-test-panel");
    await expect(registryPanel).toBeVisible({ timeout: 10000 });
    await expect(testPanel).toBeVisible();

    // 4. Fill registration form
    const providerName = "Playwright Gemma " + Date.now();
    await page.fill("#model-provider-name-input", providerName);
    await page.fill("#model-provider-endpoint-input", "http://localhost:8000/api/v1/mock/llm/v1/chat/completions");
    await page.fill("#model-provider-default-model-input", "gemma-4-12b");
    
    // Check sensitive checkbox
    await page.check("#model-provider-sensitive-context-toggle");

    // Click register button
    const registerBtn = page.locator("#model-provider-register-button");
    await registerBtn.click();

    // 5. Verify the provider is listed in the table
    const providerList = page.locator("#model-provider-list");
    await expect(providerList).toContainText(providerName);

    // Click the row to select it
    const row = providerList.locator("tr", { hasText: providerName }).first();
    await row.click();

    // 6. Verify operation panel is displayed
    const opsPanel = page.locator("#selected-provider-ops-panel");
    await expect(opsPanel).toBeVisible();
    await expect(opsPanel).not.toHaveClass(/hidden/);

    // 7. Click Health Check
    const healthCheckBtn = page.locator("#model-provider-health-check-button");
    await healthCheckBtn.click();
    await page.waitForTimeout(500);

    // Verify health status updates to SUCCESS/available
    await expect(providerList).toContainText("available");

    // 8. Discover Models
    const discoverBtn = page.locator("#model-provider-discover-models-button");
    await discoverBtn.click();
    await page.waitForTimeout(500);

    // 9. Click Approve
    const approveBtn = page.locator("#model-provider-approve-button");
    await approveBtn.click();
    await page.waitForTimeout(500);

    // 10. Test Inference Prompt
    const providerSelect = page.locator("#inference-provider-select");
    await providerSelect.selectOption({ label: `${providerName} (gemma-4-12b)` });

    await page.fill("#inference-prompt-input", "E2E model routing request verification.");
    const sendInferenceBtn = page.locator("#inference-send-button");
    await sendInferenceBtn.click();

    // Wait for response output to show successful completion
    const responseOutput = page.locator("#inference-response-output");
    await expect(responseOutput).not.toContainText("Processing request");
    await expect(responseOutput).toContainText("This is a mock assistant response");

    // Verify history list updates
    const historyList = page.locator("#inference-run-history-list");
    await expect(historyList).toContainText("gemma-4-12b");

    // Verify no console errors occurred
    expect(consoleErrors).toEqual([]);

    // 11. Capture screenshot evidence
    const screenshotPath = "artifacts/qa/model-provider-registry.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E model provider registry screenshot at: ${screenshotPath}`);
  });
});
