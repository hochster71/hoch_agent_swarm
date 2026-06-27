import * as fs from 'fs';
import * as path from 'path';

function runReplacementReadinessTests() {
  console.log("==================================================");
  console.log("VISUAL REPLACEMENT READINESS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const planJsonFile = path.join(baseDir, 'config/visual_replacement_readiness.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/live_replacement_readiness_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/20_live_replacement_readiness_plan.md');

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
  assert(fs.existsSync(planJsonFile), "config/visual_replacement_readiness.json exists");
  assert(fs.existsSync(reportJsonFile), "live_replacement_readiness_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/20_live_replacement_readiness_plan.md exists");

  if (!fs.existsSync(planJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let plan: any;
  let report: any;
  try {
    plan = JSON.parse(fs.readFileSync(planJsonFile, 'utf-8'));
    assert(true, "config/visual_replacement_readiness.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_replacement_readiness.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "live_replacement_readiness_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse live_replacement_readiness_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in plan and report
  assert(plan.replacement_ready === false, "Safety check: replacement_ready is false in plan");
  assert(report.replacement_ready === false, "Safety check: replacement_ready is false in report");
  assert(plan.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  assert(plan.local_only === true, "Safety check: local_only is true");
  assert(plan.operator_final_approval_required === true, "Safety check: operator_final_approval_required is true");
  assert(plan.rollback_verified_required === true, "Safety check: rollback_verified_required is true");
  assert(plan.baseline_backup_required === true, "Safety check: baseline_backup_required is true");

  // 4. Verify all 15 readiness gates are present
  const requiredGates = [
    "operator final approval gate",
    "baseline cockpit backup gate",
    "rollback verified gate",
    "visual parity gate",
    "telemetry truth gate",
    "state fallback gate",
    "accessibility gate",
    "tablet/ipad readability gate",
    "error budget gate",
    "security no-regression gate",
    "local-only scope gate",
    "backend mutation blocked gate",
    "prompt execution blocked gate",
    "approval decision execution blocked gate",
    "CI/QA full pass gate"
  ];
  requiredGates.forEach(gate => {
    assert(plan.readiness_gates.includes(gate), `Readiness gate registered in plan: '${gate}'`);
    assert(report.gates_pending.includes(gate), `Readiness gate pending in report: '${gate}'`);
  });

  // 5. Verify error budget contains zero-tolerance criteria
  const budgetKeys = [
    "zero_broken_dashboard_routes",
    "zero_unsupported_state_labels",
    "zero_fake_live_states",
    "zero_backend_mutation_paths",
    "zero_prompt_execution_paths",
    "zero_approval_decision_execution_paths",
    "zero_missing_rollback_steps",
    "zero_high_critical_unresolved_ui_safety_findings"
  ];
  budgetKeys.forEach(key => {
    assert(plan.error_budget[key] === true, `Error budget enforces zero-tolerance: '${key}'`);
  });

  // 6. Verify blocked actions are present
  const blockedActions = [
    "full active cockpit replacement",
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(plan.blocked_actions.includes(action), `Plan blocks action: '${action}'`);
    assert(report.blocked_actions.includes(action), `Report blocks action: '${action}'`);
  });

  // 7. Verify next allowed phase
  assert(plan.next_allowed_phase === "V12_LOCAL_REPLACEMENT_DRY_RUN", "Next allowed phase is V12_LOCAL_REPLACEMENT_DRY_RUN");

  // 8. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  // 9. Verify docs contents
  const docContent = fs.readFileSync(docFile, 'utf-8');
  assert(docContent.includes("FULL REPLACEMENT IS STILL BLOCKED"), "Documentation states that full replacement is still blocked");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL REPLACEMENT READINESS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL REPLACEMENT READINESS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runReplacementReadinessTests();
