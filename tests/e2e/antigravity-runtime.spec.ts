import { test, expect } from "@playwright/test";

const requiredNavLabels = [
  "Readiness Autopilot",
  "HOCHSTER Runtime",
  "Remediation Safety",
  "Runtime Audit",
  "Error Budget",
  "Release Provenance",
  "Swarm Control",
  "Mission Intel",
  "Timeline Replay"
];

const forbiddenLegacyText = [
  "PERT Analysis",
  "Security Audit"
];

const forbiddenRemediationText = [
  "CLUSTER TASK HISTORY",
  "Code Generation",
  "Refactoring Swarm",
  "Unit Testing",
  "task-L3",
  "task-W1"
];

test.describe("Antigravity runtime console", () => {
  test("loads without production CSS/runtime regressions", async ({ page }, testInfo) => {
    const consoleErrors: string[] = [];

    page.on("console", (msg) => {
      const text = msg.text();
      if (msg.type() === "error" || text.includes("cdn.tailwindcss.com should not be used in production")) {
        consoleErrors.push(text);
      }
    });

    await page.goto("/", { waitUntil: "networkidle" });

    await expect(page.locator("body")).toBeVisible();

    for (const label of requiredNavLabels) {
      await expect(page.locator(".sidebar").getByText(label, { exact: true })).toBeVisible();
    }

    for (const label of forbiddenLegacyText) {
      await expect(page.getByText(label, { exact: true })).toHaveCount(0);
    }

    expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);

    await page.screenshot({
      path: "artifacts/qa/antigravity-runtime-home.png",
      fullPage: true
    });

    await testInfo.attach("runtime-home", {
      path: "artifacts/qa/antigravity-runtime-home.png",
      contentType: "image/png"
    });
  });

  test("remediation safety view is semantically correct", async ({ page }, testInfo) => {
    await page.goto("/", { waitUntil: "networkidle" });

    await page.getByText("Remediation Safety", { exact: true }).click();

    const remediationView = page.locator("#view-remediation-safety");
    await expect(remediationView).toBeVisible();

    for (const required of [
      "Safety Gates",
      "Dry-Run Simulation",
      "Approval Policy",
      "Rollback Plan",
      "Active Incidents",
      "Red-Team Safety Validation",
      "Burn Rate"
    ]) {
      await expect(remediationView.getByText(required, { exact: false })).toBeVisible();
    }

    for (const forbidden of forbiddenRemediationText) {
      await expect(remediationView.getByText(forbidden, { exact: false })).toHaveCount(0);
    }

    await page.screenshot({
      path: "artifacts/qa/antigravity-remediation-safety.png",
      fullPage: true
    });

    await testInfo.attach("remediation-safety", {
      path: "artifacts/qa/antigravity-remediation-safety.png",
      contentType: "image/png"
    });
  });

  test("all locked nav modules can activate", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });

    for (const label of requiredNavLabels) {
      const navItem = page.locator(".sidebar").getByText(label, { exact: true });
      await navItem.click();
      await expect(navItem).toBeVisible();
    }
  });
});
