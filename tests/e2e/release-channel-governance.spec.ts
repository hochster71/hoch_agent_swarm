import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("@legacy @compat @deorbited Release Channel & Tag Governance E2E", () => {
  test("loads the dashboard, navigates to Release Provenance, and asserts channel widgets", async ({ page, request }) => {
    // 1. Assert backend API endpoint directly
    const apiResponse = await request.get("/api/v1/release/channel-governance");
    expect(apiResponse.ok()).toBeTruthy();
    const data = await apiResponse.json();
    
    expect(data.policy).toBeDefined();
    expect(data.policy.allowed_channels).toContain("local_dev");
    expect(data.policy.allowed_channels).toContain("candidate");
    expect(data.policy.allowed_channels).toContain("formal");
    
    expect(data.current_release).toBeDefined();
    expect(data.current_release.head_sha).toBeDefined();
    expect(data.current_release.release_finalization_status).toBeDefined();

    // 2. Go to the dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 3. Click the Release Provenance nav item
    const navItem = page.locator("#nav-release-provenance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 4. Expect release channel panel elements to be visible
    const panel = page.locator("#release-channel-governance-panel");
    await expect(panel).toBeVisible();

    await expect(page.locator("h2:has-text('Release Channel Governance')")).toBeVisible();
    await expect(panel.locator("strong:has-text('Current Channel:')")).toBeVisible();
    await expect(panel.locator("strong:has-text('Release Tag:')")).toBeVisible();
    await expect(panel.locator("strong:has-text('Tag Alignment:')")).toBeVisible();

    const currentChannel = data.current_release.channel;
    const finalizationStatus = data.current_release.release_finalization_status;
    const tagPointsAtHead = data.current_release.tag_points_at_head;
    const tagStatus = data.current_release.tag_status;

    // 5. Assert tag alignment texts based on status
    const tagStatusLocator = page.locator("#release-tag-status");
    const tagAlignLocator = page.locator("#release-tag-alignment-status");
    const finalStatusLocator = page.locator("#release-formal-finalization-status");

    if (tagPointsAtHead) {
      await expect(tagStatusLocator).toHaveText("Tag Points at HEAD");
    } else {
      if (tagStatus === "STALE_TAG") {
        await expect(page.locator("text=Stale Tag").first()).toBeVisible();
      } else if (tagStatus === "NO_RELEASE_TAG") {
        await expect(page.locator("text=No Release Tag").first()).toBeVisible();
      }
      // Ensure we do not display "Formal Release Ready" if it's stale or missing
      await expect(finalStatusLocator).not.toHaveText("Formal Release Ready");
    }

    // 6. Test submitting a candidate promotion decision
    const selectChannel = page.locator("#select-requested-channel");
    await selectChannel.selectOption("candidate");
    
    // Fill in a candidate tag
    const tagInput = page.locator("#input-requested-tag");
    await tagInput.fill("v0.1.7-CANDIDATE-E2E-TEST");

    // Listen for alert box dialog
    page.once("dialog", async dialog => {
      expect(dialog.message()).toContain("Decision submitted");
      await dialog.accept();
    });

    const submitBtn = page.locator("#release-channel-request-button");
    await submitBtn.click();

    // 7. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-channel-governance.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured screenshot at: ${screenshotPath}`);
  });
});
