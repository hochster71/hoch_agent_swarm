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

test.describe("RACI Governance E2E Spec", () => {
  test("verifies /api/raci endpoint, RACI tab rendering, Gap Analysis violations, and Landscape RACI cards", async ({ page }) => {
    // Navigate to dashboard root
    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Switch to Landscape tab and verify RACI cards
    const landscapeTabBtn = page.locator("#tab-landscape");
    await expect(landscapeTabBtn).toBeVisible();
    await landscapeTabBtn.click();
    await page.waitForTimeout(500);

    const raciStrip = page.locator("#landscapeRaci");
    await expect(raciStrip).toBeVisible();
    
    const coverageCard = raciStrip.locator("text=RACI Governance Coverage");
    await expect(coverageCard).toBeVisible();

    // 2. Switch to Gap Analysis tab and verify RACI gaps are populated
    const gapsTabBtn = page.locator("#tab-gaps");
    await expect(gapsTabBtn).toBeVisible();
    await gapsTabBtn.click();
    await page.waitForTimeout(500);

    // Verify RACI gap exists in Gap Analysis rows
    const raciGap = page.locator("text=RACI: ");
    await expect(raciGap.first()).toBeVisible();

    // 3. Switch to RACI Governance tab and check chart contents
    const raciTabBtn = page.locator("#tab-raci");
    await expect(raciTabBtn).toBeVisible();
    await raciTabBtn.click();
    await page.waitForTimeout(500);

    // Verify RACI summary and matrix sections
    const coverageHeader = page.locator("#view-raci").locator("text=Governance Coverage");
    await expect(coverageHeader).toBeVisible();

    const matrixHeader = page.locator("text=RACI Responsibility Assignment Matrix");
    await expect(matrixHeader).toBeVisible();

    // Hover matrix row to trigger tooltip
    const heatmapRow = page.locator("#raciHeatmapRows").locator("text=Live Tracker Runtime Agent").first();
    await expect(heatmapRow).toBeVisible();
    await heatmapRow.hover();
    await page.waitForTimeout(200);

    // Click row to verify drawer details open
    await heatmapRow.click();
    await page.waitForTimeout(200);
    const drawer = page.locator("#drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText("Load Detail");

    // Close the drawer
    await page.keyboard.press("Escape");
    await page.waitForTimeout(200);
    await expect(drawer).not.toBeVisible();
  });
});
