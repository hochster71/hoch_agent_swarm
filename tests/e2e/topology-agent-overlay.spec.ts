import { test, expect } from "@playwright/test";

test.describe("Topology Agent Overlay & Roster Runtime", () => {
  test("interacts with agents and runs the swarm animation successfully", async ({ page }, testInfo) => {
    page.on("console", msg => console.log(`BROWSER CONSOLE: ${msg.text()}`));
    page.on("pageerror", err => console.error(`BROWSER ERROR: ${err.message}`));

    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Check prompt bar and Gordon Vector chip are visible
    const launchBtn = page.locator("#topology-agent-launch-button");
    await expect(launchBtn).toBeVisible();
    await expect(page.locator("text=Launch Expert Swarm").first()).toBeVisible();

    const gordonChip = page.locator("#topo-chip-gordon-vector");
    await expect(gordonChip).toBeVisible();

    // 2. Click Gordon Vector to open modal
    await gordonChip.click();
    
    const modal = page.locator("#topology-agent-profile-modal");
    await expect(modal).toBeVisible();
    await expect(page.locator("#topology-agent-modal-tag")).toHaveText("CONTAINER WHISPERER");
    await expect(page.locator("#topology-agent-modal-catchphrase")).toHaveText("“The container will tell us what hurts.”");

    // 3. Click Spin Up Agent
    await page.click("#topology-agent-modal-spinup");
    
    // Expect chip or LED complete
    await expect(gordonChip).toHaveClass(/is-complete/);

    // 4. Close modal
    await page.click("#topology-agent-modal-close");
    await expect(modal).not.toBeVisible();

    // 5. Fill input and click Launch Swarm
    await page.fill("#topology-agent-prompt-input", "Research YouTube Docker debugging videos and verify release readiness.");
    await launchBtn.click();

    // 6. Wait for Complete stage green (is-complete)
    // The animation takes about 10.5 seconds, so we wait up to 15 seconds
    const completeStage = page.locator('.topology-stage-step[data-stage="Complete"]');
    await expect(completeStage).toHaveClass(/is-complete/, { timeout: 15000 });

    // Expect "Green means verified" is visible
    await expect(page.locator("text=Green means verified")).toBeVisible();

    // Expect at least one agent chip has is-complete class
    const bossChip = page.locator("#topo-chip-boss-noodle");
    await expect(bossChip).toHaveClass(/is-complete/);

    // 7. Save screenshot
    await page.screenshot({
      path: "artifacts/qa/topology-agent-overlay-runtime.png",
      fullPage: false
    });

    await testInfo.attach("topology-agent-overlay-runtime", {
      path: "artifacts/qa/topology-agent-overlay-runtime.png",
      contentType: "image/png"
    });
  });
});
