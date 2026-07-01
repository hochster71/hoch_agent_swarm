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

test.describe("Agent Genesis Spin-Up Animation E2E Test", () => {
  test("triggers agent animation transition when an SSE event arrives", async ({ page, request }) => {
    const errors: Array<Error> = [];
    page.on("pageerror", exception => {
      errors.push(exception);
    });

    await page.goto("/", { waitUntil: "networkidle" });

    const agentNode = page.locator("#agent-theater-node-Master-Orchestrator");
    await expect(agentNode).toBeVisible();

    // Trigger an SSE event by posting to /api/event
    const response = await request.post("/api/event", {
      data: {
        type: "heartbeat",
        source: "Master Orchestrator",
        target: "agent_swarm",
        payload_summary: "Agent Master Orchestrator heartbeat check"
      }
    });
    expect(response.ok()).toBe(true);

    // Wait and assert that the CSS class changes (it should transition from registered -> queued -> spawning -> running)
    await expect(async () => {
      const className = await agentNode.getAttribute("class");
      expect(className).toMatch(/agent-state-(queued|spawning|running|initializing)/);
    }).toPass({ timeout: 5000 });

    expect(errors).toEqual([]);
  });
});
