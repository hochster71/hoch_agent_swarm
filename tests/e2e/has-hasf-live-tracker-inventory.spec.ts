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

test.describe("Global Project Registry E2E Spec", () => {
  test("verifies inventory APIs, Global Registry tab navigation, summary statistics, and drawer click triggers", async ({ page }) => {
    // Navigate directly to local tracker root
    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Switch to Global Registry Tab
    const registryTabBtn = page.locator("#tab-registry");
    await expect(registryTabBtn).toBeVisible();
    await registryTabBtn.click();
    await page.waitForTimeout(500);

    // 2. Verify view panels & headers
    const summaryHeader = page.locator("text=HAS/HASF Global Registry Summary");
    await expect(summaryHeader).toBeVisible();

    const githubHeader = page.locator("text=Discovered GitHub Repositories");
    await expect(githubHeader).toBeVisible();

    const localHeader = page.locator("text=Discovered Local Workspaces");
    await expect(localHeader).toBeVisible();

    const cloudHeader = page.locator("text=Discovered Cloud Documents");
    await expect(cloudHeader).toBeVisible();

    // 3. Verify statistics are populated (not showing placeholders)
    const githubCount = page.locator("#regGithubCount");
    await expect(githubCount).not.toHaveText("-");
    const localCount = page.locator("#regLocalCount");
    await expect(localCount).not.toHaveText("-");
    const cloudCount = page.locator("#regCloudCount");
    await expect(cloudCount).not.toHaveText("-");

    // 4. Hover first local workspace row to trigger tooltip
    const localRow = page.locator("#registryLocalRows").locator("text=hoch_agent_swarm").first();
    await expect(localRow).toBeVisible();
    await localRow.hover();
    await page.waitForTimeout(200);

    // Verify tooltip shows up
    const tooltip = page.locator("#tooltip");
    await expect(tooltip).toBeVisible();

    // 5. Click the local workspace row to verify drawer details open
    await localRow.click();
    await page.waitForTimeout(200);
    const drawer = page.locator("#drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText("hoch_agent_swarm");

    // Close the drawer using Escape key
    await page.keyboard.press("Escape");
    await page.waitForTimeout(200);
    await expect(drawer).not.toBeVisible();
  });
});
