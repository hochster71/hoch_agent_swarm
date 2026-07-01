import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("Live Runtime Cockpit View E2E Spec", () => {
  test("loads the cockpit dashboard, verifies the 12 cards, and performs view switching", async ({ page }) => {
    // Navigate to dashboard root
    await page.goto("/", { waitUntil: "networkidle" });

    page.on("console", msg => console.log("BROWSER CONSOLE:", msg.text()));

    // Assert that the body is visible and title matches
    await expect(page.locator("body")).toBeVisible();
    await expect(page).toHaveTitle(/Hoch Agent Swarm/);

    // 1. Verify that the 12 cards exist in the Mission Control cockpit view
    const requiredCards = [
      "runtime-process",
      "local-models",
      "model-router",
      "escalations",
      "detections",
      "readiness",
      "evidence",
      "immutability",
      "local-outage-queue",
      "port-hardening",
      "autonomy-budget",
      "device-registry"
    ];

    // Navigate to legacy tab so cards become visible
    const legacyTabBtn = page.locator("#btn-tab-legacy");
    if (await legacyTabBtn.isVisible()) {
      await legacyTabBtn.click();
    }

    for (const cardId of requiredCards) {
      const card = page.locator(`#card-${cardId}`);
      await expect(card).toBeVisible();
      const dot = page.locator(`#dot-${cardId}`);
      await expect(dot).toBeVisible();
      const stateVal = page.locator(`#state-${cardId}`);
      await expect(stateVal).toBeVisible();
    }

    // 2. Perform view navigation switches and assert view container visibilities
    const navViews = [
      { navId: "nav-live-runtime", viewId: "view-live-runtime" },
      { navId: "nav-local-models", viewId: "view-local-models" },
      { navId: "nav-model-router", viewId: "view-model-router" },
      { navId: "nav-escalations", viewId: "view-escalations" },
      { navId: "nav-evidence", viewId: "view-evidence" },
      { navId: "nav-detections", viewId: "view-detections" },
      { navId: "nav-readiness", viewId: "view-readiness" },
      { navId: "nav-settings", viewId: "view-settings" }
    ];

    for (const v of navViews) {
      // Auto-open parent details element to make the link visible/interactable
      await page.evaluate((id) => {
        const el = document.getElementById(id);
        const details = el ? el.closest("details") : null;
        if (details) details.open = true;
      }, v.navId);

      const navItem = page.locator(`#${v.navId}`);
      await expect(navItem).toBeVisible();
      
      try {
        await navItem.click({ timeout: 2000 });
      } catch (err) {
        await page.evaluate((id) => {
          const el = document.getElementById(id);
          if (el) el.click();
        }, v.navId);
      }

      await page.waitForTimeout(200);

      // Diagnostic check before expect
      const info = await page.evaluate((id) => {
        const el = document.getElementById(id);
        if (!el) return "NOT FOUND";
        const style = window.getComputedStyle(el);
        return {
          id: el.id,
          className: el.className,
          display: style.display,
          visibility: style.visibility,
          opacity: style.opacity,
          offsetHeight: el.offsetHeight,
          offsetWidth: el.offsetWidth,
          parent: el.parentElement ? {
            id: el.parentElement.id,
            className: el.parentElement.className,
            display: window.getComputedStyle(el.parentElement).display
          } : null
        };
      }, v.viewId);
      console.log(`DIAGNOSTIC for ${v.viewId}:`, JSON.stringify(info, null, 2));

      const viewItem = page.locator(`#${v.viewId}`);
      await expect(viewItem).toBeVisible();
      await expect(viewItem).not.toHaveClass(/\bhidden\b/);
    }

    // Go back to mission control
    await page.locator("#nav-mission-control").click();
    await expect(page.locator("#view-mission-control")).toBeVisible();

    // 3. Verify horizontal scrolling is not active under 100% zoom (no horizontal overflow)
    const isOverflowing = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowing).toBe(false);

    // Save screenshot of the live cockpit instrument
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/live-runtime-cockpit.png");
    const outputDir = path.dirname(screenshotPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    await page.screenshot({ path: screenshotPath, fullPage: false });
  });
});
