import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Formal Release Authority Gate E2E", () => {
  test("implements authority gate by default, permits authority request with TEST_MODE, and gates promotion", async ({ page, request }) => {
    // 1. Go to dashboard with ?test_mode=true so frontend passes is_test=true
    await page.goto("/?test_mode=true");
    await page.waitForLoadState("networkidle");

    page.on("pageerror", err => {
      console.error("BROWSER PAGE ERROR:", err.message);
    });
    page.on("console", msg => {
      if (msg.type() === "error") {
        console.error("BROWSER CONSOLE ERROR:", msg.text());
      }
    });

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Create a candidate release packet to guarantee we have an active packet
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.authgate");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Create candidate packet for authority gate E2E test");
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

    // 4. Select the candidate in the Release Decision Room select
    const decRoomSelect = page.locator("#decision-room-candidate-select");
    await expect(decRoomSelect).toBeVisible();
    await expect(async () => {
      await decRoomSelect.selectOption(cleanPacketId);
    }).toPass({ timeout: 5000 });

    // Assert details grid becomes visible
    const detailsGrid = page.locator("#decision-room-details-grid");
    await expect(detailsGrid).toBeVisible();

    // Assert authority gate panel is visible
    const authPanel = page.locator("#release-authority-gate-panel");
    await expect(authPanel).toBeVisible();

    // Assert status shows preview mode by default (authority absent)
    const authStatus = page.locator("#gov-authority-status");
    await expect(authStatus).toHaveText("ABSENT (Preview Mode)");

    const realPromoteBtn = page.locator("#btn-execute-real-promotion");
    await expect(realPromoteBtn).toBeHidden();

    // 5. Test direct programmatic promote without token (must return 403)
    const promoteResponse = await request.post("/api/v1/release/promote", {
      data: {
        candidate_packet_id: cleanPacketId,
        operator: "Michael Hoch",
        authority_token: "invalid-token-bypass"
      }
    });
    expect(promoteResponse.status()).toBe(403);

    // 6. Setup dialog handlers for alerts/confirms during UI clicks
    let dialogCount = 0;
    page.on("dialog", async dialog => {
      dialogCount++;
      console.log(`[E2E Dialog] type: ${dialog.type()}, message: ${dialog.message()}`);
      await dialog.accept();
    });

    // 7. Click Request Release Authority
    const requestAuthBtn = page.locator("#btn-request-authority");
    await expect(requestAuthBtn).toBeEnabled();
    await requestAuthBtn.click();

    // Assert Request modal is visible and candidate ID matches
    const modal = page.locator("#authority-request-modal");
    await expect(modal).toBeVisible();
    
    const modalCandidateId = page.locator("#modal-authority-candidate-id");
    await expect(modalCandidateId).toHaveText(cleanPacketId);

    const grantBtn = page.locator("#btn-modal-grant-authority");
    await expect(grantBtn).toBeDisabled();

    // Check confirmation checkbox
    const confirmChk = page.locator("#chk-confirm-authority-scope");
    await confirmChk.check();
    await expect(grantBtn).toBeEnabled();

    // Click Grant
    await grantBtn.click();

    // Modal should close
    await expect(modal).toBeHidden();

    // Status should be GRANTED
    await expect(authStatus).toContainText("GRANTED");

    // Details should be visible and token value should start with auth-tok-
    const activeTokenVal = page.locator("#gov-active-token-val");
    await expect(activeTokenVal).toContainText("auth-tok-");

    const countdown = page.locator("#gov-token-countdown");
    await expect(countdown).toContainText("0");

    // Real promotion button should now be visible
    await expect(realPromoteBtn).toBeVisible();

    // 8. Trigger real promotion execution
    await realPromoteBtn.click();

    // Assert screenshot captured
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-authority-gate.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E authority gate screenshot at: ${screenshotPath}`);
  });
});
