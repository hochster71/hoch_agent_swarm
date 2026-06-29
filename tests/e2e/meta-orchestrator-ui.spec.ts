import { test, expect } from "@playwright/test";

test.describe("Meta-Orchestrator UI and Telemetry Verification", () => {
  test("asserts that Meta-Orchestrator panel displays correct telemetry, badges, and caps", async ({ page }) => {
    // 1. Go to root page
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Select and click Meta-Orchestrator navigation button
    const metaNavBtn = page.locator("#nav-meta-orchestrator");
    await expect(metaNavBtn).toBeVisible();
    await metaNavBtn.click();

    // 3. Verify target view-meta-orchestrator is visible
    const metaView = page.locator("#view-meta-orchestrator");
    await expect(metaView).toBeVisible();
    await expect(metaView).not.toHaveClass(/\bhidden\b/);

    // 4. Assert DOM elements exist
    await expect(page.locator("#meta-total-domains")).toBeVisible();
    await expect(page.locator("#meta-ownerless-domains")).toBeVisible();
    await expect(page.locator("#meta-critical-gaps")).toBeVisible();
    await expect(page.locator("#meta-load-score")).toBeVisible();

    // 5. Verify values mapped from Runtime Truth API
    const totalVal = await page.locator("#meta-total-domains").textContent();
    const ownerlessVal = await page.locator("#meta-ownerless-domains").textContent();
    const criticalVal = await page.locator("#meta-critical-gaps").textContent();
    const loadScore = await page.locator("#meta-load-score").textContent();

    expect(parseInt(totalVal || "0")).toBe(43);
    expect(parseInt(ownerlessVal || "0")).toBe(0);
    expect(parseInt(criticalVal || "0")).toBe(0);
    expect(loadScore).toBe("20.0");

    // 6. Verify evidence links exist
    await expect(page.locator("#meta-evidence-matrix")).toBeVisible();
    await expect(page.locator("#meta-evidence-gaps")).toBeVisible();
    await expect(page.locator("#meta-evidence-brief")).toBeVisible();
  });
});
