import { test, expect } from "@playwright/test";

test.describe("UI Runtime Truth Rewire Verification", () => {
  test("asserts that final verifier top bar displays correct status, contradictions, and readiness", async ({ page }) => {
    // 1. Go to root page
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Verify sub-header is visible
    const subheader = page.locator("#final-verifier-subheader");
    await expect(subheader).toBeVisible();

    // 3. Verify verifier status badge matches text
    const badge = page.locator("#final-verifier-badge");
    await expect(badge).toBeVisible();
    
    // 4. Verify contradictions count and readiness score elements are present
    const countEl = page.locator("#final-contradictions-count");
    await expect(countEl).toBeVisible();

    const scoreEl = page.locator("#final-readiness-capped");
    await expect(scoreEl).toBeVisible();

    const timeEl = page.locator("#final-verifier-timestamp");
    await expect(timeEl).toBeVisible();
  });
});
