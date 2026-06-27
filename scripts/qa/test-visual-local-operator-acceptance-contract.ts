import * as fs from 'fs';
import * as path from 'path';

function runLocalOperatorAcceptanceTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL OPERATOR ACCEPTANCE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const decisionJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/local_operator_acceptance.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/29_local_operator_acceptance.md');

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
  assert(fs.existsSync(decisionJsonFile), "local_operator_acceptance.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/29_local_operator_acceptance.md exists");

  if (!fs.existsSync(decisionJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let record: any;
  try {
    record = JSON.parse(fs.readFileSync(decisionJsonFile, 'utf-8'));
    assert(true, "local_operator_acceptance.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse local_operator_acceptance.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in decision record
  assert(record.decision === "ACCEPT_LOCAL_VISUAL_COCKPIT", "Decision check: ACCEPT_LOCAL_VISUAL_COCKPIT");
  assert(record.decision_scope === "local_only", "Decision scope check: local_only");
  assert(record.active_local_visual_cockpit === true, "Safety check: active_local_visual_cockpit is true");
  assert(record.rollback_ready === true, "Safety check: rollback_ready is true");
  assert(record.stabilization_complete === true, "Safety check: stabilization_complete is true");
  assert(Array.isArray(record.checks_failed) && record.checks_failed.length === 0, "Safety check: checks_failed is empty");
  assert(record.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(record.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(record.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(record.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(record.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(record.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");

  // 4. Verify paths exist
  const cockpitAbsPath = path.join(baseDir, record.accepted_cockpit_path);
  const rollbackAbsPath = path.join(baseDir, record.rollback_path);
  assert(fs.existsSync(cockpitAbsPath), "Accepted cockpit path exists");
  assert(fs.existsSync(rollbackAbsPath), "Rollback path exists");

  // 5. Verify blocked actions
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

  // 6. Verify next allowed phase
  assert(record.next_allowed_phase === "V21_LOCAL_RELEASE_PACKAGE", "Next allowed phase is V21_LOCAL_RELEASE_PACKAGE");

  // 7. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL OPERATOR ACCEPTANCE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL OPERATOR ACCEPTANCE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalOperatorAcceptanceTests();
