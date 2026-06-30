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

test.describe("HOCH PODS Theater Reduced Motion E2E Spec", () => {
  test("verifies toggling reduced motion correctly adds the CSS fallback class", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    const theater = page.locator(".hoch-pods-theater");
    await expect(theater).toBeVisible();

    // 1. Initial state check: class should not be present
    let className = await theater.getAttribute("class");
    expect(className).not.toContain("reduced-motion-state");

    // 2. Toggle Reduced Motion checkbox on
    const toggle = page.locator("#reducedMotionToggle");
    await expect(toggle).toBeVisible();
    await toggle.check();

    // 3. Verify class is added
    className = await theater.getAttribute("class");
    expect(className).toContain("reduced-motion-state");

    // 4. Toggle Reduced Motion checkbox off
    await toggle.uncheck();

    // 5. Verify class is removed
    className = await theater.getAttribute("class");
    expect(className).not.toContain("reduced-motion-state");
  });
});
