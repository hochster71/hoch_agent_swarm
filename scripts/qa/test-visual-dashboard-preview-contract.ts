import * as fs from 'fs';
import * as path from 'path';

function runDashboardPreviewTests() {
  console.log("==================================================");
  console.log("VISUAL DASHBOARD PREVIEW CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const previewHtmlFile = path.join(baseDir, 'mockups/visual-control-plane/dashboard-preview.html');
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/14_dashboard_integration_preview.md');
  const controlPlaneFile = path.join(baseDir, 'mockups/visual-control-plane/control-plane.html');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify files exist
  assert(fs.existsSync(previewHtmlFile), "dashboard-preview.html exists");
  assert(fs.existsSync(previewJsFile), "visual_dashboard_preview.js exists");
  assert(fs.existsSync(docFile), "14_dashboard_integration_preview.md documentation exists");
  assert(fs.existsSync(controlPlaneFile), "control-plane.html cockpit page remains intact");

  if (!fs.existsSync(previewHtmlFile) || !fs.existsSync(previewJsFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Read contents for verification
  const htmlContent = fs.readFileSync(previewHtmlFile, 'utf-8');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  // A. PREVIEW ONLY label check
  assert(htmlContent.includes('PREVIEW ONLY — NOT LIVE CONTROL'), "dashboard-preview.html contains 'PREVIEW ONLY — NOT LIVE CONTROL'");

  // B. Safety checks: No mutation, WebSocket, EventSource, or POST/PUT/DELETE
  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket usage in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource usage in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  // C. Reference check: references visual_adapters.js
  assert(htmlContent.includes('visual_adapters.js'), "dashboard-preview.html references visual_adapters.js");

  // D. Decision/Execution endpoint check
  assert(!jsContent.includes('/decision'), "Safety check: No approval decision API endpoints referenced in preview JS");
  assert(!jsContent.includes('/execute') && !jsContent.includes('/kickoff'), "Safety check: No prompt execution API endpoints referenced in preview JS");

  // E. 8 state labels appear in preview or fixtures
  const stateLabels = ["LIVE", "DEGRADED", "PENDING", "SIMULATED", "STALE", "FAIL-CLOSED", "UNAVAILABLE", "UNKNOWN"];
  stateLabels.forEach(label => {
    const found = jsContent.includes(label) || htmlContent.includes(label);
    assert(found, `State label '${label}' is represented in dashboard preview or fixtures`);
  });

  // F. Disabled or visual-only approvals
  assert(jsContent.includes('disabled') || jsContent.includes('VISUAL ONLY'), "Visual-only disabled approval controls are defined in the JS render loop");

  // G. Source, freshness, evidence labels
  assert(jsContent.includes('Source:') && jsContent.includes('Freshness:') && jsContent.includes('Evidence:'), "Source, Freshness, and Evidence labels are generated on cards");

  // H. Enforce fallbacks by invoking adapters using fixtures in JS context
  const adapters = require(path.join(baseDir, 'frontend/visual_adapters.js'));
  const fixtures = JSON.parse(fs.readFileSync(path.join(baseDir, 'frontend/visual_adapters.test-fixtures.json'), 'utf-8'));

  // Missing data resolves to UNAVAILABLE
  const missingTelemetry = adapters.adaptCockpitTelemetry(fixtures.cockpit_missing);
  assert(missingTelemetry.state === "UNAVAILABLE", "Invariant: Missing telemetry maps to UNAVAILABLE");

  // Stale data resolves to STALE
  const staleTelemetry = adapters.adaptCockpitTelemetry(fixtures.cockpit_stale);
  assert(staleTelemetry.state === "STALE", "Invariant: Stale telemetry maps to STALE");

  // Bypass/security fixture resolves to FAIL_CLOSED
  const fcRouterPlan = adapters.adaptPromptRouterPlan(fixtures.prompt_router_fail_closed);
  assert(fcRouterPlan.state === "FAIL-CLOSED", "Invariant: Fail-closed risk plan maps to FAIL-CLOSED");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL DASHBOARD PREVIEW CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL DASHBOARD PREVIEW CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runDashboardPreviewTests();
