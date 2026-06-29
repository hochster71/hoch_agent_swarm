import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("NetworkOps Self-Healing E2E Spec", () => {
  test("loads NetworkOps view, triggers diagnostics, and requests healing approval", async ({ page }) => {
    // Navigate to dashboard root
    await page.goto("/", { waitUntil: "networkidle" });

    // Handle alerts automatically
    let lastAlertMsg = "";
    page.on("dialog", async dialog => {
      lastAlertMsg = dialog.message();
      await dialog.accept();
    });

    // 1. Click NetworkOps Nav
    const navItem = page.locator("#nav-networkops");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 2. Assert View Visible
    const viewItem = page.locator("#view-networkops");
    await expect(viewItem).toBeVisible();
    await expect(viewItem).not.toHaveClass(/\bhidden\b/);

    // 3. Assert metrics are loaded
    const perfScore = page.locator("#networkops-perf-score");
    await expect(perfScore).not.toHaveText("--");
    await expect(perfScore).toContainText("%");

    // 4. Verify incidents list displays rows
    const firstRow = page.locator("#networkops-incidents-tbody tr").first();
    await expect(firstRow).toBeVisible();

    // 5. Trigger diagnostics scan
    const diagBtn = page.locator("#btn-networkops-diagnose");
    await expect(diagBtn).toBeVisible();
    await diagBtn.click();
    await page.waitForTimeout(500); // Wait for async alert handling
    expect(lastAlertMsg).toContain("Diagnostic scan completed");

    // 6. Request approval for inc-001 (disruptive)
    const reqApprovalBtn = page.locator("button:has-text('Request Approval')").first();
    await expect(reqApprovalBtn).toBeVisible();
    await reqApprovalBtn.click();
    await page.waitForTimeout(500);
    expect(lastAlertMsg).toContain("Safety approval request registered");

    // Save screenshot of the live cockpit instrument
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/networkops-self-healing.png");
    const outputDir = path.dirname(screenshotPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath, fullPage: false });
  });
});
