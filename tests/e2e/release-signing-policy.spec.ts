import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("@legacy @compat @deorbited Release Signing Policy Gate E2E", () => {
  test("loads the dashboard, navigates to Release Provenance, and asserts signing policy widgets", async ({ page, request }) => {
    // 1. Assert backend signing policy API endpoint directly
    const apiResponse = await request.get("/api/v1/release/signing-policy");
    expect(apiResponse.ok()).toBeTruthy();
    const data = await apiResponse.json();
    
    expect(data.policy).toBeDefined();
    expect(data.policy.unsigned_status).toBe("SIGNING_PENDING");
    expect(data.current_release).toBeDefined();
    expect(data.current_release.version).toBeDefined();
    expect(data.allowed_actions).toContain("continue_local_dev");

    // 2. Go to the dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 3. Click the Release Provenance nav item
    const navItem = page.locator("#nav-release-provenance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 4. Expect signing policy elements and text to be visible
    const panel = page.locator("#release-signing-policy-panel");
    await expect(panel).toBeVisible();

    await expect(page.locator("h2:has-text('Release Signing Policy')")).toBeVisible();
    await expect(page.locator("strong:has-text('Signature Status')")).toBeVisible();
    await expect(page.locator("strong:has-text('Signing Required for Formal Release')")).toBeVisible();
    await expect(page.locator("text=Local Dev Allows Unsigned Evidence")).toBeVisible();
    await expect(page.locator("text=Formal Release Blocks Unsigned Artifacts")).toBeVisible();

    // 5. Assert signature-specific states
    const signatureStatus = data.current_release.signature_status;
    const statusLocator = page.locator("#release-signature-status");
    if (signatureStatus === "unsigned") {
      await expect(statusLocator).toHaveText("Signing Pending");
      await expect(page.locator("#btn-signing-continue-dev")).toBeVisible();
      // Ensure we do not display "Formal Release Ready" since it is unsigned and not waived
      await expect(page.locator("#release-finalization-status")).not.toHaveText("Formal Release Ready");
    } else if (signatureStatus === "signed") {
      await expect(statusLocator).toHaveText("Signed");
    } else if (signatureStatus === "waived") {
      await expect(statusLocator).toHaveText("Waived With Operator Approval");
    }

    // 6. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-signing-policy.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured screenshot at: ${screenshotPath}`);
  });
});
