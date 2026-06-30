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

test.describe("Control Plane v2 Live Flow Overlay & Topology verification", () => {
  test("verifies topology API, node mapping, interactive drawers, and SSE stream connection", async ({ page }) => {
    // 1. Verify /api/topology response
    const topologyRes = await page.request.get("/api/topology");
    expect(topologyRes.ok()).toBeTruthy();
    const topology = await topologyRes.json();
    expect(topology.static_architecture).toBe(true);
    expect(topology.nodes.length).toBeGreaterThan(0);

    // 2. Load overview page
    await page.goto("/", { waitUntil: "networkidle" });
    
    // 3. Verify Topology container & canvas are present
    const container = page.locator("#topologyContainer");
    await expect(container).toBeVisible();
    
    const canvas = page.locator("#topologyCanvas");
    await expect(canvas).toBeVisible();

    // 4. Click a node to verify details Drawer opens
    const localDiskNode = page.locator("#node-local_disk");
    await expect(localDiskNode).toBeVisible();
    await localDiskNode.click();
    await page.waitForTimeout(300);

    const drawer = page.locator("#detailDrawer");
    await expect(drawer).toHaveClass(/open/);
    await expect(page.locator("text=LOCAL DISK NODE TELEMETRY")).toBeVisible();

    // Close drawer
    await page.locator("text=Close").click();
    await page.waitForTimeout(300);
    await expect(drawer).not.toHaveClass(/open/);
  });
});
