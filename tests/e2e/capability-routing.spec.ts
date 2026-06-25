import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Device Capability Routing Center E2E", () => {
  test("switches to Governance view, loads routing decisions, and inspects a routing event", async ({ page }) => {
    // Collect browser console errors
    const consoleErrors: string[] = [];
    page.on("console", msg => {
      if (msg.type() === "error") {
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

    // 3. Verify routing center panel and refresh button are visible
    const routingPanel = page.locator("#device-routing-center-panel");
    const refreshBtn = page.locator("#device-routing-refresh-button");
    await expect(routingPanel).toBeVisible({ timeout: 10000 });
    await expect(refreshBtn).toBeVisible();

    // 4. Force a refresh to load simulated history items
    await refreshBtn.click();
    await page.waitForTimeout(500);

    // 5. Select the first routing decision element in the list
    const historyList = page.locator("#device-routing-history-list");
    const firstRow = historyList.locator(".gate-row").first();
    await expect(firstRow).toBeVisible();
    
    // Click the first row to open details in the inspector panel
    await firstRow.click();

    // 6. Verify inspector panel displays matching details
    const inspectorPanel = page.locator("#device-routing-inspector-panel");
    await expect(inspectorPanel).toBeVisible();
    await expect(inspectorPanel).not.toHaveClass(/hidden/);

    const routingId = await page.locator("#routing-inspect-id").innerText();
    expect(routingId.startsWith("RT-")).toBe(true);

    const tableBody = page.locator("#routing-inspect-table-body");
    await expect(tableBody).toBeVisible();
    const rowCount = await tableBody.locator("tr").count();
    expect(rowCount).toBeGreaterThan(0);

    // 7. Verify no console errors occurred during interactions
    expect(consoleErrors).toEqual([]);

    // 8. Save screenshot evidence
    const screenshotPath = "artifacts/qa/capability-routing.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E capability routing screenshot at: ${screenshotPath}`);
  });
});
