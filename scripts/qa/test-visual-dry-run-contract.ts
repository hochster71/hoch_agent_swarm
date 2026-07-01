import * as fs from 'fs';
import * as path from 'path';

function runDryRunTests() {
  console.log("==================================================");
  console.log("VISUAL DRY RUN CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const planJsonFile = path.join(baseDir, 'config/visual_dry_run_plan.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/local_replacement_dry_run_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/21_local_replacement_dry_run.md');
  const scriptFile = path.join(baseDir, 'scripts/visual/dry-run-local-cockpit-replacement.sh');

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
  assert(fs.existsSync(planJsonFile), "config/visual_dry_run_plan.json exists");
  assert(fs.existsSync(reportJsonFile), "local_replacement_dry_run_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/21_local_replacement_dry_run.md exists");
  assert(fs.existsSync(scriptFile), "dry-run-local-cockpit-replacement.sh exists");

  if (!fs.existsSync(planJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile) || !fs.existsSync(scriptFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let plan: any;
  let report: any;
  try {
    plan = JSON.parse(fs.readFileSync(planJsonFile, 'utf-8'));
    assert(true, "config/visual_dry_run_plan.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_dry_run_plan.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "local_replacement_dry_run_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse local_replacement_dry_run_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in plan and report
  assert(plan.dry_run_only === true, "Safety check: dry_run_only is true in plan");
  assert(report.dry_run_only === true, "Safety check: dry_run_only is true in report");
  assert(plan.replacement_performed === false, "Safety check: replacement_performed is false");
  assert(plan.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  assert(plan.local_only === true, "Safety check: local_only is true");
  assert(plan.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(plan.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(plan.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");

  // 4. Verify script invariants
  const scriptContent = fs.readFileSync(scriptFile, 'utf-8');
  assert(scriptContent.includes("set -euo pipefail"), "Script starts with set -euo pipefail");
  assert(!scriptContent.includes("rm -ref") && !scriptContent.includes("rm -rf") && !scriptContent.includes("rm "), "Script does not perform rm commands");
  assert(!scriptContent.includes("backend/"), "Script does not modify backend/ directory");
  assert(!scriptContent.includes("visual_runtime_flags.json"), "Script does not mutate runtime flags file");
  assert(scriptContent.includes("DRY_RUN_ONLY"), "Script logs DRY_RUN_ONLY");
  assert(scriptContent.includes("NO_ACTIVE_REPLACEMENT"), "Script logs NO_ACTIVE_REPLACEMENT");
  assert(scriptContent.includes("ROLLBACK_READY"), "Script logs ROLLBACK_READY");

  // 5. Verify paths
  assert(plan.baseline_cockpit_path === "mockups/visual-control-plane/control-plane.html", "Baseline cockpit path is correct");
  assert(plan.candidate_source_path === "mockups/visual-control-plane/dashboard-preview.html", "Candidate source path is correct");
  assert(plan.candidate_output_path.startsWith("artifacts/qa/visual_review"), "Candidate output path is under artifacts");

  // 6. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL DRY RUN CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL DRY RUN CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runDryRunTests();
