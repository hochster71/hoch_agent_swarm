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

test.describe("HAS/HASF Mission Control Dashboard E2E", () => {
  test("verifies mission control page renders, handles intake goal submission, and approval deployment flow", async ({ page }) => {
    // 1. Goto home page
    await page.goto("/", { waitUntil: "networkidle" });

    // 2. Click sidebar Mission Control item
    const navItem = page.locator('aside >> text="Mission Control"');
    await expect(navItem).toBeVisible();
    await navItem.click();
    await page.waitForTimeout(500);

    // 3. Verify KPIs and structure
    await expect(page.locator('text="Total Swarm Missions"')).toBeVisible();
    await expect(page.locator('text="Running Swarms"')).toBeVisible();
    await expect(page.locator('text="Pending Human Approval"')).toBeVisible();
    await expect(page.locator('#missionGoalInput')).toBeVisible();
    await expect(page.locator('#missionSubmitBtn')).toBeVisible();

    // 4. Fill and submit intake goal
    await page.fill('#missionGoalInput', 'Launch Business Epic Fury');
    await page.click('#missionSubmitBtn');
    await page.waitForTimeout(600);

    // 5. Verify the new mission card exists in history and is selected
    const activeCard = page.locator('.active-mission-card');
    await expect(activeCard).toBeVisible();
    await expect(activeCard).toContainText('fury-');
    await expect(activeCard).toContainText('WAITING_FOR_APPROVAL');
    await expect(activeCard).toContainText('POD: BUSINESS');

    // 6. Verify approval button is visible and click it
    const approveBtn = activeCard.locator('.approve-mission-btn');
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();
    await page.waitForTimeout(600);

    // 7. Verify status changes to COMPLETED
    await expect(activeCard).toContainText('COMPLETED');
    await expect(approveBtn).not.toBeVisible();

    // 8. Verify the graph panel contains the task sequence nodes
    const graphPanel = page.locator('.mission-graph-panel');
    await expect(graphPanel).toContainText('Step 1');
    await expect(graphPanel).toContainText('Step 2');
    await expect(graphPanel).toContainText('Check Market Readiness');
    await expect(graphPanel).toContainText('Verify Pricing Matrix');
  });
});
