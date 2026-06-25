import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("Cybersecurity Factory View Flow", () => {
  test("submits app idea and processes swarm pipeline successfully", async ({ page }, testInfo) => {
    // Navigate to local dashboard
    await page.goto("/", { waitUntil: "networkidle" });

    // Click nav link for Cybersecurity Factory
    const navLink = page.locator("#nav-cybersecurity-factory");
    await expect(navLink).toBeVisible();
    await navLink.click();

    // Verify headers and key elements are visible
    const viewContainer = page.locator("#view-cybersecurity-factory");
    await expect(viewContainer).toBeVisible();

    await expect(page.getByText("Hoch Application Software Factory", { exact: false })).toBeVisible();
    await expect(page.getByText("Humanity Usefulness Gate", { exact: true }).first()).toBeVisible();

    // Fill in the input with emergency app idea
    const input = page.locator("#factory-app-idea-input");
    await expect(input).toBeVisible();
    await input.fill("Create an app that teaches families how to prepare for emergencies and organize supplies safely.");

    // Launch Swarm
    const launchBtn = page.locator("#factory-launch-swarm-button");
    await expect(launchBtn).toBeVisible();
    await launchBtn.click();

    // Expect Humanity Gate validation PASS to show
    await expect(page.locator("#gate-result-pass")).toBeVisible();
    await expect(page.getByText("PASS", { exact: true }).first()).toBeVisible();

    // Wait for the pipeline to run and check stage visibility
    // The pipeline animates sequentially with timeouts. Let's wait for the final completed state.
    // We can also assert visibility of various text items that light up
    await expect(page.getByText("North Star Planning", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("PERT\u200bAnalysis", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Cybersecurity Review", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("App Store Delivery", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Apple App Store", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Google Play", { exact: true }).first()).toBeVisible();

    // Wait for the pipeline status to complete or the final agent to finish
    await page.waitForTimeout(6500); // 14 stages * 400ms = 5.6s + 300ms initial

    // Ensure the QA artifacts folder exists
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/cybersecurity-factory-runtime.png");
    const artifactsDir = path.dirname(screenshotPath);
    if (!fs.existsSync(artifactsDir)) {
      fs.mkdirSync(artifactsDir, { recursive: true });
    }

    // Capture verification screenshot
    await page.screenshot({
      path: screenshotPath,
      fullPage: true
    });

    await testInfo.attach("cybersecurity-factory-runtime", {
      path: screenshotPath,
      contentType: "image/png"
    });
  });
});
