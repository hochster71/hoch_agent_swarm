import { test, expect } from "@playwright/test";

test.describe("Swarm Dashboard Layout Theme Skinning E2E", () => {
  test("successfully applies and renders selected themes", async ({ page }, testInfo) => {
    page.on("console", msg => console.log(`BROWSER CONSOLE: ${msg.text()}`));
    page.on("pageerror", err => console.error(`BROWSER ERROR: ${err.message}`));

    // Navigate to homepage
    await page.goto("/", { waitUntil: "load" });

    // Clear localStorage and reload
    await page.evaluate(() => {
      localStorage.removeItem("selected-theme");
      localStorage.removeItem("hoch-theme");
    });
    await page.reload({ waitUntil: "load" });

    const themeSelector = page.locator("#theme-selector");
    await expect(themeSelector).toBeVisible();

    const body = page.locator("body");

    // 1. Verify Green Theme
    await themeSelector.selectOption("theme-green");
    await page.waitForTimeout(500);
    await expect(body).toHaveClass(/theme-green/);
    
    // Check computed CSS variable --bg-base is mapped correctly to #020604
    const greenBgBase = await body.evaluate(el => getComputedStyle(el).getPropertyValue("--bg-base").trim());
    expect(greenBgBase).toBe("#020604");

    await page.screenshot({ path: "artifacts/qa/theme-green-success.png" });
    await testInfo.attach("theme-green-success", {
      path: "artifacts/qa/theme-green-success.png",
      contentType: "image/png"
    });

    // 2. Verify Blue Theme
    await themeSelector.selectOption("theme-blue");
    await page.waitForTimeout(500);
    await expect(body).toHaveClass(/theme-blue/);
    
    // Check computed CSS variable --bg-base is mapped correctly to #02040c
    const blueBgBase = await body.evaluate(el => getComputedStyle(el).getPropertyValue("--bg-base").trim());
    expect(blueBgBase).toBe("#02040c");

    await page.screenshot({ path: "artifacts/qa/theme-blue-success.png" });
    await testInfo.attach("theme-blue-success", {
      path: "artifacts/qa/theme-blue-success.png",
      contentType: "image/png"
    });

    // 3. Verify Pink Theme
    await themeSelector.selectOption("theme-pink");
    await page.waitForTimeout(500);
    await expect(body).toHaveClass(/theme-pink/);
    
    // Check computed CSS variable --bg-base is mapped correctly to #0c0206
    const pinkBgBase = await body.evaluate(el => getComputedStyle(el).getPropertyValue("--bg-base").trim());
    expect(pinkBgBase).toBe("#0c0206");

    await page.screenshot({ path: "artifacts/qa/theme-pink-success.png" });
    await testInfo.attach("theme-pink-success", {
      path: "artifacts/qa/theme-pink-success.png",
      contentType: "image/png"
    });
  });
});
