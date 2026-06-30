import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 45_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "artifacts/qa/playwright-antigravity-runtime.json" }],
    ["html", { outputFolder: "artifacts/qa/playwright-report", open: "never" }]
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || "https://has.localhost",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure"
  },
  grepInvert: process.env.COMPAT_TESTS ? undefined : /@legacy|@compat|@deorbited/,
  projects: [
    {
      name: "antigravity-chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
