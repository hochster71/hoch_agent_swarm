import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Formal Release Approval Simulator E2E", () => {
  test("navigates to Governance Cockpit, runs preview, requests approval, and approves gate successfully", async ({ page, request }) => {
    // 1. Go to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Create a candidate release packet first
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.2");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Create candidate packet for approval E2E test");
    const channelSelect = page.locator("#candidate-packet-channel-select");
    await channelSelect.selectOption("candidate");

    // Set dialog handler to print messages and handle the prompt dialog
    page.on("dialog", async dialog => {
      console.log(`E2E Dialog type: ${dialog.type()}, message: ${dialog.message()}`);
      if (dialog.type() === "prompt") {
        await dialog.accept("Simulated formal release approval for E2E testing");
      } else {
        await dialog.accept();
      }
    });

    const createCandidateBtn = page.locator("#candidate-packet-create-button");
    await createCandidateBtn.click();

    // Wait for packet status to update
    const candidateStatusEl = page.locator("#candidate-packet-status");
    await expect(candidateStatusEl).not.toHaveText("None", { timeout: 10000 });

    const candidateIdEl = page.locator("#candidate-packet-id");
    const packetId = await candidateIdEl.textContent();
    expect(packetId).not.toBeNull();

    // 4. Fill Formal Release Finalization Preview form
    const previewSelect = page.locator("#formal-preview-candidate-select");
    await expect(previewSelect).toBeVisible();
    await previewSelect.selectOption(packetId!);

    const previewOperatorInput = page.locator("#formal-preview-operator-input");
    await previewOperatorInput.fill("Michael Hoch");

    const previewReasonInput = page.locator("#formal-preview-reason-input");
    await previewReasonInput.fill("Preview formal readiness for approval E2E test");

    // 5. Click preview button
    const previewBtn = page.locator("#formal-preview-create-button");
    await expect(previewBtn).toBeVisible();
    await previewBtn.click();

    // Wait for preview status to update
    const previewStatusEl = page.locator("#formal-preview-status");
    await expect(previewStatusEl).not.toHaveText("None", { timeout: 10000 });

    const previewIdEl = page.locator("#formal-preview-id");
    const previewId = await previewIdEl.textContent();
    expect(previewId).not.toBeNull();
    expect(previewId?.trim().length).toBeGreaterThan(5);

    // 6. Request approval
    const requestApprovalBtn = page.locator("#formal-preview-request-approval-button");
    await expect(requestApprovalBtn).toBeVisible();
    await requestApprovalBtn.click();

    // Assert status transitions to PENDING and button disappears
    await expect(requestApprovalBtn).not.toBeVisible();
    const approvalStatusEl = page.locator("#formal-preview-approval-status");
    await expect(approvalStatusEl).toBeVisible();
    await expect(approvalStatusEl).toHaveText("PENDING");

    // 7. Verify gate surfaces in the cockpit pending list
    const pendingList = page.locator("#gov-pending-list");
    const gateCard = pendingList.locator(".card", { hasText: `channel_decision:formal:${previewId}` });
    await expect(gateCard).toBeVisible();

    // 8. Approve the gate
    const approveBtn = gateCard.locator("button:has-text('Approve')");
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Assert status transitions to APPROVED
    await expect(approvalStatusEl).toHaveText("APPROVED");
    
    // Assert simulation report path is rendered
    const reportPathEl = page.locator("#formal-preview-approval-report-path");
    await expect(reportPathEl).toHaveText(`dist/formal-previews/${previewId}/formal_release_approval_report.json`);

    // 9. Verify report files are generated on disk
    const workspaceRoot = "/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm";
    const jsonPath = path.join(workspaceRoot, "dist/formal-previews", previewId!, "formal_release_approval_report.json");
    const mdPath = path.join(workspaceRoot, "dist/formal-previews", previewId!, "formal_release_approval_report.md");
    
    expect(fs.existsSync(jsonPath)).toBeTruthy();
    expect(fs.existsSync(mdPath)).toBeTruthy();

    const reportContent = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
    expect(reportContent.formal_preview_id).toBe(previewId);
    expect(reportContent.decision).toBe("approved");

    // 10. Assert no git tags were created
    const tagMatch = fs.existsSync(path.join(workspaceRoot, ".git/refs/tags/v0.1.7-candidate.2"));
    expect(tagMatch).toBeFalsy();

    // Wait for transition and take screenshot
    await page.waitForTimeout(1000);
    const screenshotPath = "artifacts/qa/formal-release-approval.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured screenshot at: ${screenshotPath}`);
  });
});
