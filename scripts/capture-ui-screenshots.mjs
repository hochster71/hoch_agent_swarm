import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const baseUrl = process.env.UI_BASE_URL || "http://localhost:8000";
const outDir = process.env.SCREENSHOT_OUT_DIR
  ? path.resolve(process.env.SCREENSHOT_OUT_DIR)
  : path.resolve(__dirname, "../artifacts/ui-screenshot-evidence/visual-control-plane-local-v1/screenshots");

fs.mkdirSync(outDir, { recursive: true });

async function runCapture() {
  console.log("Launching Playwright browser...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  const results = [];

  const captureTab = async (tabSelector, fileName) => {
    try {
      console.log(`Capturing view: ${fileName} using selector: ${tabSelector}`);
      await page.goto(baseUrl, { waitUntil: "networkidle", timeout: 15000 });
      if (tabSelector !== "#nav-mission-control") {
        await page.click(tabSelector);
        await page.waitForTimeout(500); // Allow render transition
      }
      const outputPath = path.join(outDir, fileName);
      await page.screenshot({ path: outputPath, fullPage: true });
      results.push({ name: fileName, captured: true, path: outputPath });
    } catch (err) {
      console.error(`Failed to capture ${fileName}:`, err.message);
      results.push({ name: fileName, captured: false, error: err.message });
    }
  };

  // 1. Capture React Views from running server
  await captureTab("#nav-mission-control", "cockpit-overview.png");
  await captureTab("#nav-live-runtime", "runtime-health.png");
  await captureTab("#nav-model-router", "process-monitor.png");
  await captureTab("#nav-evidence", "evidence-status.png");
  await captureTab("#nav-settings", "blocked-actions.png");
  await captureTab("#nav-readiness", "security-ato-readiness.png");
  await captureTab("#nav-local-models", "backend-binding-readiness.png");
  await captureTab("#nav-model-mesh", "frontend-runtime-readiness.png");
  await captureTab("#nav-production-command-center", "production-command-center.png");
  await captureTab("#nav-release-provenance", "release-provenance.png");
  await captureTab("#nav-governance", "operator-governance.png");
  await captureTab("#nav-finance-command-center", "finance-command-center.png");

  // 2. Capture Local Cockpit HTML files via file:/// scheme
  const projectRoot = path.resolve(__dirname, "../");
  
  const captureLocalFile = async (relativeFilePath, fileName) => {
    try {
      const absolutePath = path.join(projectRoot, relativeFilePath);
      const url = `file://${absolutePath}`;
      console.log(`Capturing local file: ${fileName} from url: ${url}`);
      await page.goto(url, { waitUntil: "load", timeout: 15000 });
      await page.waitForTimeout(500);
      const outputPath = path.join(outDir, fileName);
      await page.screenshot({ path: outputPath, fullPage: true });
      results.push({ name: fileName, captured: true, path: outputPath });
    } catch (err) {
      console.error(`Failed to capture local file ${fileName}:`, err.message);
      results.push({ name: fileName, captured: false, error: err.message });
    }
  };

  await captureLocalFile("mockups/visual-control-plane/control-plane.html", "operator-acceptance-package.png");
  await captureLocalFile("artifacts/releases/visual-control-plane-local/control-plane.html", "local-preview-handoff-package.png");
  await captureLocalFile("artifacts/install-review/visual-control-plane-local/control-plane.html", "final-local-preview-closure.png");

  await browser.close();

  const resultsSummary = {
    baseUrl,
    timestamp: new Date().toISOString(),
    results
  };

  const resultsPath = process.env.SCREENSHOT_OUT_DIR
    ? path.join(path.dirname(path.resolve(process.env.SCREENSHOT_OUT_DIR)), "screenshot_capture_results.json")
    : path.resolve(__dirname, "../artifacts/ui-screenshot-evidence/visual-control-plane-local-v1/screenshot_capture_results.json");
  fs.writeFileSync(resultsPath, JSON.stringify(resultsSummary, null, 2));
  console.log(`Capture summary written to ${resultsPath}`);
}

runCapture().catch(err => {
  console.error("Runner failed:", err);
  process.exit(1);
});
