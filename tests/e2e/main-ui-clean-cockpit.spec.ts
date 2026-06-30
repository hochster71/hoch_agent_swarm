import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("Operator Cockpit and Sidebar Cleanup E2E Spec", () => {
  test("verifies the clean operator cockpit UI, collapsible sidebar groups, and tab switching", async ({ page }) => {
    // Navigate to dashboard root
    await page.goto("/", { waitUntil: "networkidle" });

    // Assert that body is visible and title matches
    await expect(page.locator("body")).toBeVisible();
    await expect(page).toHaveTitle(/Hoch Agent Swarm/);

    // 1. Verify that the Sidebar Accordion groups exist
    const accordionSummaries = [
      "Core Operations",
      "Registry & Portals",
      "Cyber & Governance",
      "Runtime & Release"
    ];

    for (const groupName of accordionSummaries) {
      const summary = page.locator(`summary:has-text("${groupName}")`);
      await expect(summary).toBeVisible();
    }

    // 2. Verify the 10 Operator Cockpit information items are visible in the default view
    const cockpitElements = [
      "op-verifier-status",
      "op-readiness-val",
      "op-verifier-blockers",
      "op-truth-status",
      "gate-dock-val",
      "gate-k8s-val",
      "gate-fake-val",
      "gate-host-val",
      "op-mission-title",
      "op-mission-desc",
      "op-next-safe-action",
      "op-worker-name",
      "op-worker-host",
      "op-worker-status",
      "op-worker-routing",
      "op-evidence-filename",
      "op-evidence-status",
      "op-approval-badge",
      "op-approval-queue-list"
    ];

    for (const elId of cockpitElements) {
      const element = page.locator(`#${elId}`);
      await expect(element).toBeVisible();
    }

    // 3. Test Tab Switching
    const btnCockpit = page.locator("#btn-tab-cockpit");
    const btnLegacy = page.locator("#btn-tab-legacy");
    const containerCockpit = page.locator("#container-operator-cockpit");
    const containerLegacy = page.locator("#container-legacy-telemetry");

    await expect(btnCockpit).toBeVisible();
    await expect(btnLegacy).toBeVisible();

    // Default state: Cockpit is visible, Legacy is hidden
    await expect(containerCockpit).toBeVisible();
    await expect(containerLegacy).toHaveClass(/\bhidden\b/);

    // Click Legacy Tab
    await btnLegacy.click();
    await expect(containerLegacy).toBeVisible();
    await expect(containerCockpit).toHaveClass(/\bhidden\b/);

    // Click Cockpit Tab back
    await btnCockpit.click();
    await expect(containerCockpit).toBeVisible();
    await expect(containerLegacy).toHaveClass(/\bhidden\b/);

    // Save screenshot of the new clean cockpit design
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/clean-operator-cockpit.png");
    const outputDir = path.dirname(screenshotPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath, fullPage: false });
  });
});
