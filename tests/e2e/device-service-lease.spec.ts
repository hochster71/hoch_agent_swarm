import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Device Service Health Lease Manager E2E", () => {
  test("registers, approves, updates leases, and asserts UI status badges", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", msg => {
      if (msg.type() === "error" && !msg.text().includes("WebSocket")) {
        consoleErrors.push(msg.text());
      }
    });

    // 1. Navigate to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Click on the Governance tab nav button
    const navGov = page.locator("#nav-governance");
    await expect(navGov).toBeVisible();
    await navGov.click();

    // 3. Verify DaaS Registry panel
    const registryPanel = page.locator("#device-service-registry-panel");
    await expect(registryPanel).toBeVisible({ timeout: 10000 });

    // 4. Click the discovery button
    const discoverBtn = page.locator("#device-discovery-run-button");
    await expect(discoverBtn).toBeVisible();
    await discoverBtn.click();

    // 5. Wait for the discovery card mock item to appear
    const discoveredIpadCard = page.locator("#discovered-card-discovery-ipad-mock");
    await expect(discoveredIpadCard).toBeVisible({ timeout: 15000 });
    await discoveredIpadCard.click();

    // 6. Approve the device
    const notesArea = page.locator("#approval-operator-notes");
    await notesArea.fill("Approval with lease verification E2E");
    const approveBtn = page.locator("#btn-device-approve");
    await approveBtn.click();

    // 7. Verify node is approved and default lease is active
    const approvedNode = page.locator("#service-node-registry-list");
    await expect(approvedNode).toContainText("Michael's iPad Mini", { timeout: 10000 });
    await expect(approvedNode).toContainText("Lease Active");
    await expect(approvedNode).toContainText("100% (AC)");

    // 8. Update lease to 'sleeping' state via API
    await page.evaluate(async () => {
      await fetch("/api/v1/devices/lease/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id: "discovery-ipad-mock",
          battery_level: 42.0,
          power_source: "Battery",
          network_status: "degraded",
          availability: "sleeping",
          lease_duration_seconds: 300
        })
      });
    });

    // 9. Reload/Refresh registry UI data
    const refreshBtn = page.locator("#device-service-refresh-button");
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
    } else {
      // Fallback: reload page
      await page.reload();
      await page.waitForLoadState("networkidle");
      await page.locator("#nav-governance").click();
    }

    // 10. Verify lease status reflects expiration/inactivity
    const registryList = page.locator("#service-node-registry-list");
    await expect(registryList).toContainText("Lease Expired", { timeout: 10000 });
    await expect(registryList).toContainText("42% (Battery)");

    // 11. Capture verification screenshot
    const screenshotPath = "artifacts/qa/device-service-lease.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured device service lease E2E screenshot at: ${screenshotPath}`);

    // Verify no console errors occurred
    expect(consoleErrors).toEqual([]);
  });
});
