import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

test.describe("@legacy @compat @deorbited Cross-Runtime Evidence Graph E2E", () => {
  test("triggers evidence trace, inspects node details, and persists a manual relationship", async ({ page }) => {
    // Dismiss all alert/confirm dialogs automatically
    page.on("dialog", async dialog => {
      console.log(`Dialog opened: [${dialog.type()}] ${dialog.message()}`);
      await dialog.accept();
    });

    const consoleErrors: string[] = [];
    page.on("console", msg => {
      console.log(`[BROWSER CONSOLE ${msg.type().toUpperCase()}]: ${msg.text()}`);
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

    // 3. Verify Evidence Graph panel is visible
    const graphPanel = page.locator("#evidence-chain-view-panel");
    await expect(graphPanel).toBeVisible({ timeout: 10000 });

    // 4. Click the Refresh Graph button
    const refreshBtn = page.locator("#btn-refresh-evidence-graph");
    await expect(refreshBtn).toBeVisible();
    const refreshPromise = page.waitForResponse(response => 
      response.url().includes("/api/v1/evidence/graph") && response.status() === 200
    );
    await refreshBtn.click();
    await refreshPromise;
    await page.waitForTimeout(200);

    // 5. Select a candidate in the Release Candidate filter
    const releaseFilter = page.locator("#evidence-graph-release-filter");
    await expect(releaseFilter).toBeVisible();

    await page.waitForFunction(() => {
      const select = document.getElementById("evidence-graph-release-filter") as HTMLSelectElement;
      return select && select.options.length > 1;
    }, { timeout: 10000 });

    const optionValue = await page.evaluate(() => {
      const select = document.getElementById("evidence-graph-release-filter") as HTMLSelectElement;
      return select.options[1].value;
    });

    console.log(`Selected Release Candidate filter value: ${optionValue}`);
    const tracePromise = page.waitForResponse(response => 
      response.url().includes("/api/v1/evidence/graph/trace/") && response.status() === 200
    );
    await releaseFilter.selectOption(optionValue);
    await tracePromise;
    await page.waitForTimeout(500);

    // 6. Assert flow-chips are rendered in flow container
    const flowContainer = page.locator("#evidence-flow-container");
    await expect(flowContainer.locator(".evidence-node-chip").first()).toBeVisible();

    // Verify export button is visible and trigger download
    const exportBtn = page.locator("#btn-export-evidence-summary");
    await expect(exportBtn).toBeVisible();
    
    console.log("Triggering client-side evidence summary download...");
    const downloadPromise = page.waitForEvent("download");
    await exportBtn.click();
    const download = await downloadPromise;
    console.log(`Downloaded evidence summary: ${download.suggestedFilename()}`);

    // Verify stats counters (Phase 21)
    const nodeCountEl = page.locator("#evidence-graph-node-count");
    const edgeCountEl = page.locator("#evidence-graph-edge-count");
    const hiddenCountEl = page.locator("#evidence-graph-hidden-count");
    await expect(nodeCountEl).not.toBeEmpty();
    await expect(edgeCountEl).not.toBeEmpty();
    await expect(hiddenCountEl).not.toBeEmpty();

    const initialHiddenText = await hiddenCountEl.textContent();
    const initialHidden = parseInt(initialHiddenText || "0", 10);
    console.log(`Initial hidden count: ${initialHidden}`);

    // If there are hidden nodes, verify Load More works
    if (initialHidden > 0) {
      const loadMoreBtn = page.locator("#evidence-graph-load-more-button");
      const warningEl = page.locator("#evidence-graph-large-warning");
      await expect(loadMoreBtn).toBeVisible();
      await expect(warningEl).toBeVisible();

      // Click Load More
      await loadMoreBtn.click();
      await page.waitForTimeout(500);

      // Verify hidden count decreased
      const newHiddenText = await hiddenCountEl.textContent();
      const newHidden = parseInt(newHiddenText || "0", 10);
      console.log(`New hidden count after load more: ${newHidden}`);
      expect(newHidden).toBeLessThan(initialHidden);
    }

    // 7. Click a flow chip to activate Inspector
    const firstChip = flowContainer.locator(".evidence-node-chip").first();
    await firstChip.click();
    await page.waitForTimeout(300);

    // Verify Inspector details content is visible
    const inspectorContent = page.locator("#evidence-node-inspector-content");
    await expect(inspectorContent).toBeVisible();
    await expect(page.locator("#inspector-node-id")).not.toBeEmpty();

    // 8. Test explicit manual relationship linkage
    const sourceSelect = page.locator("#link-source-select");
    const targetSelect = page.locator("#link-target-select");
    const relationSelect = page.locator("#link-relation-select");
    const saveLinkBtn = page.locator("#btn-save-manual-link");

    await expect(sourceSelect).toBeVisible();
    await expect(targetSelect).toBeVisible();
    await expect(saveLinkBtn).toBeVisible();

    // Populate selects with mock or real items
    const sourceVal = await page.evaluate(() => {
      const select = document.getElementById("link-source-select") as HTMLSelectElement;
      return select.options.length > 1 ? select.options[1].value : "";
    });
    const targetVal = await page.evaluate(() => {
      const select = document.getElementById("link-target-select") as HTMLSelectElement;
      // Use last option to avoid duplicate self-loops
      return select.options.length > 2 ? select.options[select.options.length - 1].value : "";
    });

    if (sourceVal && targetVal && sourceVal !== targetVal) {
      console.log(`Creating manual link from ${sourceVal} to ${targetVal}`);
      await sourceSelect.selectOption(sourceVal);
      await targetSelect.selectOption(targetVal);
      await relationSelect.selectOption("associated_with");
      
      // Save link
      const linkPromise = page.waitForResponse(response => 
        response.url().includes("/api/v1/evidence/graph/link") && response.status() === 200
      );
      await saveLinkBtn.click();
      await linkPromise;

      // Verify that after saving, no browser console errors occurred
      expect(consoleErrors).toEqual([]);
    }

    // 9. Capture screenshot evidence
    const screenshotPath = "artifacts/qa/evidence-graph.png";
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    console.log(`Captured E2E Evidence Graph screenshot at: ${screenshotPath}`);
  });
});
