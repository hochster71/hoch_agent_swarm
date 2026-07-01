import * as fs from 'fs';
import * as path from 'path';

function runOperatorDecisionTests() {
  console.log("==================================================");
  console.log("VISUAL OPERATOR DECISION CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const decisionJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/operator_decision_record.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/local_replacement_dry_run_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/23_operator_decision_record.md');

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
  assert(fs.existsSync(decisionJsonFile), "operator_decision_record.json exists");
  assert(fs.existsSync(reportJsonFile), "local_replacement_dry_run_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/23_operator_decision_record.md exists");

  if (!fs.existsSync(decisionJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let record: any;
  let report: any;
  try {
    record = JSON.parse(fs.readFileSync(decisionJsonFile, 'utf-8'));
    assert(true, "operator_decision_record.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse operator_decision_record.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "local_replacement_dry_run_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse local_replacement_dry_run_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in decision record
  assert(record.decision === "APPROVE_DRY_RUN_FOR_LOCAL_REPLACEMENT", "Decision check: APPROVE_DRY_RUN_FOR_LOCAL_REPLACEMENT");
  assert(record.decision_scope === "local_only", "Decision scope check: local_only");
  assert(record.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  assert(record.replacement_performed === false, "Safety check: replacement_performed is false");
  assert(record.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(record.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(record.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");

  // 4. Verify paths and existence of candidate and rollback files
  assert(record.candidate_path === "artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html", "Candidate path referenced correctly");
  assert(record.rollback_path === "artifacts/qa/visual_review/dry_run_candidate/ROLLBACK.md", "Rollback path referenced correctly");

  const absCandidatePath = path.join(baseDir, record.candidate_path);
  const absRollbackPath = path.join(baseDir, record.rollback_path);
  assert(fs.existsSync(absCandidatePath), "Staged candidate cockpit file exists");
  assert(fs.existsSync(absRollbackPath), "Staged rollback file exists");

  // 5. Verify blocked actions
  const blockedActions = [
    "production deployment",
    "external publication",
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(record.blocked_actions.includes(action), `Decision record blocks action: '${action}'`);
  });

  // 6. Verify next allowed phase
  assert(record.next_allowed_phase === "V15_CONTROLLED_LOCAL_SUBSTITUTION", "Next allowed phase is V15_CONTROLLED_LOCAL_SUBSTITUTION");

  // 7. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL OPERATOR DECISION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL OPERATOR DECISION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runOperatorDecisionTests();
