import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Release Evidence Archive Preview E2E", () => {
  test("calculates archive preview, renders metrics, displays warnings, and supports downloading manifests", async ({ page }) => {
    // Collect browser console errors
    const consoleErrors: string[] = [];
    page.on("console", msg => {
      console.log(`[Browser Console ${msg.type()}]: ${msg.text()}`);
      if (msg.type() === "error" && !msg.text().includes("WebSocket")) {
        consoleErrors.push(msg.text());
      }
    });
    page.on("pageerror", err => {
      console.error("BROWSER PAGE EXCEPTION:", err);
    });

    // 1. Go to dashboard with ?test_mode=true
    await page.goto("/?test_mode=true");
    await page.waitForLoadState("networkidle");

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Confirm archive preview panel is visible
    const archivePanel = page.locator("#release-evidence-archive-preview-panel");
    await expect(archivePanel).toBeVisible();

    // 4. Details container should be hidden initially
    const detailsContainer = page.locator("#archive-preview-details");
    await expect(detailsContainer).toBeHidden();

    // 5. Trigger preview calculation
    const calcBtn = page.locator("#btn-calculate-archive-preview");
    await expect(calcBtn).toBeVisible();

    const fetchPromise = page.waitForResponse(response =>
      response.url().includes("/api/v1/release/evidence/archive/preview") &&
      response.request().method() === "GET" &&
      response.status() === 200
    );
    await calcBtn.click();
    const response = await fetchPromise;
    const responseData = await response.json();
    await page.waitForTimeout(200);

    // 6. Assert details are now visible
    await expect(detailsContainer).toBeVisible();

    // Check paths & checksum
    const pathEl = page.locator("#archive-preview-path");
    await expect(pathEl).toHaveText(responseData.planned_archive_path);

    const checksumEl = page.locator("#archive-preview-checksum");
    await expect(checksumEl).toHaveText(responseData.checksum);

    // Check counts
    const inclCount = page.locator("#archive-preview-count-included");
    await expect(inclCount).toHaveText(responseData.included_count.toString());

    const exclCount = page.locator("#archive-preview-count-excluded");
    await expect(exclCount).toHaveText(responseData.excluded_count.toString());

    const reviewCount = page.locator("#archive-preview-count-review");
    await expect(reviewCount).toHaveText(responseData.needs_review_count.toString());

    const missingCount = page.locator("#archive-preview-count-missing");
    await expect(missingCount).toHaveText(responseData.missing_count.toString());

    // Check warnings if any
    const warningsPanel = page.locator("#archive-preview-warnings");
    if (responseData.needs_review_count > 0 || responseData.missing_count > 0) {
      await expect(warningsPanel).toBeVisible();
      const warningsList = page.locator("#archive-preview-warnings-list li");
      const count = await warningsList.count();
      expect(count).toBeGreaterThan(0);
    } else {
      await expect(warningsPanel).toBeHidden();
    }

    // Check planned included table body
    const tableBody = page.locator("#archive-preview-included-tbody");
    if (responseData.included_count === 0) {
      await expect(tableBody).toContainText("No artifacts selected for retention.");
    } else {
      await expect(tableBody.locator("tr").first()).toBeVisible();
    }

    // 7. Check Markdown download
    const exportMdBtn = page.locator("#btn-export-preview-markdown");
    await expect(exportMdBtn).toBeVisible();
    const [downloadMd] = await Promise.all([
      page.waitForEvent("download"),
      exportMdBtn.click()
    ]);
    expect(downloadMd.suggestedFilename()).toBe("release-evidence-archive-preview.md");

    // 8. Check JSON download
    const exportJsonBtn = page.locator("#btn-export-preview-json");
    await expect(exportJsonBtn).toBeVisible();
    const [downloadJson] = await Promise.all([
      page.waitForEvent("download"),
      exportJsonBtn.click()
    ]);
    expect(downloadJson.suggestedFilename()).toBe("release-evidence-archive-preview.json");

    // 9. Verify no browser console errors occurred
    expect(consoleErrors).toEqual([]);

    // 10. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-evidence-archive-preview.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E archive preview screenshot at: ${screenshotPath}`);
  });
});
