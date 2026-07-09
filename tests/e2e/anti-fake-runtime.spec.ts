import { test, expect } from "@playwright/test";

test.describe("Anti-Fake Runtime Check Gate", () => {
  test("asserts that UI elements map to verified runtime truth and blocks overrides", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("load");

    // 1. Verify that no fake green state overrides are active
    const errorWarning = page.locator(".no-go-warning");
    const goState = page.locator(".go-state");
    if (await errorWarning.isVisible() && await goState.isVisible()) {
      throw new Error("FAIL: Contradiction detected: GO and NO-GO status co-exist.");
    }

    // 2. Ensure hidden compatibility wrappers do not satisfy active/live selectors
    const compatWrapper = page.locator("#deorbited-compatibility-wrapper");
    if (await compatWrapper.isVisible()) {
      const displayStyle = await compatWrapper.evaluate(el => window.getComputedStyle(el).display);
      const visibilityStyle = await compatWrapper.evaluate(el => window.getComputedStyle(el).visibility);
      const opacityStyle = await compatWrapper.evaluate(el => window.getComputedStyle(el).opacity);
      
      // If it is positioned visible on-screen, it's not compat-only
      const boundingBox = await compatWrapper.boundingBox();
      if (boundingBox && boundingBox.x >= 0 && boundingBox.y >= 0 && opacityStyle === "1") {
        throw new Error("FAIL: Hidden compatibility wrapper is exposed as a live visual panel.");
      }
    }
    
    // 3. Confirm that no dynamic status displays fake done indicators
    const readinessScoreText = await page.locator("#led-readiness").evaluate(el => el.textContent);
    if (readinessScoreText === "100%") {
      // Must check if dirty tree or lack of evidence caps it
      const gitDirty = await page.evaluate(() => localStorage.getItem("git_dirty"));
      if (gitDirty === "true") {
        throw new Error("FAIL: Overall readiness is falsely reported as 100% despite dirty workspace.");
      }
    }
  });
});
