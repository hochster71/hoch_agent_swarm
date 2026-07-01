import * as fs from 'fs';
import * as path from 'path';

function runActivationPlanTests() {
  console.log("==================================================");
  console.log("VISUAL ACTIVATION PLAN CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const planJsonFile = path.join(baseDir, 'config/visual_activation_plan.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/15_operator_review_and_activation_plan.md');

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
  assert(fs.existsSync(planJsonFile), "config/visual_activation_plan.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/15_operator_review_and_activation_plan.md exists");

  if (!fs.existsSync(planJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON
  let plan: any;
  try {
    const rawJson = fs.readFileSync(planJsonFile, 'utf-8');
    plan = JSON.parse(rawJson);
    assert(true, "config/visual_activation_plan.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_activation_plan.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety & scope flags
  assert(plan.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  assert(plan.visual_preview_enabled === true, "Safety check: visual_preview_enabled is true");
  assert(plan.michael_hoch_approval_required === true, "Safety check: michael_hoch_approval_required is true");
  assert(plan.rollback_required === true, "Safety check: rollback_required is true");
  assert(plan.activation_scope === "local_only", "Safety check: activation_scope is local_only");

  // 4. Verify blocked actions
  const requiredBlocked = [
    "production deployment",
    "external publication",
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "security posture change"
  ];
  requiredBlocked.forEach(action => {
    assert(plan.blocked_actions.includes(action), `Blocked action '${action}' registered in JSON config`);
  });

  // 5. Verify rollback steps and decision table
  assert(plan.rollback_steps && plan.rollback_steps.length > 0, "Rollback steps list is non-empty");
  
  const decisions = plan.decision_table.map((d: any) => d.decision);
  assert(decisions.includes("GO"), "Decision table contains GO");
  assert(decisions.includes("CONDITIONAL_GO"), "Decision table contains CONDITIONAL_GO");
  assert(decisions.includes("NO_GO"), "Decision table contains NO_GO");

  // 6. Verify documentation content
  const docContent = fs.readFileSync(docFile, 'utf-8');
  assert(docContent.includes("Michael Hoch"), "Documentation contains explicit 'Michael Hoch' approval gate reference");
  assert(docContent.includes("active_cockpit_replacement_enabled"), "Documentation references feature flag key 'active_cockpit_replacement_enabled'");
  assert(docContent.includes("control-plane.html"), "Documentation references active cockpit page 'control-plane.html'");

  // 7. Verify no production activation is authorized
  assert(plan.feature_flags.active_cockpit_replacement_enabled === false, "Feature flag cockpit replacement is disabled by default");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL ACTIVATION PLAN CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL ACTIVATION PLAN CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runActivationPlanTests();
