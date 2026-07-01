import * as fs from 'fs';
import * as path from 'path';

function runControlledSubstitutionTests() {
  console.log("==================================================");
  console.log("VISUAL CONTROLLED SUBSTITUTION CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_controlled_substitution.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/controlled_local_substitution_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/24_controlled_local_substitution.md');
  const scriptFile = path.join(baseDir, 'scripts/visual/controlled-local-cockpit-substitution.sh');

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
  assert(fs.existsSync(configJsonFile), "config/visual_controlled_substitution.json exists");
  assert(fs.existsSync(reportJsonFile), "controlled_local_substitution_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/24_controlled_local_substitution.md exists");
  assert(fs.existsSync(scriptFile), "controlled-local-cockpit-substitution.sh exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile) || !fs.existsSync(scriptFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let config: any;
  let report: any;
  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_controlled_substitution.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_controlled_substitution.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "controlled_local_substitution_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse controlled_local_substitution_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in config and report
  assert(config.local_only === true, "Safety check: local_only is true");
  assert(config.controlled_substitution_allowed === true, "Safety check: controlled_substitution_allowed is true");
  assert(config.active_cockpit_replacement_enabled === true, "Safety check: active_cockpit_replacement_enabled is true (controlled V15 scope)");
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
  assert(scriptContent.includes("CONTROLLED_LOCAL_SUBSTITUTION"), "Script prints CONTROLLED_LOCAL_SUBSTITUTION");
  assert(scriptContent.includes("LOCAL_ONLY"), "Script prints LOCAL_ONLY");
  assert(scriptContent.includes("BACKUP_CREATED"), "Script prints BACKUP_CREATED");
  assert(scriptContent.includes("ROLLBACK_READY"), "Script prints ROLLBACK_READY");
  assert(scriptContent.includes("NO_BACKEND_MUTATION"), "Script prints NO_BACKEND_MUTATION");

  // 5. Verify dynamic report state based on execution
  if (report.decision === "CONTROLLED_LOCAL_SUBSTITUTION_COMPLETE") {
    assert(report.substitution_performed === true, "Report shows substitution_performed=true after execution");
    assert(report.backup_created === true, "Report shows backup_created=true after execution");
    assert(report.rollback_ready === true, "Report shows rollback_ready=true after execution");
    
    const absRollbackPath = path.join(baseDir, config.rollback_path);
    assert(fs.existsSync(absRollbackPath), "Staged rollback instruction file exists after execution");
  } else {
    assert(report.substitution_performed === false, "Report shows substitution_performed=false before execution");
  }

  // 6. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL CONTROLLED SUBSTITUTION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL CONTROLLED SUBSTITUTION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runControlledSubstitutionTests();
