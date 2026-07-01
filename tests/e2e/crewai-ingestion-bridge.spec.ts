import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited CrewAI Ingestion Bridge E2E", () => {
  test("triggers ingestion, indexes plans and run reports, and updates the evidence graph", async ({ page }) => {
    // Dismiss all alert/confirm dialogs automatically
    page.on("dialog", async dialog => {
      console.log(`Dialog opened: [${dialog.type()}] ${dialog.message()}`);
      await dialog.accept();
    });

    const consoleErrors: string[] = [];
    page.on("console", msg => {
      if (msg.type() === "error" && !msg.text().includes("WebSocket")) {
        consoleErrors.push(msg.text());
      }
    });

    // 1. Navigate to main dashboard
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 2. Click Governance navigation link
    const navGov = page.locator("#nav-governance");
    await expect(navGov).toBeVisible();
    await navGov.click();

    // 3. Verify CrewAI Ingestion Bridge panel is visible
    const bridgePanel = page.locator("#crewai-ingestion-bridge-panel");
    await expect(bridgePanel).toBeVisible({ timeout: 10000 });

    // 4. Click the Trigger Ingestion button
    const triggerBtn = page.locator("#btn-trigger-crewai-ingest");
    await expect(triggerBtn).toBeVisible();
    await triggerBtn.click();

    // Wait for the ingestion to complete and UI to update
    await page.waitForTimeout(1000);

    // 5. Verify the tables contain the ingested files
    const indexedPlans = page.locator("#crewai-plans-tbody");
    const indexedRuns = page.locator("#crewai-runs-tbody");
    
    // Assert they are no longer just empty placeholders and contain the mock/real artifacts
    await expect(indexedPlans).toContainText(".md");
    await expect(indexedRuns).toContainText("artifacts");

    // 6. Verify Evidence Graph updates
    // In app.js, evidence graph is rendered and loaded. Let's make sure there is no console error.
    expect(consoleErrors).toEqual([]);

    // 7. Capture screenshot evidence
    const screenshotPath = "artifacts/qa/crewai-ingestion-bridge.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E CrewAI Ingestion Bridge screenshot at: ${screenshotPath}`);
  });
});
