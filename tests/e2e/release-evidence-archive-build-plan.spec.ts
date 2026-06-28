import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Release Evidence Archive Build Plan E2E", () => {
  test("asserts build plan state starts blocked, transitions to ready after retention classification, and supports export downloads", async ({ page }) => {
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

    // 3. Verify dry run panel is visible
    const planPanel = page.locator("#release-evidence-archive-build-plan-panel");
    await expect(planPanel).toBeVisible();

    const detailsContainer = page.locator("#archive-build-plan-details");
    await expect(detailsContainer).toBeHidden();

    // 3b. Reset all classifications to needs-review for a clean baseline
    console.log("Resetting all classifications to needs-review...");
    await page.evaluate(async () => {
      const res = await fetch("/api/v1/release/evidence/retention");
      const data = await res.json();
      const items = data.evidence || [];
      for (const item of items) {
        if (item.retention_decision !== "needs-review") {
          await fetch("/api/v1/release/evidence/retention/classify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              evidence_id: item.evidence_id,
              retention_decision: "needs-review"
            })
          });
        }
      }
      await (window as any).loadEvidenceRetentionList();
    });
    await page.waitForTimeout(500);

    // 4. Calculate initial plan (should be BLOCKED because items default to needs-review)
    const genBtn = page.locator("#btn-generate-archive-build-plan");
    await expect(genBtn).toBeVisible();

    const fetchPromise = page.waitForResponse(response =>
      response.url().includes("/api/v1/release/evidence/archive/build-plan") &&
      response.request().method() === "GET" &&
      response.status() === 200
    );
    await genBtn.click();
    const responseBlocked = await fetchPromise;
    const dataBlocked = await responseBlocked.json();
    await page.waitForTimeout(200);

    // Details must be visible
    await expect(detailsContainer).toBeVisible();

    // Status must be BLOCKED
    const statusEl = page.locator("#archive-build-status");
    await expect(statusEl).toHaveText("BLOCKED");

    // Warnings must be visible
    const warningsPanel = page.locator("#archive-build-plan-warnings");
    await expect(warningsPanel).toBeVisible();

    // 5. Classify all items as RETAIN to clear unclassified blockers
    console.log("Bulk classifying evidence items as RETAIN via page.evaluate...");
    await page.evaluate(async () => {
      const res = await fetch("/api/v1/release/evidence/retention");
      const data = await res.json();
      const needsReview = (data.evidence || []).filter((item: any) => item.retention_decision === "needs-review");
      
      for (const item of needsReview) {
        await fetch("/api/v1/release/evidence/retention/classify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            evidence_id: item.evidence_id,
            retention_decision: "retain"
          })
        });
      }
      
      await (window as any).loadEvidenceRetentionList();
    });
    await page.waitForTimeout(500);


    // 6. Regenerate plan (should now be READY)
    const fetchPromiseReady = page.waitForResponse(response =>
      response.url().includes("/api/v1/release/evidence/archive/build-plan") &&
      response.request().method() === "GET" &&
      response.status() === 200
    );
    await genBtn.click();
    const responseReady = await fetchPromiseReady;
    const dataReady = await responseReady.json();
    await page.waitForTimeout(200);

    // Status must update to READY
    await expect(statusEl).toHaveText("READY");

    // Warnings must be hidden
    await expect(warningsPanel).toBeHidden();

    // Check paths & checksum
    const targetPathEl = page.locator("#archive-build-target-path");
    await expect(targetPathEl).toHaveText(dataReady.planned_archive_path);

    const manifestHashEl = page.locator("#archive-build-manifest-hash");
    await expect(manifestHashEl).toHaveText(dataReady.expected_manifest_hash);

    // Check operations table
    const opsTableBody = page.locator("#archive-build-operations-tbody");
    await expect(opsTableBody.locator("tr").first()).toBeVisible();

    // 7. Check export downloads
    const exportMdBtn = page.locator("#btn-export-build-plan-markdown");
    await expect(exportMdBtn).toBeVisible();
    const [downloadMd] = await Promise.all([
      page.waitForEvent("download"),
      exportMdBtn.click()
    ]);
    expect(downloadMd.suggestedFilename()).toBe("release-evidence-archive-build-plan.md");

    const exportJsonBtn = page.locator("#btn-export-build-plan-json");
    await expect(exportJsonBtn).toBeVisible();
    const [downloadJson] = await Promise.all([
      page.waitForEvent("download"),
      exportJsonBtn.click()
    ]);
    expect(downloadJson.suggestedFilename()).toBe("release-evidence-archive-build-plan.json");

    // 8. Verify no browser console errors occurred
    expect(consoleErrors).toEqual([]);

    // 9. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-evidence-archive-build-plan.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E archive build plan screenshot at: ${screenshotPath}`);
  });
});
