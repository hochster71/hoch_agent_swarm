import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Operator Release Decision Room E2E", () => {
  test("evaluates candidate release, runs simulation, updates ledger, and exports decision memo", async ({ page }) => {
    // 1. Go to dashboard
    await page.goto("/");
    
    page.on("pageerror", err => {
      console.error("BROWSER PAGE ERROR:", err.message);
    });
    page.on("console", msg => {
      if (msg.type() === "error") {
        console.error("BROWSER CONSOLE ERROR:", msg.text());
      }
    });

    await page.waitForLoadState("networkidle");

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Create a candidate release packet to guarantee we have an active packet
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.decroom");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Create candidate packet for decision room E2E test");
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

    // 4. Set dialog handler to print messages and handle prompt dialogs
    page.on("dialog", async dialog => {
      console.log(`E2E Dialog type: ${dialog.type()}, message: ${dialog.message()}`);
      if (dialog.type() === "prompt") {
        await dialog.accept("Michael Hoch operator simulation approval E2E justification");
      } else {
        await dialog.accept();
      }
    });

    // 5. Select the candidate in the Release Decision Room select
    const decRoomSelect = page.locator("#decision-room-candidate-select");
    await expect(decRoomSelect).toBeVisible();
    
    // Give options a moment to populate or select by value
    await expect(async () => {
      await decRoomSelect.selectOption(cleanPacketId);
    }).toPass({ timeout: 5000 });

    // Assert details grid becomes visible
    const detailsGrid = page.locator("#decision-room-details-grid");
    await expect(detailsGrid).toBeVisible();

    // Assert status fields render correct packet ID
    const decStatusPacket = page.locator("#dec-status-packet");
    await expect(decStatusPacket).toHaveText(cleanPacketId);

    // 6. Click simulate approval
    const simulateApproveBtn = page.locator("#btn-decision-simulate-approve");
    await expect(simulateApproveBtn).toBeVisible();
    await simulateApproveBtn.click();

    // 7. Verify the simulated decision is added to the historical decision ledger
    const ledgerTable = page.locator("#gov-ledger-tbody");
    await expect(ledgerTable).toContainText("simulated_release_decision");
    await expect(ledgerTable).toContainText("APPROVED");

    // 8. Test Export Decision Memo download
    const exportBtn = page.locator("#btn-export-decision-memo");
    await expect(exportBtn).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await exportBtn.click();
    const download = await downloadPromise;

    const downloadPath = await download.path();
    expect(downloadPath).not.toBeNull();
    
    const suggestedName = download.suggestedFilename();
    expect(suggestedName).toBe(`operator-release-decision-memo-${cleanPacketId}.md`);

    const memoContent = fs.readFileSync(downloadPath!, "utf8");
    expect(memoContent).toContain("# Operator Release Decision Memo");
    expect(memoContent).toContain(cleanPacketId);
    expect(memoContent).toContain("dec-sim-");
    expect(memoContent).toContain("APPROVED");
    expect(memoContent).toContain("🔒 **Simulation Mode Notice**");

    // 9. Assert no git tags were created
    const workspaceRoot = "/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm";
    const tagExists = fs.existsSync(path.join(workspaceRoot, `.git/refs/tags/v0.1.7-candidate.decroom`));
    expect(tagExists).toBeFalsy();

    // Capture screenshot of the cockpit decision room
    await page.waitForTimeout(1000);
    const screenshotPath = "artifacts/qa/operator-release-decision-room.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured decision room screenshot at: ${screenshotPath}`);
  });
});
