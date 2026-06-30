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

test.describe("HAS/HASF Kubernetes Sidecar Observability Spec", () => {
  test("verifies local k8s sidecar script existence and baseline integration health", async ({ page }) => {
    // 1. Verify scripts exist on disk
    const statusScriptPath = path.join(__dirname, "..", "..", "scripts", "k8s_sidecar_status.sh");
    expect(fs.existsSync(statusScriptPath)).toBe(true);

    const bootstrapScriptPath = path.join(__dirname, "..", "..", "scripts", "k8s_sidecar_bootstrap.sh");
    expect(fs.existsSync(bootstrapScriptPath)).toBe(true);

    // 2. Goto baseline Control Plane
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("text=HAS/HASF CONTROL PLANE")).toBeVisible();

    // 3. Confirm sidecar status bar or truth badge shows LIVE_API_TRUTH
    const truthBadge = page.locator("#truthSourceBadge");
    await expect(truthBadge).toContainText("LIVE_API_TRUTH");

    // 4. Ensure no fake sidecar events are fabricated in the logs
    const eventLogContainer = page.locator("#sseEventsContainer");
    if (await eventLogContainer.isVisible()) {
      const eventTexts = await eventLogContainer.innerText();
      // Ensure no fictional "fake-sidecar-telemetry" exists
      expect(eventTexts).not.toContain("fake-sidecar-telemetry");
    }

    // 5. Verify /api/disk responds successfully
    const diskResponse = await page.request.get("/api/disk");
    expect(diskResponse.status()).toBe(200);
    const diskJson = await diskResponse.json();
    expect(diskJson).toHaveProperty("snapshot_allowed");
    expect(diskJson).toHaveProperty("disk_available");
  });
});
