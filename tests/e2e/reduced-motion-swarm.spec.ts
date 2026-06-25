import { test, expect } from "@playwright/test";

test.describe("Reduced Motion E2E", () => {
  test("loads the page with emulated reduced motion, runs the swarm, and takes a screenshot", async ({ page }, testInfo) => {
    const consoleErrors: string[] = [];
    page.on("console", msg => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });
    page.on("pageerror", err => consoleErrors.push(err.message));

    // 1. Emulate prefers-reduced-motion: reduce
    await page.emulateMedia({ reducedMotion: "reduce" });

    // 2. Load page
    await page.goto("/", { waitUntil: "networkidle" });

    // 3. Launch topology swarm
    const launchBtn = page.locator("#topology-agent-launch-button");
    await expect(launchBtn).toBeVisible();

    await page.fill("#topology-agent-prompt-input", "Verify release readiness with zero motion.");
    await launchBtn.click();

    // 4. Verify no console errors
    expect(consoleErrors).toEqual([]);

    // 5. Verify LEDs/stages still update
    const completeStage = page.locator('.topology-stage-step[data-stage="Complete"]');
    await expect(completeStage).toHaveClass(/is-complete/, { timeout: 15000 });

    // 6. Save screenshot to artifacts/qa/reduced-motion-swarm.png
    await page.screenshot({
      path: "artifacts/qa/reduced-motion-swarm.png",
      fullPage: false
    });

    await testInfo.attach("reduced-motion-swarm", {
      path: "artifacts/qa/reduced-motion-swarm.png",
      contentType: "image/png"
    });
  });
});
