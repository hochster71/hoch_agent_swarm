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

test("debug mirror visibility", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  
  page.on("console", msg => console.log(`BROWSER LOG: [${msg.type()}] ${msg.text()}`));
  page.on("pageerror", err => console.error(`BROWSER ERROR:`, err));

  console.log("Clicking Live Tracker Mirror...");
  const navItem = page.locator('aside >> text="Live Tracker Mirror"');
  await navItem.click();
  await page.waitForTimeout(1000);

  const displayStyle = await page.evaluate(() => {
    const el = document.getElementById("view-mirror");
    return el ? {
      outerHTML: el.outerHTML.slice(0, 200),
      display: el.style.display,
      computedDisplay: window.getComputedStyle(el).display,
      parentDisplay: window.getComputedStyle(el.parentElement).display,
      parentOuterHTML: el.parentElement.outerHTML.slice(0, 300)
    } : "NOT FOUND";
  });

  console.log("Result:", displayStyle);
});
