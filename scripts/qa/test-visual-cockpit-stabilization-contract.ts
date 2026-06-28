import * as fs from 'fs';
import * as path from 'path';

function runStabilizationTests() {
  console.log("==================================================");
  console.log("VISUAL COCKPIT STABILIZATION CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_cockpit_stabilization.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/local_visual_cockpit_stabilization_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/28_local_visual_cockpit_stabilization.md');
  const stylesFile = path.join(baseDir, 'mockups/visual-control-plane/styles.css');

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
  assert(fs.existsSync(configJsonFile), "config/visual_cockpit_stabilization.json exists");
  assert(fs.existsSync(reportJsonFile), "local_visual_cockpit_stabilization_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/28_local_visual_cockpit_stabilization.md exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let config: any;
  let report: any;
  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_cockpit_stabilization.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_cockpit_stabilization.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "local_visual_cockpit_stabilization_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse local_visual_cockpit_stabilization_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in config and report
  assert(config.local_only === true, "Safety check: local_only is true");
  assert(config.active_local_visual_cockpit === true, "Safety check: active_local_visual_cockpit is true");
  assert(config.active_cockpit_replacement_enabled === true, "Safety check: active_cockpit_replacement_enabled is true (controlled local visual scope)");
  assert(config.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(config.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(config.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(config.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");
  assert(config.rollback_required === true, "Safety check: rollback_required is true");

  // 4. Verify paths exist
  const cockpitAbsPath = path.join(baseDir, config.cockpit_path);
  const rollbackAbsPath = path.join(baseDir, config.rollback_path);
  assert(fs.existsSync(cockpitAbsPath), "Cockpit file exists");
  assert(fs.existsSync(rollbackAbsPath), "Rollback instruction file exists");

  // 5. Verify cockpit content verification markers
  const cockpitContent = fs.readFileSync(cockpitAbsPath, 'utf-8');
  assert(cockpitContent.includes("LOCAL") || cockpitContent.includes("PREVIEW"), "Cockpit file contains LOCAL or PREVIEW status language");
  assert(cockpitContent.includes("Source") || cockpitContent.includes("[SRC]"), "Cockpit file contains Source or [SRC]");
  assert(cockpitContent.includes("Freshness") || cockpitContent.includes("[TIME]"), "Cockpit file contains Freshness or [TIME]");
  assert(cockpitContent.includes("Evidence") || cockpitContent.includes("[EVID]"), "Cockpit file contains Evidence or [EVID]");
  assert(cockpitContent.includes("FAIL-CLOSED"), "Cockpit file contains FAIL-CLOSED");

  // 6. Verify tablet/iPad responsive media queries in stylesheet
  assert(fs.existsSync(stylesFile), "Stylesheet file mockups/visual-control-plane/styles.css exists");
  if (fs.existsSync(stylesFile)) {
    const stylesContent = fs.readFileSync(stylesFile, 'utf-8');
    assert(stylesContent.includes("@media") && stylesContent.includes("max-width: 1024px"), "Styles retain tablet/iPad responsive media queries");
  }

  // 7. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  // 8. Verify report status
  if (report.decision === "STABILIZATION_COMPLETE") {
    assert(report.checks_failed.length === 0, "Report shows checks_failed is empty after stabilization completion");
  }

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL COCKPIT STABILIZATION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL COCKPIT STABILIZATION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runStabilizationTests();
