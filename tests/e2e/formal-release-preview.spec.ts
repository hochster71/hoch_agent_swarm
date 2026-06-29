import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Formal Release Finalization Preview E2E", () => {
  test("navigates to Governance Cockpit, triggers formal release preview, and captures screenshot", async ({ page, request }) => {
    // 1. Go to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Click Governance Cockpit nav item
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Assert Formal Release Finalization Preview panel exists
    const panel = page.locator("#formal-release-preview-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator("h3:has-text('Formal Release Finalization Preview')")).toBeVisible();

    // 4. Submit candidate packet first to ensure we have a packet to select
    // Fill Candidate Release Packet Builder form to generate a packet
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.1");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Create candidate packet for E2E testing preview");
    const channelSelect = page.locator("#candidate-packet-channel-select");
    await channelSelect.selectOption("candidate");

    // Set dialog handler to auto-accept the success alerts
    page.on("dialog", async dialog => {
      console.log(`E2E Dialog text: ${dialog.message()}`);
      await dialog.accept();
    });

    const createCandidateBtn = page.locator("#candidate-packet-create-button");
    await createCandidateBtn.click();

    // Wait for packet status to update
    const candidateStatusEl = page.locator("#candidate-packet-status");
    await expect(candidateStatusEl).not.toHaveText("None", { timeout: 10000 });

    const candidateIdEl = page.locator("#candidate-packet-id");
    const packetId = await candidateIdEl.textContent();
    expect(packetId).not.toBeNull();

    // 5. Fill Formal Release Finalization Preview form
    const previewSelect = page.locator("#formal-preview-candidate-select");
    await expect(previewSelect).toBeVisible();
    
    // Select the candidate packet we just created
    await previewSelect.selectOption(packetId!);

    const previewOperatorInput = page.locator("#formal-preview-operator-input");
    await previewOperatorInput.fill("Michael Hoch");

    const previewReasonInput = page.locator("#formal-preview-reason-input");
    await previewReasonInput.fill("Preview formal readiness for E2E testing candidate packet");

    // 6. Assert required label texts are visible
    await expect(panel.locator("span:has-text('No Tags Are Created')")).toBeVisible();
    await expect(panel.locator("span:has-text('No Signing Is Performed')")).toBeVisible();
    await expect(panel.locator("span:has-text('No Publishing Is Performed')")).toBeVisible();
    await expect(panel.locator("span:has-text('Preview Only')")).toBeVisible();

    // 7. Click preview button
    const previewBtn = page.locator("#formal-preview-create-button");
    await expect(previewBtn).toBeVisible();
    await previewBtn.click();

    // 8. Assert generated preview values populate
    const previewStatusEl = page.locator("#formal-preview-status");
    await expect(previewStatusEl).not.toHaveText("None", { timeout: 10000 });

    const previewIdEl = page.locator("#formal-preview-id");
    await expect(previewIdEl).not.toHaveText("None");
    const previewId = await previewIdEl.textContent();
    expect(previewId).not.toBeNull();
    expect(previewId?.trim().length).toBeGreaterThan(5);

    const previewReadyEl = page.locator("#formal-preview-formal-ready");
    await expect(previewReadyEl).toBeVisible();

    const previewPathEl = page.locator("#formal-preview-path");
    await expect(previewPathEl).not.toHaveText("None");

    const blockersEl = page.locator("#formal-preview-blockers");
    await expect(blockersEl).toBeVisible();

    const actionsEl = page.locator("#formal-preview-required-actions");
    await expect(actionsEl).toBeVisible();

    // 9. API query check
    const apiResponse = await request.get("/api/v1/release/formal-preview");
    expect(apiResponse.ok()).toBeTruthy();
    const previews = await apiResponse.json();
    expect(previews.length).toBeGreaterThan(0);
    
    // Check newest preview matches
    const newestPreview = previews[0];
    expect(newestPreview.formal_preview_id).toBe(previewId);
    expect(newestPreview.candidate_packet_id).toBe(packetId);

    // Wait for visual transition
    await page.waitForTimeout(1000);

    // 10. Capture screenshot
    const screenshotPath = "artifacts/qa/formal-release-preview.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured screenshot at: ${screenshotPath}`);
  });
});
