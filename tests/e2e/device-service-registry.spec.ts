import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Device-as-a-Service Registry E2E", () => {
  test("runs local device discovery, inspects details, and approves a node", async ({ page }) => {
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

    // 3. Verify that the Device-as-a-Service Registry panel is visible
    const registryPanel = page.locator("#device-service-registry-panel");
    await expect(registryPanel).toBeVisible({ timeout: 10000 });

    // Verify safety disclaimers are present
    const safetyNotice = page.locator("#device-service-safety-notice");
    await expect(safetyNotice).toBeVisible();
    const safetyText = await safetyNotice.innerText();
    expect(safetyText).toContain("Operator Approval Required");
    expect(safetyText).toContain("No Automatic Agent Installation");
    expect(safetyText).toContain("No Credential Attempts");

    // 4. Click the discovery button
    const discoverBtn = page.locator("#device-discovery-run-button");
    await expect(discoverBtn).toBeVisible();
    await discoverBtn.click();

    // 5. Wait for the discovery card mock item to appear
    const discoveredIpadCard = page.locator("#discovered-card-discovery-ipad-mock");
    await expect(discoveredIpadCard).toBeVisible({ timeout: 15000 });

    // 6. Click on the iPad Mini discovery card
    await discoveredIpadCard.click();

    // 7. Verify approval panel is visible and contains classification
    const approvalPanel = page.locator("#device-service-approval-panel");
    await expect(approvalPanel).toBeVisible();
    
    const deviceName = await page.locator("#approval-device-name").innerText();
    expect(deviceName.toLowerCase()).toContain("ipad mini");

    const fleetGroup = await page.locator("#approval-fleet-group").innerText();
    expect(fleetGroup).toBe("mobile_fleet");

    const computeTier = await page.locator("#approval-compute-tier").innerText();
    expect(computeTier).toBe("edge_light");

    // 8. Type operator notes
    const notesArea = page.locator("#approval-operator-notes");
    await notesArea.fill("Audited and approved by Michael Hoch for tactical mesh support");

    // 9. Click approve button
    const approveBtn = page.locator("#btn-device-approve");
    await approveBtn.click();

    // 10. Verify it gets registered as active node
    const approvedNode = page.locator("#service-node-registry-list");
    await expect(approvedNode).toContainText("Michael's iPad Mini", { timeout: 10000 });
    await expect(approvedNode).toContainText("Lease Active");

    // 11. Capture screenshot of the dashboard state
    const screenshotPath = "artifacts/qa/device-service-registry.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured device service registry E2E screenshot at: ${screenshotPath}`);

    // Verify no console errors occurred
    expect(consoleErrors).toEqual([]);
  });
});
