import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("@legacy @compat @deorbited Cybersecurity Factory View Flow", () => {
  test.skip("submits app idea and processes swarm pipeline successfully", async ({ page }, testInfo) => {
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
    await expect(page.locator("#view-cybersecurity-factory").getByText("PASS", { exact: true }).first()).toBeVisible();

    // Wait for the pipeline to run and check stage visibility
    // The pipeline animates sequentially with timeouts. Let's wait for the final completed state.
    // We can also assert visibility of various text items that light up
    await expect(page.getByText("North Star Planning", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("PERT Analysis", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Cybersecurity Review", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("App Store Delivery", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Apple App Store", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Google Play", { exact: true }).first()).toBeVisible();

    // Wait for the pipeline status to complete or the final agent to finish
    await page.waitForTimeout(6500); // 14 stages * 400ms = 5.6s + 300ms initial

    // Assert that the Privacy Disclosure Consistency Check panel is visible
    await expect(page.getByText("Privacy Disclosure Consistency Check", { exact: true }).first()).toBeVisible();
    await expect(page.locator("#privacy-gate-status")).toHaveText("PASS (Consistent)");

    // Assert that "Evidence generated · signing pending" is present in E2E logs
    await expect(page.getByText("Evidence generated · signing pending", { exact: false })).toBeVisible();

    // Click on foreman-fizz agent chip to open capability manifest modal
    const foremanChip = page.locator("#factory-chip-foreman-fizz");
    await foremanChip.click();

    // Expect the dossier modal and capability manifest block to be visible
    const manifestContainer = page.locator("#topology-agent-modal-manifest-container");
    await expect(manifestContainer).toBeVisible();
    await expect(page.locator("#agent-manifest-allowed")).toHaveText("git, grep, view_file, list_dir");
    await expect(page.locator("#agent-manifest-denied")).toHaveText("run_command, write_to_file");

    // Close modal
    const closeBtn = page.locator("#topology-agent-modal-close");
    await closeBtn.click();

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
