import { test, expect } from "@playwright/test";

test.describe("Main UI API Origin Cleanup Spec", () => {
  test("proves same-origin browser API paths and no CORS console errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    const absoluteApiRequests: string[] = [];

    // Capture console logs/errors
    page.on("console", (msg) => {
      if (msg.type() === "error" || msg.type() === "warning") {
        const text = msg.text();
        consoleErrors.push(text);
      }
    });

    // Capture page errors
    page.on("pageerror", (err) => {
      consoleErrors.push(err.message);
    });

    // Capture network requests to check for absolute localhost:8000 calls
    page.on("request", (request) => {
      const url = request.url();
      if (url.includes("localhost:8000") || url.includes("127.0.0.1:8000")) {
        absoluteApiRequests.push(url);
      }
    });

    // Navigate to dashboard root
    await page.goto("/", { waitUntil: "networkidle" });

    // Assert that the page loaded successfully
    await expect(page.locator("body")).toBeVisible();
    await expect(page).toHaveTitle(/Hoch Agent Swarm/);

    // Verify Final Verifier BLOCKED is visible
    const verifierStatus = page.locator("#op-verifier-status");
    await expect(verifierStatus).toContainText("BLOCKED");

    // Verify Readiness 50 is visible
    const readinessVal = page.locator("#op-readiness-val");
    await expect(readinessVal).toContainText("50");

    // Ensure no absolute requests were made to localhost:8000 or 127.0.0.1:8000
    expect(absoluteApiRequests).toEqual([]);

    // Ensure no CORS or load failures are in the console logs
    const corsErrors = consoleErrors.filter(
      (err) =>
        err.toLowerCase().includes("access control checks") ||
        err.toLowerCase().includes("typeerror: load failed")
    );
    expect(corsErrors).toEqual([]);
  });
});
