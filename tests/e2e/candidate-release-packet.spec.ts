import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Candidate Release Packet Builder E2E", () => {
  test("navigates to Governance Cockpit, fills candidate form, triggers generation, and captures screenshot", async ({ page, request }) => {
    // 1. Go to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Click Governance Cockpit nav item
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Assert Candidate Release Packet Builder panel exists
    const panel = page.locator("#candidate-release-packet-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator("h3:has-text('Candidate Release Packet Builder')")).toBeVisible();

    // 4. Fill form
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.1");

    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");

    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Candidate packet after governance cockpit seal");

    const channelSelect = page.locator("#candidate-packet-channel-select");
    await channelSelect.selectOption("candidate");

    // 5. Assert required label texts
    await expect(page.locator("span:has-text('No Tags Are Created Automatically')")).toBeVisible();
    await expect(page.locator("span:has-text('Formal Release Still Requires Signing and Tag Alignment')")).toBeVisible();

    // 6. Handle prompt/alert dialogs when submitting
    page.on("dialog", async dialog => {
      console.log(`E2E Dialog text: ${dialog.message()}`);
      await dialog.accept();
    });

    // 7. Click create button
    const createBtn = page.locator("#candidate-packet-create-button");
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    // 8. Assert generated values populate
    const statusEl = page.locator("#candidate-packet-status");
    await expect(statusEl).not.toHaveText("None", { timeout: 10000 });
    await expect(statusEl).toBeVisible();

    const idEl = page.locator("#candidate-packet-id");
    await expect(idEl).not.toHaveText("None");
    await expect(idEl).toBeVisible();
    const packetId = await idEl.textContent();
    expect(packetId).not.toBeNull();
    expect(packetId?.trim().length).toBeGreaterThan(5);

    const pathEl = page.locator("#candidate-packet-path");
    await expect(pathEl).not.toHaveText("None");
    await expect(pathEl).toBeVisible();

    const blockersEl = page.locator("#candidate-packet-blockers");
    await expect(blockersEl).toBeVisible();

    // 9. API query check
    const apiResponse = await request.get("/api/v1/release/candidate-packets");
    expect(apiResponse.ok()).toBeTruthy();
    const packets = await apiResponse.json();
    expect(packets.length).toBeGreaterThan(0);
    
    // Check newest packet
    const newest = packets[0];
    expect(newest.candidate_packet_id).toBe(packetId);
    expect(newest.candidate_version).toBe("0.1.7-candidate.1");
    expect(newest.candidate_channel).toBe("candidate");
    
    // Check formal release ready check
    const formalReadyEl = page.locator("#candidate-packet-formal-ready");
    await expect(formalReadyEl).toBeVisible();
    
    // Since this is in test mode, wait for state to settle
    await page.waitForTimeout(1000);

    // 10. Capture screenshot
    const screenshotPath = "artifacts/qa/candidate-release-packet.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured screenshot at: ${screenshotPath}`);
  });
});
