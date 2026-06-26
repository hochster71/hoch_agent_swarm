import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("Full-Page Swarm Traversal and Console Audit", () => {
  test("traverses every page, captures screenshots, and asserts zero console errors or 404s", async ({ page }) => {
    const consoleErrors: string[] = [];
    const asset404s: string[] = [];

    // Capture console errors
    page.on("console", (msg) => {
      if (msg.type() === "error" && !msg.text().includes("WebSocket")) {
        consoleErrors.push(msg.text());
      }
    });

    // Capture 404 response errors
    page.on("response", (response) => {
      if (response.status() === 404) {
        asset404s.push(response.url());
      }
    });

    // 1. Load localhost
    await page.goto("/", { waitUntil: "networkidle" });

    // Verify page has loaded
    await expect(page.locator("body")).toBeVisible();

    const outputDir = path.resolve(__dirname, "../../artifacts/qa/pages");
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Required nav link IDs and their corresponding view IDs and target screenshot names
    const pages = [
      { navId: "nav-readiness-autopilot", viewId: "view-readiness-autopilot", name: "readiness-autopilot.png" },
      { navId: "nav-hochster-runtime", viewId: "view-hochster-runtime", name: "hochster-runtime.png" },
      { navId: "nav-cybersecurity-factory", viewId: "view-cybersecurity-factory", name: "cybersecurity-factory.png" },
      { navId: "nav-remediation-safety", viewId: "view-remediation-safety", name: "remediation-safety.png" },
      { navId: "nav-runtime-audit", viewId: "view-runtime-audit", name: "runtime-audit.png" },
      { navId: "nav-error-budget", viewId: "view-error-budget", name: "error-budget.png" },
      { navId: "nav-release-provenance", viewId: "view-release-provenance", name: "release-provenance.png" },
      { navId: "nav-swarm-control", viewId: "view-swarm-control", name: "swarm-control.png" },
      { navId: "nav-mission-intel", viewId: "view-mission", name: "mission-intel.png" },
      { navId: "nav-timeline-replay", viewId: "view-replay", name: "timeline-replay.png" }
    ];

    for (const p of pages) {
      const navItem = page.locator(`#${p.navId}`);
      await expect(navItem).toBeVisible();
      await navItem.click();
      
      const viewItem = page.locator(`#${p.viewId}`);
      await expect(viewItem).not.toHaveClass(/\bhidden\b/);
      
      await page.waitForTimeout(300); // stabilize

      await page.screenshot({
        path: path.join(outputDir, p.name),
        fullPage: false
      });
    }

    // Capture Topology Agent Overlay screenshot (Swarm Control page overlay)
    await page.locator("#nav-swarm-control").click();
    await page.waitForTimeout(300);
    const overlay = page.locator("#topology-agent-overlay-runtime");
    await expect(overlay).toBeVisible();
    await page.screenshot({
      path: path.join(outputDir, "topology-agent-overlay.png"),
      fullPage: false
    });

    // Capture Runs Console screenshot
    const runsConsole = page.locator("#runs-control-panel");
    await expect(runsConsole).toBeVisible();
    await runsConsole.screenshot({
      path: path.join(outputDir, "runs-console.png")
    });

    // Check for errors
    expect(consoleErrors, `Uncaught console errors detected: ${consoleErrors.join("\n")}`).toEqual([]);
    expect(asset404s, `404 asset load failures detected: ${asset404s.join("\n")}`).toEqual([]);
  });
});
