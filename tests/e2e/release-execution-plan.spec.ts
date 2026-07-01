import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Formal Release Execution Plan E2E", () => {
  test("generatesordered execution plan, checks authority scopes, updates status, and exports plans", async ({ page }) => {
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

    // 3. Create candidate packet
    const versionInput = page.locator("#candidate-packet-version-input");
    await versionInput.fill("0.1.7-candidate.execplan");
    const operatorInput = page.locator("#candidate-packet-operator-input");
    await operatorInput.fill("Michael Hoch");
    const reasonInput = page.locator("#candidate-packet-reason-input");
    await reasonInput.fill("Create candidate packet for execution plan E2E test");
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

    // 4. Select candidate
    const decRoomSelect = page.locator("#decision-room-candidate-select");
    await expect(decRoomSelect).toBeVisible();
    await expect(async () => {
      await decRoomSelect.selectOption(cleanPacketId);
    }).toPass({ timeout: 5000 });

    // Assert Execution Plan card is visible
    const planPanel = page.locator("#release-execution-plan-panel");
    await expect(planPanel).toBeVisible();

    const generateBtn = page.locator("#btn-generate-execution-plan");
    await expect(generateBtn).toBeEnabled();

    // 5. Generate plan (initial - authority absent)
    await generateBtn.click();

    const planDetails = page.locator("#execution-plan-details");
    await expect(planDetails).toBeVisible();

    const stepsTable = page.locator("#execution-plan-steps-tbody");
    await expect(stepsTable).toContainText("Verify Release Readiness and Compliance");
    await expect(stepsTable).toContainText("Mutate Git Tags (Release Tagging)");

    // Step 2 (git tagging) should display MISSING because authority is absent
    const step2Row = stepsTable.locator("tr").nth(1);
    await expect(step2Row.locator("td").nth(1)).toContainText("Mutate Git Tags");
    await expect(step2Row.locator("td").nth(4)).toContainText("MISSING");

    // 6. Request Release Authority Token
    page.on("dialog", async dialog => {
      console.log(`[E2E Dialog] ${dialog.message()}`);
      await dialog.accept();
    });

    const requestAuthBtn = page.locator("#btn-request-authority");
    await requestAuthBtn.click();

    const confirmChk = page.locator("#chk-confirm-authority-scope");
    await confirmChk.check();
    
    const grantBtn = page.locator("#btn-modal-grant-authority");
    await grantBtn.click();

    // Confirm authority is active
    const authStatus = page.locator("#gov-authority-status");
    await expect(authStatus).toContainText("GRANTED");

    // 7. Re-generate plan (authority satisfied)
    await generateBtn.click();

    // Step 2 should now display SATISFIED
    await expect(step2Row.locator("td").nth(4)).toContainText("SATISFIED");

    // 8. Test exports
    const exportMdBtn = page.locator("#btn-export-plan-markdown");
    const downloadMdPromise = page.waitForEvent("download");
    await exportMdBtn.click();
    const downloadMd = await downloadMdPromise;
    expect(downloadMd.suggestedFilename()).toBe(`formal-release-execution-plan-${cleanPacketId}.md`);
    const mdPath = await downloadMd.path();
    expect(mdPath).not.toBeNull();
    const mdContent = fs.readFileSync(mdPath!, "utf8");
    expect(mdContent).toContain("Authority Status**: GRANTED");

    const exportJsonBtn = page.locator("#btn-export-plan-json");
    const downloadJsonPromise = page.waitForEvent("download");
    await exportJsonBtn.click();
    const downloadJson = await downloadJsonPromise;
    expect(downloadJson.suggestedFilename()).toBe(`formal-release-execution-plan-${cleanPacketId}.json`);
    const jsonPath = await downloadJson.path();
    expect(jsonPath).not.toBeNull();
    const jsonContent = fs.readFileSync(jsonPath!, "utf8");
    const planObj = JSON.parse(jsonContent);
    expect(planObj.status).toBe("success");
    expect(planObj.authority_status).toBe("granted");

    // 9. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/release-execution-plan.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E execution plan screenshot at: ${screenshotPath}`);
  });
});
