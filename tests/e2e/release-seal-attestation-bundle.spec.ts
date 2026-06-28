import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("Release Seal Attestation Bundle E2E", () => {
  test("runs preview, requests approval, approves preview, executes seal dry run, and generates attestation bundle successfully", async ({ page, request }) => {
    // 1. Go to dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Navigate to Governance Cockpit
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 3. Create a candidate release packet first
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.4");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Create candidate packet for attestation bundle E2E test");
    const channelSelect = page.locator("#candidate-packet-channel-select");
    await channelSelect.selectOption("candidate");

    // Set dialog handler for alerts and prompts
    page.on("dialog", async dialog => {
      console.log(`E2E Dialog type: ${dialog.type()}, message: ${dialog.message()}`);
      if (dialog.type() === "prompt") {
        await dialog.accept("Simulated formal release approval for attestation bundle E2E testing");
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
    await previewReasonInput.fill("Preview formal readiness for attestation bundle E2E test");

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

    // 6. Request approval
    const requestApprovalBtn = page.locator("#formal-preview-request-approval-button");
    await expect(requestApprovalBtn).toBeVisible();
    await requestApprovalBtn.click();

    // Assert status transitions to PENDING
    await expect(requestApprovalBtn).not.toBeVisible();
    const approvalStatusEl = page.locator("#formal-preview-approval-status");
    await expect(approvalStatusEl).toBeVisible();
    await expect(approvalStatusEl).toHaveText("PENDING");

    // 7. Verify gate surfaces in the cockpit pending list and approve it
    const pendingList = page.locator("#gov-pending-list");
    const gateCard = pendingList.locator(".card", { hasText: `channel_decision:formal:${previewId}` });
    await expect(gateCard).toBeVisible();

    const approveBtn = gateCard.locator("button:has-text('Approve')");
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Assert status transitions to APPROVED
    await expect(approvalStatusEl).toHaveText("APPROVED");

    // 8. Select this approved preview in the Seal Dry Run panel and execute
    const dryRunSelect = page.locator("#seal-dry-run-preview-select");
    await expect(dryRunSelect).toBeVisible();
    await page.waitForTimeout(1000);
    await dryRunSelect.selectOption(previewId!);

    const dryRunOperatorInput = page.locator("#seal-dry-run-operator-input");
    await dryRunOperatorInput.fill("Michael Hoch");

    const executeDryRunBtn = page.locator("#seal-dry-run-execute-button");
    await expect(executeDryRunBtn).toBeVisible();
    await executeDryRunBtn.click();

    // Wait for seal dry run output elements
    const dryRunStatusEl = page.locator("#seal-dry-run-status");
    await expect(dryRunStatusEl).not.toHaveText("None", { timeout: 10000 });
    const dryRunStatus = await dryRunStatusEl.textContent();
    expect(dryRunStatus === "SEAL_READY" || dryRunStatus === "SEAL_BLOCKED").toBeTruthy();

    const dryRunIdEl = page.locator("#seal-dry-run-id");
    const dryRunId = await dryRunIdEl.textContent();
    expect(dryRunId).not.toBeNull();

    // 9. Now select this seal dry run in the Release Seal Attestation Bundle panel
    const attestationPanel = page.locator("#release-seal-attestation-panel");
    await expect(attestationPanel).toBeVisible();

    const attestationSelect = page.locator("#attestation-seal-dry-run-select");
    await expect(attestationSelect).toBeVisible();
    await page.waitForTimeout(1000);
    await attestationSelect.selectOption(dryRunId!);

    const attestationOperator = page.locator("#attestation-operator-input");
    await attestationOperator.fill("Michael Hoch");

    const attestationReason = page.locator("#attestation-reason-input");
    await attestationReason.fill("Attestation bundle after Phase 12 seal dry run");

    // 10. Click Generate Attestation Bundle
    const generateAttestationBtn = page.locator("#attestation-create-button");
    await expect(generateAttestationBtn).toBeVisible();
    await generateAttestationBtn.click();

    // 11. Assert attestation details are updated
    const attestationStatusEl = page.locator("#attestation-status");
    await expect(attestationStatusEl).not.toHaveText("None", { timeout: 10000 });
    const attStatus = await attestationStatusEl.textContent();
    expect(attStatus?.startsWith("ATTESTATION_")).toBeTruthy();

    const attIdEl = page.locator("#attestation-bundle-id");
    const attId = await attIdEl.textContent();
    expect(attId).not.toBeNull();
    expect(attId?.startsWith("attestation-bundle-")).toBeTruthy();

    const noMutationEl = page.locator("#attestation-no-mutation-guarantee");
    await expect(noMutationEl).toHaveText("ACTIVE (No tags/signs applied)");

    // 12. Assert files are written on disk
    const workspaceRoot = "/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm";
    const manifestPath = path.join(workspaceRoot, "dist/attestations", attId!, "release_seal_attestation_bundle_manifest.json");
    const summaryPath = path.join(workspaceRoot, "dist/attestations", attId!, "release_seal_attestation_bundle_summary.md");

    expect(fs.existsSync(manifestPath)).toBeTruthy();
    expect(fs.existsSync(summaryPath)).toBeTruthy();

    const manifestContent = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    expect(manifestContent.attestation_bundle_id).toBe(attId);
    expect(manifestContent.seal_dry_run_id).toBe(dryRunId);
    expect(manifestContent.no_mutation_guarantee).toBeTruthy();

    // 13. Verify safety texts on page
    await expect(attestationPanel).toContainText("No Mutation Guarantee");
    await expect(attestationPanel).toContainText("No Tags Are Created");
    await expect(attestationPanel).toContainText("No Signing Is Performed");
    await expect(attestationPanel).toContainText("No Publishing Is Performed");
    await expect(attestationPanel).toContainText("Attestation Is Not A Formal Release");

    // 14. Query backend list API
    const apiRes = await request.get("/api/v1/release/attestation-bundles");
    expect(apiRes.ok()).toBeTruthy();
    const list = await apiRes.json();
    expect(list.length).toBeGreaterThan(0);
    expect(list[0].attestation_bundle_id).toBe(attId);

    // 15. Take screenshot
    await page.waitForTimeout(1000);
    const screenshotPath = "artifacts/qa/release-seal-attestation-bundle.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E screenshot at: ${screenshotPath}`);
  });
});
