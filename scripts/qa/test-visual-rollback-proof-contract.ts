import * as fs from 'fs';
import * as path from 'path';

function runRollbackProofTests() {
  console.log("==================================================");
  console.log("VISUAL ROLLBACK PROOF CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_rollback_proof.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/local_substitution_rollback_proof_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/25_local_substitution_validation_and_rollback_proof.md');
  const scriptFile = path.join(baseDir, 'scripts/visual/verify-local-cockpit-rollback.sh');

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
  assert(fs.existsSync(configJsonFile), "config/visual_rollback_proof.json exists");
  assert(fs.existsSync(reportJsonFile), "local_substitution_rollback_proof_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/25_local_substitution_validation_and_rollback_proof.md exists");
  assert(fs.existsSync(scriptFile), "verify-local-cockpit-rollback.sh exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile) || !fs.existsSync(scriptFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let config: any;
  let report: any;
  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_rollback_proof.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_rollback_proof.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "local_substitution_rollback_proof_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse local_substitution_rollback_proof_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in config and report
  assert(config.local_only === true, "Safety check: local_only is true");
  assert(config.rollback_required === true, "Safety check: rollback_required is true");
  assert(config.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(config.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(config.rollback_path === "artifacts/qa/visual_review/active_substitution/ROLLBACK.md", "Rollback path is referenced correctly");
  assert(config.baseline_cockpit_path === "mockups/visual-control-plane/control-plane.html", "Baseline cockpit path is referenced correctly");

  // 4. Verify script source checks
  const scriptContent = fs.readFileSync(scriptFile, 'utf-8');
  assert(scriptContent.includes("set -euo pipefail"), "Script starts with set -euo pipefail");
  assert(!scriptContent.includes("rm -ref") && !scriptContent.includes("rm -rf") && !scriptContent.includes("rm "), "Script does not perform rm commands");
  assert(!scriptContent.includes("backend/"), "Script does not modify backend/ directory");
  assert(scriptContent.includes("ROLLBACK_PROOF"), "Script prints ROLLBACK_PROOF");
  assert(scriptContent.includes("BASELINE_RESTORED"), "Script prints BASELINE_RESTORED");
  assert(scriptContent.includes("LOCAL_ONLY"), "Script prints LOCAL_ONLY");
  assert(scriptContent.includes("NO_BACKEND_MUTATION"), "Script prints NO_BACKEND_MUTATION");

  // 5. Verify dynamic report state based on execution
  if (report.decision === "ROLLBACK_PROOF_COMPLETE") {
    assert(report.rollback_executed === true, "Report shows rollback_executed=true after execution");
    assert(report.baseline_restored === true, "Report shows baseline_restored=true after execution");
  } else {
    assert(report.rollback_executed === false, "Report shows rollback_executed=false before execution");
  }

  // 6. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL ROLLBACK PROOF CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL ROLLBACK PROOF CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runRollbackProofTests();
