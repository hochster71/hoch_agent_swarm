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

test.describe("HOCH PODS Theater Movie Clip E2E Spec", () => {
  test("renders theater, stage, timeline, and verifies clicking clips opens detail drawers", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Verify theater wrapper
    const theater = page.locator(".hoch-pods-theater");
    await expect(theater).toBeVisible();

    // 2. Verify stage
    const stage = page.locator("#topologyContainer");
    await expect(stage).toBeVisible();

    // 3. Verify timeline
    const timeline = page.locator("#movieTimeline");
    await expect(timeline).toBeVisible();

    // 4. Verify that we have 17 clips in the timeline
    const clips = page.locator(".movie-clip");
    await expect(clips).toHaveCount(17);

    // 5. Click the first clip to open the detail drawer
    const firstClip = page.locator("#clip-pod-system-boot");
    await expect(firstClip).toBeVisible();
    await firstClip.click();

    // 6. Verify that the drawer opens and displays telemetry metadata details
    const drawer = page.locator("#drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText("System Boot");
    await expect(drawer).toContainText("Trigger & Metadata");
    await expect(drawer).toContainText("Telemetry Data Validation");
    await expect(drawer).toContainText("Next Recommended Action");

    // Close the drawer
    const closeBtn = page.locator("#drawer button >> text=Close");
    await closeBtn.click();
    await expect(drawer).not.toBeVisible();
  });
});
