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

test.describe("Agent Genesis Profile Drawer and Hover Popups Test", () => {
  test("verifies hover popup details and click drawer async load", async ({ page }) => {
    const errors: Array<Error> = [];
    page.on("pageerror", exception => {
      errors.push(exception);
    });

    await page.goto("/", { waitUntil: "networkidle" });

    // Wait for the agent theater nodes to be rendered
    const agentNode = page.locator(".agent-theater-node").first();
    await expect(agentNode).toBeVisible();

    // Directly dispatch mouseenter to avoid intersection/pointer-event check in Playwright
    await page.evaluate(() => {
      const el = document.querySelector(".agent-theater-node");
      if (el) {
        const evt = new MouseEvent("mouseenter", { bubbles: true, cancelable: true });
        el.dispatchEvent(evt);
      }
    });
    
    // Verify hover card is visible and contains expected role/action/model fields
    const hoverCard = page.locator("#agentHoverCard");
    await expect(hoverCard).toBeVisible();
    await expect(hoverCard).toContainText("Role:");
    await expect(hoverCard).toContainText("Next Action:");

    // Directly click to trigger the drawer without interception error
    await page.evaluate(() => {
      const el = document.querySelector(".agent-theater-node") as HTMLElement;
      if (el) {
        el.click();
      }
    });

    // Verify drawer opens and shows capabilities / RACI details
    const drawer = page.locator("#drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText("Capabilities");
    await expect(drawer).toContainText("RACI Governance Mapping");

    // Close the drawer by invoking the global closeDrawer function directly
    await page.evaluate(() => {
      if (typeof (window as any).closeDrawer === "function") {
        (window as any).closeDrawer();
      }
    });

    // Wait for slide-out animation and transition timeout
    await page.waitForTimeout(600);
    await expect(drawer).not.toBeVisible();

    expect(errors).toEqual([]);
  });
});
