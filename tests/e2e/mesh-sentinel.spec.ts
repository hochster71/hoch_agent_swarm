import { test, expect } from "@playwright/test";

test("Mesh Sentinel live map loads without fake topology", async ({ page }) => {
  await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle" });

  const nav = page.getByText("Mesh Sentinel", { exact: true });
  await expect(nav).toBeVisible();
  await nav.click();

  await expect(page.getByText("HOCH Mesh Sentinel Map")).toBeVisible();
  await expect(page.getByText("Rescan AI Runtimes")).toBeVisible();
  await expect(page.locator("#mesh-sentinel-map")).toBeVisible();

  await expect(page.getByText("43 agents operational")).toHaveCount(0);
  await expect(page.getByText("Mean cluster CPU load")).toHaveCount(0);
  await expect(page.getByText("HEALTHY 100%")).toHaveCount(0);
  await expect(page.getByText("10 ASSETS ACTIVE")).toHaveCount(0);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  expect(overflow).toBeFalsy();
});
