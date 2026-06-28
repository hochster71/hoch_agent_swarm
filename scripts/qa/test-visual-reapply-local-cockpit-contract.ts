import * as fs from 'fs';
import * as path from 'path';

function runReapplyLocalCockpitTests() {
  console.log("==================================================");
  console.log("VISUAL REAPPLY LOCAL COCKPIT CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_reapply_local_cockpit.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/reapply_local_visual_cockpit_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/27_reapply_local_visual_cockpit.md');
  const scriptFile = path.join(baseDir, 'scripts/visual/reapply-local-visual-cockpit.sh');

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
  assert(fs.existsSync(configJsonFile), "config/visual_reapply_local_cockpit.json exists");
  assert(fs.existsSync(reportJsonFile), "reapply_local_visual_cockpit_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/27_reapply_local_visual_cockpit.md exists");
  assert(fs.existsSync(scriptFile), "reapply-local-visual-cockpit.sh exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile) || !fs.existsSync(scriptFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let config: any;
  let report: any;
  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_reapply_local_cockpit.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_reapply_local_cockpit.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "reapply_local_visual_cockpit_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse reapply_local_visual_cockpit_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in config and report
  assert(config.local_only === true, "Safety check: local_only is true");
  assert(config.required_operator_decision === "REAPPLY_VISUAL_COCKPIT_LOCALLY", "Required operator decision is REAPPLY_VISUAL_COCKPIT_LOCALLY");
  assert(config.reapply_allowed === true, "Safety check: reapply_allowed is true");
  assert(config.active_cockpit_replacement_enabled === true, "Safety check: active_cockpit_replacement_enabled is true (controlled V18 scope)");
  assert(config.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(config.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(config.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(config.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");
  assert(config.rollback_required === true, "Safety check: rollback_required is true");

  // 4. Verify script source checks
  const scriptContent = fs.readFileSync(scriptFile, 'utf-8');
  assert(scriptContent.includes("set -euo pipefail"), "Script starts with set -euo pipefail");
  assert(!scriptContent.includes("rm -ref") && !scriptContent.includes("rm -rf") && !scriptContent.includes("rm "), "Script does not perform rm commands");
  assert(!scriptContent.includes("backend/"), "Script does not modify backend/ directory");
  assert(scriptContent.includes("REAPPLY_LOCAL_VISUAL_COCKPIT"), "Script prints REAPPLY_LOCAL_VISUAL_COCKPIT");
  assert(scriptContent.includes("LOCAL_ONLY"), "Script prints LOCAL_ONLY");
  assert(scriptContent.includes("BACKUP_CREATED"), "Script prints BACKUP_CREATED");
  assert(scriptContent.includes("ROLLBACK_READY"), "Script prints ROLLBACK_READY");
  assert(scriptContent.includes("NO_BACKEND_MUTATION"), "Script prints NO_BACKEND_MUTATION");

  // 5. Verify dynamic report state based on execution
  if (report.decision === "REAPPLY_LOCAL_VISUAL_COCKPIT_COMPLETE") {
    assert(report.reapply_performed === true, "Report shows reapply_performed=true after execution");
    assert(report.backup_created === true, "Report shows backup_created=true after execution");
    assert(report.rollback_ready === true, "Report shows rollback_ready=true after execution");
    
    const absRollbackPath = path.join(baseDir, config.rollback_path);
    assert(fs.existsSync(absRollbackPath), "Staged rollback instruction file exists after execution");
  } else {
    assert(report.reapply_performed === false, "Report shows reapply_performed=false before execution");
  }

  // 6. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL REAPPLY LOCAL COCKPIT CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL REAPPLY LOCAL COCKPIT CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runReapplyLocalCockpitTests();
