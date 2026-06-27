import * as fs from 'fs';
import * as path from 'path';

function runPostRollbackDecisionTests() {
  console.log("==================================================");
  console.log("VISUAL POST-ROLLBACK DECISION CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const decisionJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/operator_post_rollback_decision.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/26_operator_post_rollback_decision.md');

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
  assert(fs.existsSync(decisionJsonFile), "operator_post_rollback_decision.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/26_operator_post_rollback_decision.md exists");

  if (!fs.existsSync(decisionJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let record: any;
  try {
    record = JSON.parse(fs.readFileSync(decisionJsonFile, 'utf-8'));
    assert(true, "operator_post_rollback_decision.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse operator_post_rollback_decision.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags and values in decision record
  assert(record.decision === "REAPPLY_VISUAL_COCKPIT_LOCALLY", "Decision check: REAPPLY_VISUAL_COCKPIT_LOCALLY");
  assert(record.decision_scope === "local_only", "Decision scope check: local_only");
  assert(record.rollback_executed === true, "Safety check: rollback_executed is true");
  assert(record.baseline_restored === true, "Safety check: baseline_restored is true");
  assert(record.substitution_performed_in_this_phase === false, "Safety check: substitution_performed_in_this_phase is false");
  assert(record.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(record.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(record.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(record.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(record.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(record.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");

  // 4. Verify blocked actions
  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(record.blocked_actions.includes(action), `Decision record blocks action: '${action}'`);
  });

  // 5. Verify next allowed phase
  assert(record.next_allowed_phase === "V18_REAPPLY_LOCAL_VISUAL_COCKPIT", "Next allowed phase is V18_REAPPLY_LOCAL_VISUAL_COCKPIT");

  // 6. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL POST-ROLLBACK DECISION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL POST-ROLLBACK DECISION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runPostRollbackDecisionTests();
