import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

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

test.describe("Control Plane Header Status Badges", () => {
  test("verifies all 10 required header fields exist and display non-empty values", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    // Assert exist and are visible
    const badgeIds = [
      "top-system-status",
      "top-truth-source",
      "top-has-api-status",
      "top-tracker-status",
      "top-raci-coverage",
      "top-qa-gate",
      "top-registry-count",
      "top-open-gaps",
      "top-live-events",
      "top-sidecar-status"
    ];

    for (const badgeId of badgeIds) {
      const badge = page.locator(`#${badgeId}`);
      await expect(badge).toBeVisible();
      
      const valText = badge.locator(".val");
      // Check that the value container exists and is populated
      if (await valText.count() > 0) {
        await expect(valText).not.toBeEmpty();
        await expect(valText).not.toContainText("-");
      } else {
        await expect(badge).not.toBeEmpty();
      }
    }
  });
});
