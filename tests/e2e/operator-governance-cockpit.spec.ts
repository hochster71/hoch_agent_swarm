import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("Operator Governance Command Center E2E", () => {
  test("navigates to Governance Cockpit and asserts all core panels are visible", async ({ page, request }) => {
    // 1. Assert backend governance summary API endpoint directly
    const apiResponse = await request.get("/api/v1/governance/summary");
    expect(apiResponse.ok()).toBeTruthy();
    const data = await apiResponse.json();
    
    expect(data.pending_gates).toBeDefined();
    expect(data.capability_decisions).toBeDefined();
    expect(data.formal_release_blockers).toBeDefined();
    expect(data.decision_ledger).toBeDefined();
    expect(data.replay_protection_evidence).toBeDefined();

    // 2. Go to the dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 3. Click the Governance Cockpit nav item
    const navItem = page.locator("#nav-governance");
    await expect(navItem).toBeVisible();
    await navItem.click();

    // 4. Expect cockpit view and elements to be visible
    const view = page.locator("#view-governance");
    await expect(view).toBeVisible();

    await expect(page.locator("h2:has-text('Operator Governance Command Center')")).toBeVisible();
    await expect(page.locator("h3:has-text('PENDING APPROVAL GATES')")).toBeVisible();
    await expect(page.locator("h3:has-text('FORMAL RELEASE BLOCKERS')")).toBeVisible();
    await expect(page.locator("h3:has-text('ACTIVE POLICIES & WAIVERS')")).toBeVisible();
    await expect(page.locator("h3:has-text('CAPABILITY ENFORCEMENT DECISIONS')")).toBeVisible();
    await expect(page.locator("h3:has-text('REPLAY-PROTECTION INTEGRITY EVIDENCE')")).toBeVisible();
    await expect(page.locator("h3:has-text('HISTORICAL OPERATOR DECISION LEDGER')")).toBeVisible();

    // CrewAI Ingestion Bridge Assertions
    const bridgePanel = page.locator("#crewai-ingestion-bridge-panel");
    await expect(bridgePanel).toBeVisible();
    await expect(bridgePanel.locator("h3:has-text('CREWAI EXECUTION ARTIFACT INGESTION BRIDGE')")).toBeVisible();
    
    const ingestBtn = bridgePanel.locator("#btn-trigger-crewai-ingest");
    await expect(ingestBtn).toBeVisible();
    
    // Trigger ingestion scan
    await ingestBtn.click();
    
    // Wait for the ingestion message to show success
    const statusMsg = bridgePanel.locator("#crewai-ingest-status-msg");
    await expect(statusMsg).toBeVisible();
    await expect(statusMsg).toContainText("Ingestion complete");

    // 5. Capture screenshot
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/operator-governance-cockpit.png");
    const screenshotDir = path.dirname(screenshotPath);
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured screenshot at: ${screenshotPath}`);
  });
});
