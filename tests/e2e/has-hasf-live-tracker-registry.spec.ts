import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// Load secrets from ~/.hoch-secrets/has-tracker.env if it exists
const secretsPath = path.join(process.env.HOME || "", ".hoch-secrets", "has-tracker.env");
let username = "admin";
let password = "change-this-password";
let port = "3001";

if (fs.existsSync(secretsPath)) {
  const content = fs.readFileSync(secretsPath, "utf8");
  content.split(/\r?\n/).forEach(line => {
    const idx = line.indexOf("=");
    if (idx !== -1) {
      const key = line.slice(0, idx).trim();
      const val = line.slice(idx + 1).trim();
      if (key === "TRACKER_USER") username = val;
      if (key === "TRACKER_PASSWORD") password = val;
      if (key === "TRACKER_PORT") port = val;
    }
  });
}

test.use({
  baseURL: `http://localhost:${port}`,
  httpCredentials: {
    username,
    password
  }
});

test.describe("Global Project Registry E2E Verification Spec", () => {
  test("verifies /api/registry, /api/dedupe, canonical records rendering, duplicate groups, monetization candidates, devsecops targets, tooltips, and drawers", async ({ page }) => {
    // Navigate directly to local tracker root
    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Verify API endpoints
    const registryRes = await page.request.get("/api/registry");
    expect(registryRes.status()).toBe(200);
    const registryData = await registryRes.json();
    expect(registryData.length).toBeGreaterThan(0);

    const dedupeRes = await page.request.get("/api/dedupe");
    expect(dedupeRes.status()).toBe(200);
    const dedupeData = await dedupeRes.json();
    expect(dedupeData.length).toBeGreaterThan(0);

    // 2. Switch to Global Registry Tab
    const registryTabBtn = page.locator("#tab-registry");
    await expect(registryTabBtn).toBeVisible();
    await registryTabBtn.click();
    await page.waitForTimeout(500);

    // 3. Verify statistics
    const regCanonicalCount = page.locator("#regCanonicalCount");
    await expect(regCanonicalCount).not.toHaveText("-");
    const regMonetizationCount = page.locator("#regMonetizationCount");
    await expect(regMonetizationCount).not.toHaveText("-");
    const regDevSecOpsCount = page.locator("#regDevSecOpsCount");
    await expect(regDevSecOpsCount).not.toHaveText("-");

    // 4. Verify canonical project rows are populated
    const firstCanonicalRow = page.locator(".registry-canonical-name-cell").first();
    await expect(firstCanonicalRow).toBeVisible();

    // 5. Verify Tooltip triggers on hover
    await firstCanonicalRow.hover();
    await page.waitForTimeout(200);
    const tooltip = page.locator("#tooltip");
    await expect(tooltip).toBeVisible();
    await page.keyboard.press("Escape");
    await page.mouse.move(0, 0);
    await page.waitForTimeout(200);
    await expect(tooltip).not.toBeVisible();

    // 6. Verify detail Drawer opens on click
    await firstCanonicalRow.click();
    await page.waitForTimeout(200);
    const drawer = page.locator("#drawer");
    await expect(drawer).toBeVisible();

    // Close the drawer using Escape key
    await page.keyboard.press("Escape");
    await page.waitForTimeout(200);
    await expect(drawer).not.toBeVisible();

    // 7. Verify duplicate groups, monetization candidates, and DevSecOps scan targets render
    const firstDedupeRow = page.locator(".registry-dedupe-name-cell").first();
    await expect(firstDedupeRow).toBeVisible();

    const firstDevSecOpsRow = page.locator(".registry-devsecops-name-cell").first();
    await expect(firstDevSecOpsRow).toBeVisible();
  });
});
