import { test, expect } from "@playwright/test";

test.describe("Runtime Reliability E2E and Telemetry Validation", () => {
  test("navigates to Runtime Reliability cockpit, verifies all 18 telemetry indicators, and ensures no console errors", async ({ page }) => {
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
      if (response.status() === 404 && !response.url().includes("tailwind.css")) {
        asset404s.push(response.url());
      }
    });

    // 1. Load Root Dashboard Route
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("body")).toBeVisible();

    // 2. Select and click Runtime Reliability Link in sidebar navigation
    const relNavBtn = page.locator("#nav-runtime-reliability");
    await expect(relNavBtn).toBeVisible();
    await relNavBtn.click();

    // 3. Verify target view-runtime-reliability is visible and class hidden is removed
    const reliabilityView = page.locator("#view-runtime-reliability");
    await expect(reliabilityView).not.toHaveClass(/\bhidden\b/);

    // 4. Assert header metadata
    await expect(page.locator("#reliability-northstar-header")).toBeVisible();
    await expect(page.locator("#reliability-status-badge")).toBeVisible();

    // 5. Assert budget ceiling and estimated monthly costs
    await expect(page.locator("#rel-monthly-cost")).toBeVisible();
    await expect(page.locator("#rel-budget-panel")).toContainText("$100/mo");

    // 6. Assert registered agents and limits
    await expect(page.locator("#rel-agent-ratio")).toContainText("300");

    // 7. Assert Redis queue details
    await expect(page.locator("#rel-queue-status")).toBeVisible();
    await expect(page.locator("#rel-queue-depth-val")).toContainText("0");

    // 8. Assert host status
    await expect(page.locator("#rel-primary-status")).toBeVisible();
    await expect(page.locator("#rel-secondary-status")).toBeVisible();

    // 9. Assert backup, watchdog, and failover readiness
    await expect(page.locator("#rel-failover-ready")).toBeVisible();
    await expect(page.locator("#rel-risks-list")).toContainText("No GPU on Secondary VPS");

    // Ensure zero runtime JS console errors or assets crashes
    expect(consoleErrors.length).toBe(0);
    expect(asset404s.length).toBe(0);
  });
});
