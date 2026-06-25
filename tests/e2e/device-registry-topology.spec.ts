import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Device Registry Topology E2E", () => {
  test("renders all three new onboarded iPads and the updated iMac IP on the dashboard", async ({ page }) => {
    // 1. Go to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Locate the node cards on the dashboard
    const pro11Card = page.locator("#node-card-IPAD_PRO_11");
    const mini5Card = page.locator("#node-card-IPAD_MINI_1");
    const mini3Card = page.locator("#node-card-IPAD_MINI_2");
    const imacCard = page.locator("#node-card-L2");

    // 3. Assert all are visible on the dashboard
    await expect(pro11Card).toBeVisible({ timeout: 10000 });
    await expect(mini5Card).toBeVisible({ timeout: 10000 });
    await expect(mini3Card).toBeVisible({ timeout: 10000 });
    await expect(imacCard).toBeVisible({ timeout: 10000 });

    // 4. Assert correct text outputs/metadata
    await expect(pro11Card).toContainText("Michael's iPad pro 11-inch MTXQ2LL/A");
    await expect(pro11Card).toContainText("10.0.0.44");

    await expect(mini5Card).toContainText("iPad mini MUU62LL/A");
    await expect(mini5Card).toContainText("10.0.0.91");

    await expect(mini3Card).toContainText("iPad mini MGNV2LL/A");
    await expect(mini3Card).toContainText("10.0.0.137");

    await expect(imacCard).toContainText("MICHAEL'S IMAC");
    await expect(imacCard).toContainText("10.0.0.92");

    // 5. Take screenshot
    const screenshotPath = "artifacts/qa/device-registry-topology.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E topology screenshot at: ${screenshotPath}`);
  });
});
