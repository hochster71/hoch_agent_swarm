import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Release Evidence Archive Seal Preview E2E", () => {
  test("asserts seal preview state starts blocked, transitions to ready after authority and classification setup, and supports export downloads", async ({ page }) => {
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

    // Register dialog handler early to catch ALL alerts/confirms automatically
    page.on("dialog", async dialog => {
      console.log(`[E2E Dialog] type: ${dialog.type()}, message: ${dialog.message()}`);
      await dialog.accept();
    });

    // 1. Go to dashboard with ?test_mode=true
    await page.goto("/?test_mode=true");
    await page.waitForLoadState("networkidle");

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Verify seal preview panel is visible
    const sealPanel = page.locator("#release-evidence-archive-seal-preview-panel");
    await expect(sealPanel).toBeVisible();

    const detailsContainer = page.locator("#archive-seal-preview-details");
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

    // 4. Calculate initial preview (should be BLOCKED because no packet, no authority, unclassified evidence)
    const genBtn = page.locator("#btn-generate-archive-seal-preview");
    await expect(genBtn).toBeVisible();

    const fetchPromiseBlocked = page.waitForResponse(response =>
      response.url().includes("/api/v1/release/evidence/archive/seal-preview") &&
      response.request().method() === "GET" &&
      response.status() === 200
    );
    await genBtn.click();
    const responseBlocked = await fetchPromiseBlocked;
    const dataBlocked = await responseBlocked.json();
    await page.waitForTimeout(200);

    // Details must be visible
    await expect(detailsContainer).toBeVisible();

    // Status must be BLOCKED
    const statusEl = page.locator("#archive-seal-status");
    await expect(statusEl).toHaveText("BLOCKED");

    // Warnings must be visible
    const warningsPanel = page.locator("#archive-seal-preview-warnings");
    await expect(warningsPanel).toBeVisible();

    // 5. Create a candidate release packet
    console.log("Creating release candidate packet...");
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.6-seal-preview");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Testing seal preview E2E");
    const channelSelect = page.locator("#candidate-packet-channel-select");
    await channelSelect.selectOption("candidate");

    const createCandidateBtn = page.locator("#candidate-packet-create-button");
    await createCandidateBtn.click();

    // Wait for candidate packet status to update
    const candidateStatusEl = page.locator("#candidate-packet-status");
    await expect(candidateStatusEl).not.toHaveText("None", { timeout: 10000 });

    const candidateIdEl = page.locator("#candidate-packet-id");
    const packetId = await candidateIdEl.textContent();
    expect(packetId).not.toBeNull();
    const cleanPacketId = packetId!.trim();

    // 6. Select the candidate in the Release Decision Room select
    const decRoomSelect = page.locator("#decision-room-candidate-select");
    await expect(decRoomSelect).toBeVisible();

    const fetchAuthorityState = page.waitForResponse(response =>
      response.url().includes(`/api/v1/release/authority/state/${cleanPacketId}`) &&
      response.status() === 200
    );

    await expect(async () => {
      await decRoomSelect.selectOption(cleanPacketId);
    }).toPass({ timeout: 5000 });

    // Wait for details load to complete
    await fetchAuthorityState;
    await page.waitForTimeout(500);

    // Assert details grid is visible
    const detailsGrid = page.locator("#decision-room-details-grid");
    await expect(detailsGrid).toBeVisible();

    // 7. Request and grant release authority
    console.log("Requesting and granting authority token...");
    const requestAuthBtn = page.locator("#btn-request-authority");
    await expect(requestAuthBtn).toBeEnabled();
    await requestAuthBtn.click();

    const modal = page.locator("#authority-request-modal");
    await expect(modal).toBeVisible();

    const modalCandidateId = page.locator("#modal-authority-candidate-id");
    await expect(modalCandidateId).toHaveText(cleanPacketId);

    const grantBtn = page.locator("#btn-modal-grant-authority");
    const confirmChk = page.locator("#chk-confirm-authority-scope");
    await confirmChk.check();
    await expect(grantBtn).toBeEnabled();
    await grantBtn.click();

    await expect(modal).toBeHidden();

    // Confirm authority is active
    const authStatus = page.locator("#gov-authority-status");
    await expect(authStatus).toContainText("GRANTED");

    // 8. Classify all items as RETAIN to clear unclassified blockers
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

    // Record list of archives files before generating seal preview
    const archiveDir = path.resolve(__dirname, "../../dist/archives");
    const initialFiles = fs.existsSync(archiveDir) ? fs.readdirSync(archiveDir) : [];

    // 9. Regenerate seal preview (should now be READY)
    console.log("Regenerating seal preview...");
    const fetchPromiseReady = page.waitForResponse(response =>
      response.url().includes("/api/v1/release/evidence/archive/seal-preview") &&
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

    // Check planned metadata values
    const sealIdEl = page.locator("#archive-seal-id");
    await expect(sealIdEl).toHaveText(dataReady.seal_id);
    expect(dataReady.seal_id).not.toBe("N/A");

    const archiveIdEl = page.locator("#archive-seal-archive-id");
    await expect(archiveIdEl).toHaveText(dataReady.archive_id);
    expect(dataReady.archive_id).not.toBe("N/A");

    const manifestHashEl = page.locator("#archive-seal-manifest-hash");
    await expect(manifestHashEl).toHaveText(dataReady.manifest_hash);
    expect(dataReady.manifest_hash).not.toBe("N/A");

    const custodyPathEl = page.locator("#archive-seal-custody-path");
    await expect(custodyPathEl).toHaveText(dataReady.custody_path);

    const operatorEl = page.locator("#archive-seal-operator");
    await expect(operatorEl).toHaveText("Michael Hoch");

    // 10. Check export downloads
    console.log("Verifying export downloads...");
    const exportMdBtn = page.locator("#btn-export-seal-preview-markdown");
    await expect(exportMdBtn).toBeVisible();
    const [downloadMd] = await Promise.all([
      page.waitForEvent("download"),
      exportMdBtn.click()
    ]);
    expect(downloadMd.suggestedFilename()).toBe("release-evidence-archive-seal-preview.md");

    const exportJsonBtn = page.locator("#btn-export-seal-preview-json");
    await expect(exportJsonBtn).toBeVisible();
    const [downloadJson] = await Promise.all([
      page.waitForEvent("download"),
      exportJsonBtn.click()
    ]);
    expect(downloadJson.suggestedFilename()).toBe("release-evidence-archive-seal-preview.json");

    // 11. Verify zero-mutation safety invariant (no new archive files were created)
    const finalFiles = fs.existsSync(archiveDir) ? fs.readdirSync(archiveDir) : [];
    expect(finalFiles).toEqual(initialFiles);

    // 12. Verify no browser console errors occurred
    expect(consoleErrors).toEqual([]);

    // 13. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-evidence-archive-seal-preview.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E seal preview screenshot at: ${screenshotPath}`);
  });
});
