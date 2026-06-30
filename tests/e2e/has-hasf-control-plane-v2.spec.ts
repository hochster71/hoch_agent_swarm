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

test.describe("Control Plane v2 UI Shell verification", () => {
  test("verifies core layout, sidebar navigation, top status bar, kpi metrics, and sub-pages", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    // 1. Verify Brand and Shell header elements
    const brandHeader = page.locator("text=HAS/HASF CONTROL PLANE");
    await expect(brandHeader).toBeVisible();

    const statusBadge = page.locator("text=SYSTEM OPERATIONAL");
    await expect(statusBadge).toBeVisible();

    // 2. Verify sidebar groups
    await expect(page.locator("aside >> text=Core Hub")).toBeVisible();
    await expect(page.locator("aside >> text=Project Tracker")).toBeVisible();
    await expect(page.locator("aside >> text=Platforms")).toBeVisible();
    await expect(page.locator("aside >> text=DevSecOps")).toBeVisible();

    // 3. Verify KPI cards
    await expect(page.locator("#kpiAgents")).toBeVisible();
    await expect(page.locator("#kpiRegistry")).toBeVisible();
    await expect(page.locator("#kpiBuilds")).toBeVisible();
    await expect(page.locator("#kpiTasks")).toBeVisible();

    // 4. Verify navigating to sub-pages
    const registryItem = page.locator("aside >> text=Global Registry");
    await registryItem.click();
    await page.waitForTimeout(300);
    await expect(page.locator("#canonicalRegistryTable")).toBeVisible();

    const swarmItem = page.locator("aside >> text=Agent Swarm");
    await swarmItem.click();
    await page.waitForTimeout(300);
    await expect(page.locator("#agentsTable")).toBeVisible();

    const buildsItem = page.locator("aside >> text=Build Factory");
    await buildsItem.click();
    await page.waitForTimeout(300);
    await expect(page.locator("#buildsTable")).toBeVisible();
  });
});
