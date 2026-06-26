import { test, expect } from "@playwright/test";

test.describe("Global Swarm Process Animation Runtime", () => {
  test.skip("runs the swarm animation flow and completes successfully", async ({ page }, testInfo) => {
    page.on("console", msg => console.log(`BROWSER CONSOLE: ${msg.text()}`));
    page.on("pageerror", err => console.error(`BROWSER ERROR: ${err.message}`));

    await page.goto("/", { waitUntil: "networkidle" });

    const globalSwarmRuntime = page.locator("#hoch-global-swarm-runtime");
    await expect(globalSwarmRuntime).toBeVisible();

    const statusBadge = page.locator("#hoch-global-swarm-status");
    await expect(statusBadge).toHaveText("STANDBY");

    // Click launch button with default prompt
    await page.fill("#hoch-process-prompt-input", "Research YouTube videos on Docker container debugging, summarize repair patterns, and assign agents to harden Hoch Agent Swarm.");
    await page.click("#hoch-process-launch-button");

    // Wait for the status badge to transit through executing states and eventually to COMPLETED
    await expect(statusBadge).toHaveText("COMPLETED", { timeout: 12000 });

    // Assert that active agents like Boss Noodle, Gordon Vector, Ms. Checkmark, etc. are complete
    const dockCard = page.locator("#dock-card-boss-noodle");
    await expect(dockCard).toBeVisible();
    await expect(dockCard).toContainText("complete");

    // Verify evidence lights got locked (at least one is locked)
    const evidenceLight = page.locator("#hoch-global-evidence-lights .evidence-light").first();
    await expect(evidenceLight).toHaveClass(/locked/);

    // Save screenshot
    await page.screenshot({
      path: "artifacts/qa/global-swarm-animation-runtime.png",
      fullPage: false
    });

    await testInfo.attach("global-swarm-animation-runtime", {
      path: "artifacts/qa/global-swarm-animation-runtime.png",
      contentType: "image/png"
    });
  });
});
