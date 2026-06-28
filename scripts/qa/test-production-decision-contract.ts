import * as fs from 'fs';
import * as path from 'path';

function runProductionDecisionTests() {
  console.log("==================================================");
  console.log("PRODUCTION OPERATOR DECISION GATE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr13Dir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');

  const manifestFile = path.join(pr13Dir, 'production_decision_manifest.json');
  const decisionFile = path.join(pr13Dir, 'production_readiness_go_no_go_decision.json');
  const boundaryFile = path.join(pr13Dir, 'decision_boundary_attestation.json');
  const blockedFile = path.join(pr13Dir, 'decision_blocked_actions.json');
  const sealFile = path.join(pr13Dir, 'pr13_final_seal.json');

  const pr12aManifest = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1/production_final_candidate_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR13 files exist
  assert(fs.existsSync(manifestFile), "production_decision_manifest.json exists");
  assert(fs.existsSync(decisionFile), "production_readiness_go_no_go_decision.json exists");
  assert(fs.existsSync(boundaryFile), "decision_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "decision_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr13_final_seal.json exists");

  assert(fs.existsSync(pr12aManifest), "PR12A manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(decisionFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let decision: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_decision_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    decision = JSON.parse(fs.readFileSync(decisionFile, 'utf-8'));
    assert(true, "production_readiness_go_no_go_decision.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse decision: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "decision_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "decision_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr13_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR13_PRODUCTION_READINESS_OPERATOR_CONTROLLED_STAGING_GO_NO_GO_DECISION", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR13 PRODUCTION READINESS OPERATOR CONTROLLED STAGING GO / NO-GO DECISION — ACCEPTED FOR OPERATOR DECISION RECORD ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify decision info
  const dec = decision.production_readiness_go_no_go_decision;
  assert(!!dec, "production_readiness_go_no_go_decision object exists");
  if (dec) {
    assert(dec.operator === "Michael Hoch", "Operator is Michael Hoch");
    assert(dec.decision === "GO_RECOMMENDED_FOR_CONTROLLED_STAGING_ENTRY", "Decision is GO_RECOMMENDED_FOR_CONTROLLED_STAGING_ENTRY");
    assert(dec.verification_checklist.no_drift_lock_active === true, "no_drift_lock_active check is true");
    assert(dec.verification_checklist.residual_risk_level === "LOW", "residual_risk_level check is LOW");
    assert(dec.verification_checklist.sandboxed_preview_passed === true, "sandboxed_preview_passed check is true");
    assert(dec.verification_checklist.contract_tests_passed === true, "contract_tests_passed check is true");
  }

  // 5. Verify blocked actions
  const requiredActions = [
    "production deployment",
    "git push",
    "main merge",
    "production secrets",
    "live external binding",
    "prompt execution",
    "approval execution",
    "external publication",
    "actual ATO claim"
  ];

  const blockedList = blocked.decision_blocked_actions;
  assert(Array.isArray(blockedList), "decision_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 6. Verify no file claims execution performed
  const allJsonContents = [manifest, decision, boundary, blocked, seal];
  allJsonContents.forEach(jsonObj => {
    const str = JSON.stringify(jsonObj);
    assert(!str.includes('"production_deployment": true') && 
           !str.includes('"performed": true') && 
           !str.includes('"git_push": true') && 
           !str.includes('"main_merge": true'), 
           "No file claims execution was performed");
  });

  // 7. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("PRODUCTION OPERATOR DECISION GATE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION OPERATOR DECISION GATE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionDecisionTests();
