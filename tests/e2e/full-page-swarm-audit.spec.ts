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
      { navId: "nav-mission-control", viewId: "view-mission-control", name: "mission-control.png" },
      { navId: "nav-live-runtime", viewId: "view-live-runtime", name: "live-runtime.png" },
      { navId: "nav-local-models", viewId: "view-local-models", name: "local-models.png" },
      { navId: "nav-model-router", viewId: "view-model-router", name: "model-router.png" },
      { navId: "nav-escalations", viewId: "view-escalations", name: "escalations.png" },
      { navId: "nav-evidence", viewId: "view-evidence", name: "evidence.png" },
      { navId: "nav-detections", viewId: "view-detections", name: "detections.png" },
      { navId: "nav-readiness", viewId: "view-readiness", name: "readiness.png" },
      { navId: "nav-settings", viewId: "view-settings", name: "settings.png" }
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

    // Check for errors
    console.log("DEBUG CONSOLE ERRORS:", consoleErrors);
    console.log("DEBUG 404 ASSETS:", asset404s);
    expect(consoleErrors, `Uncaught console errors detected: ${consoleErrors.join("\n")}`).toEqual([]);
    expect(asset404s, `404 asset load failures detected: ${asset404s.join("\n")}`).toEqual([]);
  });
});
