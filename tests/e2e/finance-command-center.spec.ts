import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("@legacy @compat @deorbited Finance Command Center E2E and Validation Audit", () => {
  test("loads the Finance dashboard, validates rendering of panels, categories, and zero math deviations", async ({ page }) => {
    const consoleErrors: string[] = [];
    const asset404s: string[] = [];

    // Capture console errors
    page.on("console", (msg) => {
      // Ignore websocket connection failures or warnings
      if (msg.type() === "error" && !msg.text().includes("WebSocket")) {
        consoleErrors.push(msg.text());
      }
    });

    // Capture 404 response errors
    page.on("response", (response) => {
      // Ignore tailwind.css if it returns 404, we want to audit actual fatal JS crashes
      if (response.status() === 404 && !response.url().includes("tailwind.css")) {
        asset404s.push(response.url());
      }
    });

    // 1. Load root route
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Click Finance Command Center Tab in sidebar
    const financeNavBtn = page.locator("#nav-finance-command-center");
    await expect(financeNavBtn).toBeVisible();
    await financeNavBtn.click();

    // 3. Assert the view-finance-command-center is active and visible (not hidden)
    const financeView = page.locator("#view-finance-command-center");
    await expect(financeView).not.toHaveClass(/\bhidden\b/);

    // 4. Assert North Star Header and Metric totals
    await expect(page.locator("#finance-northstar-header")).toBeVisible();
    await expect(page.locator("#monthly-income-total")).toContainText("$19,474.62");
    await expect(page.locator("#monthly-bills-total")).toContainText("$6,328.98");
    await expect(page.locator("#monthly-available-total")).toContainText("$13,145.64");
    await expect(page.locator("#debt-total")).toContainText("$141,420.00");
    await expect(page.locator("#asset-total")).toContainText("$212,000.00");
    await expect(page.locator("#savings-this-session")).toContainText("$262.37");

    // 5. Assert Panels are present and populated
    await expect(page.locator("#finance-income-panel")).toBeVisible();
    await expect(page.locator("#finance-bills-master-grid")).toBeVisible();
    await expect(page.locator("#finance-spending-intelligence")).toBeVisible();
    await expect(page.locator("#finance-debt-command-center")).toBeVisible();
    await expect(page.locator("#finance-legal-credit-hub")).toBeVisible();
    await expect(page.locator("#finance-insurance-estate-panel")).toBeVisible();
    await expect(page.locator("#finance-assets-panel")).toBeVisible();
    await expect(page.locator("#finance-investing-dca-panel")).toBeVisible();
    await expect(page.locator("#finance-cost-cutting-panel")).toBeVisible();
    await expect(page.locator("#finance-business-panel")).toBeVisible();
    await expect(page.locator("#finance-agent-activity-stream")).toBeVisible();
    await expect(page.locator("#finance-qa-audit-panel")).toBeVisible();

    // 6. Assert Bills table rows structure
    const billsList = page.locator("#fin-bills-list");
    await expect(billsList).toContainText("PennyMac Mortgage");
    await expect(billsList).toContainText("SkylaFCU 2nd Mortgage");
    // Verify sub-totals render
    await expect(billsList).toContainText("Sub-total (Housing & Loans):");

    // 7. Verify tooltip hovers don't crash
    const superchargerCard = page.locator("#fin-spending-transactions >> text=Tesla Supercharger");
    await expect(superchargerCard).toBeVisible();
    await superchargerCard.hover(); // Verify hover trigger works without console crashes

    // 8. Assert QA audit panel matches PASS status
    const qaBadge = page.locator("#finance-qa-badge");
    await expect(qaBadge).toContainText("ALL MATHEMATICAL INTEGRITY VALIDATED");
    await expect(qaBadge).toHaveClass(/\bpass\b/);

    // Ensure no JS crashes occurred
    expect(consoleErrors.length).toBe(0);
    expect(asset404s.length).toBe(0);
  });
});
