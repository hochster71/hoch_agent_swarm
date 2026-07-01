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

test.describe("HOCH PODS Theater No-Fake-Data & Armed State Spec", () => {
  test("verifies WAITING/ARMED idle states render when no active events exist", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Verify that the readiness banner is present and displays the ARMED/WAITING state
    const banner = page.locator("#podReadinessBanner");
    await expect(banner).toBeVisible();
    
    const bannerText = await banner.textContent();
    // It should say "HOCH PODS ARMED" or "WAITING FOR NEXT REAL EVENT"
    expect(bannerText).toMatch(/ARMED|WAITING|ALL SYSTEMS GREEN/);

    // 2. Verify that there are no fake telemetry logs or fake running events
    const timeline = page.locator("#movieTimeline");
    await expect(timeline).toBeVisible();

    // Verify clip-pod-vault-open state is waiting (since no event has run yet)
    const vaultOpenClip = page.locator("#clip-pod-vault-open");
    await expect(vaultOpenClip).toBeVisible();
    await expect(vaultOpenClip).toContainText("WAITING");

    const blockedClip = page.locator("#clip-agent-blocked");
    await expect(blockedClip).toBeVisible();
    await expect(blockedClip).toContainText(/WAITING|ACTIVE/);
  });
});
