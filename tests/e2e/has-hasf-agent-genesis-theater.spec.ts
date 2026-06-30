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

test.describe("Agent Genesis Theater Layout & Orbit Test", () => {
  test("verifies Agent Genesis Theater elements exist and render", async ({ page }) => {
    const errors: Array<Error> = [];
    page.on("pageerror", exception => {
      errors.push(exception);
    });

    await page.goto("/", { waitUntil: "networkidle" });

    // Verify Swarm Core node exists
    const swarmCore = page.locator("#node-agent_swarm");
    await expect(swarmCore).toBeVisible();

    // Verify orbit ring inside SVG (circle element with cx/cy/r)
    const orbitRing = page.locator("#topologySvg circle");
    await expect(orbitRing).toBeVisible();

    // Verify agent-theater-node elements exist
    const agentNodes = page.locator(".agent-theater-node");
    const count = await agentNodes.count();
    expect(count).toBeGreaterThan(0);

    // Verify that at least one has an initials label
    const firstAgentText = await agentNodes.first().innerText();
    expect(firstAgentText.length).toBeLessThanOrEqual(2);

    expect(errors).toEqual([]);
  });
});
