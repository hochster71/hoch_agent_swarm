import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Release Evidence Retention Manager E2E", () => {
  test("indexes evidence, allows classification, and updates status metrics without disk mutation", async ({ page }) => {
    // 1. Go to dashboard with ?test_mode=true
    await page.goto("/?test_mode=true");
    await page.waitForLoadState("networkidle");

    page.on("pageerror", err => {
      console.error("BROWSER PAGE ERROR:", err.message);
    });
    page.on("console", msg => {
      if (msg.type() === "error") {
        console.log(`[Browser Console] ${msg.text()}`);
      }
    });

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Confirm retention manager panel is visible
    const retentionPanel = page.locator("#release-evidence-retention-panel");
    await expect(retentionPanel).toBeVisible();

    // 5. Verify untracked items are in the table
    const tableBody = page.locator("#retention-evidence-tbody");
    await expect(tableBody.locator("tr").first()).toBeVisible();

    // 6. Test dropdown interaction
    const firstRowSelect = tableBody.locator("tr").first().locator("select");
    await expect(firstRowSelect).toBeVisible();

    // Ensure it is in "needs-review" state to start the test deterministically
    const currentVal = await firstRowSelect.inputValue();
    if (currentVal !== "needs-review") {
      const fetchPromise = page.waitForResponse(response =>
        response.url().includes('/api/v1/release/evidence/retention') &&
        response.request().method() === 'GET' &&
        response.status() === 200
      );
      await firstRowSelect.selectOption("needs-review");
      await fetchPromise;
      await page.waitForTimeout(200);
    }

    // Now get clean baseline counts for the transition from needs-review to retain
    const reviewCountEl = page.locator("#retention-count-review");
    await expect(reviewCountEl).not.toBeEmpty();
    const initialReviewText = await reviewCountEl.textContent();
    const initialReview = parseInt(initialReviewText || "0", 10);

    const retainedCountEl = page.locator("#retention-count-retained");
    await expect(retainedCountEl).not.toBeEmpty();
    const initialRetainedText = await retainedCountEl.textContent();
    const initialRetained = parseInt(initialRetainedText || "0", 10);

    // Change value to retain
    const fetchPromise = page.waitForResponse(response =>
      response.url().includes('/api/v1/release/evidence/retention') &&
      response.request().method() === 'GET' &&
      response.status() === 200
    );
    await firstRowSelect.selectOption("retain");
    await fetchPromise;
    await page.waitForTimeout(200);

    // Assert counts updated
    const afterReviewText = await reviewCountEl.textContent();
    const afterReview = parseInt(afterReviewText || "0", 10);
    expect(afterReview).toBe(initialReview - 1);

    const expectedRetainedText = (initialRetained + 1).toString();
    await expect(retainedCountEl).toHaveText(expectedRetainedText);

    // 7. Click Scan/Sync Evidence to refresh and verify state is persisted
    const scanBtn = page.locator("#btn-scan-evidence");
    const scanFetchPromise = page.waitForResponse(response =>
      response.url().includes('/api/v1/release/evidence/retention') &&
      response.request().method() === 'GET' &&
      response.status() === 200
    );
    await scanBtn.click();
    await scanFetchPromise;
    await page.waitForTimeout(200);

    // State should remain same
    await expect(firstRowSelect).toHaveValue("retain");
    await expect(retainedCountEl).toHaveText(expectedRetainedText);

    // 8. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-evidence-retention.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E retention screenshot at: ${screenshotPath}`);
  });
});
