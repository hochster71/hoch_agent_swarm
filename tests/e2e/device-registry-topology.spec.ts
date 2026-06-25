import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Device Registry Topology E2E", () => {
  test("renders Cluster Command Map 2.0 and verifies Mobile Fleet Drawer details", async ({ page }) => {
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

    // 2. Verify Command Map 2.0 layout containers are visible
    const commandMap = page.locator("#cluster-command-map-v2");
    const agentRail = page.locator("#cluster-agent-command-rail");
    const fleetDrawer = page.locator("#cluster-device-fleet-drawer");
    const mobileSection = page.locator("#cluster-device-mobile-section");

    await expect(commandMap).toBeVisible({ timeout: 10000 });
    await expect(agentRail).toBeVisible({ timeout: 10000 });
    await expect(fleetDrawer).toBeVisible({ timeout: 10000 });
    await expect(mobileSection).toBeVisible({ timeout: 10000 });

    // 3. Open the collapsible fleet drawer by clicking the toggle tab
    const drawerToggle = page.locator("#fleet-drawer-toggle-tab");
    await expect(drawerToggle).toBeVisible();
    await drawerToggle.click();

    // Verify the drawer is expanded (transform transition is done)
    await expect(fleetDrawer).toHaveClass(/fleet-drawer-expanded/);

    // 4. Assert all iPad model IDs are visible
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).toContain("MTXQ2LL/A");
    expect(bodyText).toContain("MUU62LL/A");
    expect(bodyText).toContain("MGNV2LL/A");

    // 5. Locate an iPad card in the Mobile Fleet list and click it
    const ipadProCard = page.locator("#fleet-card-IPAD_PRO_11");
    await expect(ipadProCard).toBeVisible();
    await ipadProCard.click();

    // 6. Verify that the Selected Node Inspector updates with the node info
    const inspector = page.locator("#cluster-selected-node-inspector");
    await expect(inspector).toBeVisible();
    const inspectorText = await inspector.innerText();
    expect(inspectorText).toContain("MTXQ2LL/A");
    expect(inspectorText).toContain("10.0.0.44");

    // 7. Verify no browser console errors occurred
    expect(consoleErrors).toEqual([]);

    // 8. Capture verification screenshot
    const screenshotPath = "artifacts/qa/device-registry-topology.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E topology screenshot at: ${screenshotPath}`);
  });
});
