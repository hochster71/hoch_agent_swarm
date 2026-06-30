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

test.describe("Control Plane All Pages Render", () => {
  test("clicks every sidebar item and ensures it renders without crashing or showing a blank page", async ({ page }) => {
    const errors: Array<Error> = [];
    page.on("pageerror", exception => {
      errors.push(exception);
    });

    await page.goto("/", { waitUntil: "networkidle" });

    const sidebarItems = [
      { text: "Live Tracker Mirror", type: "mirror" },
      { text: "HAS Personal Core", type: "wip" },
      { text: "HAS Business Core", type: "wip" },
      { text: "HAS Hobby Core", type: "wip" },
      { text: "Global Registry", type: "tab", id: "canonicalRegistryTable" },
      { text: "Landscape Map", type: "tab", id: "landscapeLanes" },
      { text: "RACI Governance", type: "tab", id: "raciMatrixRows" },
      { text: "Gap Analysis", type: "tab", id: "gapsListRows" },
      { text: "Agent Swarm", type: "tab", id: "agentsTable" },
      { text: "Build Factory", type: "tab", id: "buildsTable" },
      { text: "Observability", type: "wip" },
      { text: "Production Acceleration", type: "wip" },
      { text: "Security Center", type: "wip" },
      { text: "Compliance", type: "wip" },
      { text: "Vulnerability Scan", type: "wip" },
      { text: "Policy Engine", type: "wip" },
      { text: "Reports", type: "wip" },
      { text: "Integrations", type: "wip" },
      { text: "Settings", type: "wip" }
    ];

    for (const item of sidebarItems) {
      const navItem = page.locator(`aside >> text="${item.text}"`);
      await expect(navItem).toBeVisible();
      await navItem.click();
      await page.waitForTimeout(400);

      if (item.type === "mirror") {
        await expect(page.locator("#view-mirror")).toBeVisible();
      } else if (item.type === "tab") {
        await expect(page.locator(`#${item.id}`)).toBeVisible();
      } else if (item.type === "wip") {
        await expect(page.locator("#view-wip")).toBeVisible();
        await expect(page.locator("#wipContentArea")).not.toBeEmpty();
        await expect(page.locator("#wipContentArea")).not.toContainText("Loading live data...");
      }

      // Assert no JavaScript runtime crashes
      expect(errors).toEqual([]);
    }
  });
});
