import { defineConfig, devices } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

// Load secrets from ~/.hoch-secrets/has-tracker.env if it exists
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

export default defineConfig({
  testDir: "tests/e2e",
  testMatch: [
    "**/has-hasf-*.spec.ts",
    "**/antigravity-runtime.spec.ts",
    "**/anti-fake-runtime.spec.ts",
    "**/hoch200-compute-setup.spec.ts",
    "**/rc26-relay-routing.spec.ts",
    "**/rc28-mission-execution-proof.spec.ts",
    "**/rc32-pert-command-center.spec.ts",
    "**/rc33-compute-utilization.spec.ts",
    "**/rc36-worker-dashboard.spec.ts",
    "**/rc37-dispatch-metrics.spec.ts",
    "**/rc38-goal-readiness.spec.ts",
    "**/rc39-telemetry-truth.spec.ts",
    "**/rc39-qa-audit-alignment.spec.ts",
    "**/rc40-compute-gap-pert.spec.ts",
    "**/rc41-worker-telemetry-accuracy.spec.ts",
    "**/rc42-epic-fury-csp-audit.spec.ts",
    "**/rc43-telemetry-freshness.spec.ts",
    "**/rc44-epic-fury-flowchart.spec.ts",
    "**/rc45-revenue-readiness.spec.ts",
    "**/rc46-revenue-action-queue.spec.ts",
    "**/rc47-epic-fury-admin-access.spec.ts",
    "**/rc48-hoch-pods-architecture.spec.ts",
    "**/rc49-hoch-pod-scheduler.spec.ts",
    "**/rc49_5-telemetry-truth-freshness.spec.ts",
    "**/rc49_6-hoch-pods-visual-fidelity.spec.ts",
    "**/rc50-ai-business-structure.spec.ts",
    "**/rc49_7-compute-node-pruning.spec.ts",
    "**/rc50_1-hoch-hasf-soccer-pipeline.spec.ts",
  ],
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
    baseURL: process.env.E2E_BASE_URL || `http://localhost:${port}`,
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    httpCredentials: {
      username,
      password
    }
  },
  grepInvert: process.env.COMPAT_TESTS ? undefined : /@legacy|@compat|@deorbited/,
  projects: [
    {
      name: "antigravity-chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
