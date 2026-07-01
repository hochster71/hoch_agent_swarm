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

test.describe("Control Plane UI Data Completeness", () => {
  test("verifies that pages render with useful live data, explicit fallback, or active statuses", async ({ page }) => {
    // Listen for JS errors
    const errors: Array<Error> = [];
    page.on("pageerror", exception => {
      errors.push(exception);
    });

    await page.goto("/", { waitUntil: "networkidle" });

    // Verify main overview layout
    await expect(page.locator("#readinessBanner")).toBeVisible();
    await expect(page.locator("#readinessBannerTitle")).not.toBeEmpty();

    // Verify dynamic page loading for observability
    await page.locator("aside >> text=Observability").click();
    await page.waitForTimeout(500);
    
    const contentArea = page.locator("#wipContentArea");
    await expect(contentArea).toBeVisible();
    await expect(contentArea).not.toContainText("Loading live data...");
    await expect(contentArea).not.toContainText("Error loading");
    
    // Verify specific metric card elements
    await expect(page.locator(".kpi-card >> text=SSE Live Event Stream")).toBeVisible();
    await expect(page.locator(".kpi-card >> text=Topology Edge Connections")).toBeVisible();

    // Verify dynamic page loading for production acceleration
    await page.locator("aside >> text=Production Acceleration").click();
    await page.waitForTimeout(500);
    await expect(contentArea).not.toContainText("Loading live data...");
    await expect(page.locator(".kpi-card >> text=Projected Acceleration Verdict")).toBeVisible();
    await expect(page.locator(".kpi-card >> text=Critical Path Drag")).toBeVisible();

    // Verify dynamic page loading for settings / integrations
    await page.locator("aside >> text=Integrations").click();
    await page.waitForTimeout(500);
    await expect(contentArea).not.toContainText("Loading live data...");
    await expect(page.locator(".kpi-card >> text=k3d Sidecar State")).toBeVisible();
    await expect(page.locator(".kpi-card >> text=Disk Available")).toBeVisible();

    // Assert no console errors occurred during page loads
    expect(errors).toEqual([]);
  });
});
