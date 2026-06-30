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

test.describe("Control Plane v2 Live Tracker Mirror verification", () => {
  test("verifies mirror iframe page, same-origin health, and legacy direct access usability", async ({ page }) => {
    // 1. Verify mirror-health route
    const healthRes = await page.request.get("/api/mirror-health");
    expect(healthRes.ok()).toBeTruthy();
    const health = await healthRes.json();
    expect(health.status).toBe("OK");
    expect(health.mirror).toBe("authenticated_same_origin");

    // 2. Load Control Plane main page
    await page.goto("/", { waitUntil: "networkidle" });

    // 3. Switch to mirror tab via sidebar
    const mirrorNav = page.locator("aside >> text=Live Tracker Mirror");
    await expect(mirrorNav).toBeVisible();
    await mirrorNav.click();
    await page.waitForTimeout(500);

    // 4. Verify iframe loads legacy view
    const iframe = page.frameLocator("#liveTrackerMirror");
    // The legacy view has tab-dashboard button or specific headers
    await expect(iframe.locator("#tab-dashboard")).toBeVisible();

    // 5. Verify direct legacy view /tracker-mirror path is usable as-is
    await page.goto("/tracker-mirror", { waitUntil: "networkidle" });
    await expect(page.locator("#tab-dashboard")).toBeVisible();
    await expect(page.locator("text=HAS/HASF Live Project Tracker")).toBeVisible();
  });
});
