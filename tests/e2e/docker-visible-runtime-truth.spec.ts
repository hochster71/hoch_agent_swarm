import { test, expect } from "@playwright/test";

test.describe("Docker-First Visible Runtime Truth Verification", () => {
  test("asserts that UI elements match Final Verifier blocked state, hiding stale telemetry", async ({ page }) => {
    // 1. Go to root page
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Verify sub-header indicators
    const badge = page.locator("#final-verifier-badge");
    await expect(badge).toBeVisible();
    
    const countEl = page.locator("#final-contradictions-count");
    await expect(countEl).toBeVisible();

    const scoreEl = page.locator("#final-readiness-capped");
    await expect(scoreEl).toBeVisible();

    // 3. Verify topbar is synchronized with verifier block
    const rCount = page.locator("#topbar-readiness");
    await expect(rCount).toBeVisible();
    // In BLOCKED state, it should be capped at 50%
    await expect(rCount).toHaveText("50%");

    const gNogo = page.locator("#topbar-gonogo");
    await expect(gNogo).toBeVisible();
    await expect(gNogo).toHaveText("NO-GO BLOCKED");

    // 4. Verify No-Drift Gate card is synchronized with verifier block
    const prodStatus = page.locator("#nodrift-prod-status");
    await expect(prodStatus).toBeVisible();
    await expect(prodStatus).toHaveText("BLOCKED");

    // 5. Verify deorbited elements are hidden
    const deorbitedContainer = page.locator("#deorbited-operator-governance-cockpit");
    await expect(deorbitedContainer).not.toBeVisible();
  });
});
