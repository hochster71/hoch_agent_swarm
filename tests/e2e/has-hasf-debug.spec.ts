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

test("debug mirror visibility", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  
  console.log("Clicking Live Tracker Mirror...");
  const navItem = page.locator('aside >> text="Live Tracker Mirror"');
  await navItem.click();
  await page.waitForTimeout(1000);

  const containerBox = await page.locator(".app-container").boundingBox();
  console.log("App Container Box:", containerBox);

  const viewportBox = await page.locator(".viewport").boundingBox();
  console.log("Viewport Box:", viewportBox);

  const mirrorBox = await page.locator("#view-mirror").boundingBox();
  console.log("Mirror Box:", mirrorBox);
});
