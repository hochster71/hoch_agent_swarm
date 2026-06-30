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

test.describe("Agent Genesis Liftoff & Swarm Routing E2E Test", () => {
  test("triggers agent liftoff and verifies spatial translation of agent node to destination lane", async ({ page, request }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    const agentNode = page.locator("#agent-theater-node-Master-Orchestrator");
    await expect(agentNode).toBeVisible();

    // Get initial position
    const boxBefore = await agentNode.boundingBox();
    expect(boxBefore).not.toBeNull();
    const initialX = boxBefore!.x;
    const initialY = boxBefore!.y;

    // Trigger spawning event
    const response = await request.post("/api/event", {
      data: {
        type: "agent_spawn",
        source: "Master Orchestrator",
        target: "has",
        payload_summary: "Master Orchestrator spawning sequence triggered"
      }
    });
    expect(response.ok()).toBe(true);

    // Wait and verify that the position changed (spawning triggers motion towards destination pod)
    await expect(async () => {
      const boxNow = await agentNode.boundingBox();
      expect(boxNow).not.toBeNull();
      // Position should be significantly different
      const diffX = Math.abs(boxNow!.x - initialX);
      const diffY = Math.abs(boxNow!.y - initialY);
      expect(diffX + diffY).toBeGreaterThan(5);
    }).toPass({ timeout: 5000 });
  });
});
