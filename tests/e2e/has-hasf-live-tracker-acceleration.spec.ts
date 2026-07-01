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

test.describe("Production Acceleration E2E Spec", () => {
  test("verifies /api/acceleration endpoint and Landscape Acceleration strip rendering", async ({ page }) => {
    // Navigate to dashboard root
    await page.goto("/", { waitUntil: "networkidle" });
    
    // Switch to Landscape Map tab
    const landscapeTabBtn = page.locator("#tab-landscape");
    await expect(landscapeTabBtn).toBeVisible();
    await landscapeTabBtn.click();
    await page.waitForTimeout(500);

    // Assert that the Moonshot Acceleration strip is visible
    const accStrip = page.locator("#landscapeAcceleration");
    await expect(accStrip).toBeVisible();

    // Verify presence of cards in the acceleration strip
    const verdictCard = accStrip.locator("text=Production Verdict");
    await expect(verdictCard).toBeVisible();

    const remainingHoursCard = accStrip.locator("text=Remaining Swarm Hours");
    await expect(remainingHoursCard).toBeVisible();

    const hoursSavedCard = accStrip.locator("text=Est. Swarm Hours Saved");
    await expect(hoursSavedCard).toBeVisible();

    const parallelBatchCard = accStrip.locator("text=Safe Parallel Swarm Batch");
    await expect(parallelBatchCard).toBeVisible();

    const staleRescueCard = accStrip.locator("text=Stale Task Rescue List");
    await expect(staleRescueCard).toBeVisible();

    const actionsCard = accStrip.locator("text=Next 3 Highest-Impact Actions");
    await expect(actionsCard).toBeVisible();

    // Hover a card to check tooltip binding
    await remainingHoursCard.hover();
    await page.waitForTimeout(200);

    // Click a card to verify drawer opens with detail content
    await remainingHoursCard.click();
    await page.waitForTimeout(200);
    const drawer = page.locator("#drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText("Remaining Swarm Hours");

    // Close the drawer
    await page.keyboard.press("Escape");
    await page.waitForTimeout(200);
    await expect(drawer).not.toBeVisible();
  });
});
