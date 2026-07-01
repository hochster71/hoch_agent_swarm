import { test, expect } from "@playwright/test";

test.describe("Defect Zero Command Center E2E Verification", () => {
  test("asserts that Defect Zero panel displays correct telemetry, metrics, and tools", async ({ page }) => {
    // 1. Go to root page
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Select and click Defect Zero navigation button
    const defectNavBtn = page.locator("#nav-defect-zero");
    await expect(defectNavBtn).toBeVisible();
    await defectNavBtn.click();

    // 3. Verify target view-defect-zero is visible
    const defectView = page.locator("#view-defect-zero");
    await expect(defectView).toBeVisible();
    await expect(defectView).not.toHaveClass(/\bhidden\b/);

    // 4. Assert DOM elements exist
    await expect(page.locator("#defect-open-count")).toBeVisible();
    await expect(page.locator("#defect-critical-count")).toBeVisible();
    await expect(page.locator("#defect-warning-count")).toBeVisible();
    await expect(page.locator("#defect-security-count")).toBeVisible();

    // 5. Verify registered sandbox tools container is populated
    await expect(page.locator("#defect-tools-list")).toContainText("pytest");
    await expect(page.locator("#defect-tools-list")).toContainText("playwright");

    // 6. Verify agent scoreboard displays Claude Code
    await expect(page.locator("#defect-routing-status")).toContainText("Claude Code");
  });
});
