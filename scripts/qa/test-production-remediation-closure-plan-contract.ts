import * as fs from 'fs';
import * as path from 'path';

function runProductionClosureTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL CLOSURE PLAN VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr9Dir = path.join(baseDir, 'artifacts/production-readiness-remediation-closure-plan/visual-control-plane-local-v1');

  const manifestFile = path.join(pr9Dir, 'production_remediation_closure_manifest.json');
  const planFile = path.join(pr9Dir, 'production_remediation_closure_plan.json');
  const boundaryFile = path.join(pr9Dir, 'remediation_closure_boundary_attestation.json');
  const blockedFile = path.join(pr9Dir, 'remediation_closure_blocked_actions.json');
  const sealFile = path.join(pr9Dir, 'pr9_final_seal.json');

  const pr8Manifest = path.join(baseDir, 'artifacts/production-readiness-risk-register/visual-control-plane-local-v1/production_risk_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR9 files exist
  assert(fs.existsSync(manifestFile), "production_remediation_closure_manifest.json exists");
  assert(fs.existsSync(planFile), "production_remediation_closure_plan.json exists");
  assert(fs.existsSync(boundaryFile), "remediation_closure_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "remediation_closure_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr9_final_seal.json exists");

  assert(fs.existsSync(pr8Manifest), "PR8 risk manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(planFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let plan: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_remediation_closure_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    plan = JSON.parse(fs.readFileSync(planFile, 'utf-8'));
    assert(true, "production_remediation_closure_plan.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse plan: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "remediation_closure_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary attestation: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "remediation_closure_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked actions: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr9_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify manifest
  assert(manifest.track_id === "PR9", "Track ID is correct");
  assert(manifest.track_name === "Production Readiness Remediation Closure Plan", "Track Name is correct");
  assert(manifest.prior_dependency === "PR8", "Prior dependency is correct");

  // 4. Verify seal
  const requiredCert = "PR9 PRODUCTION READINESS REMEDIATION CLOSURE PLAN — ACCEPTED FOR REMEDIATION CLOSURE PLANNING ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 5. Verify closure plan entries (all 8 risk IDs)
  const requiredRiskIds = [
    "RSK-TLS-001",
    "RSK-AUTH-002",
    "RSK-AUD-003",
    "RSK-MUT-004",
    "RSK-SPL-005",
    "RSK-OBS-006",
    "RSK-REC-007",
    "RSK-CMP-008"
  ];

  const items = plan.remediation_closure_plan;
  assert(Array.isArray(items), "remediation_closure_plan is an array");
  
  requiredRiskIds.forEach(id => {
    const item = items.find((x: any) => x.risk_id === id);
    assert(!!item, `Plan contains entry for ${id}`);
    if (item) {
      assert(typeof item.closure_criteria === 'string' && item.closure_criteria.length > 0, `${id} has closure_criteria`);
      assert(Array.isArray(item.validation_commands) && item.validation_commands.length > 0, `${id} has validation_commands`);
      assert(Array.isArray(item.required_evidence_artifacts) && item.required_evidence_artifacts.length > 0, `${id} has required_evidence_artifacts`);
      assert(typeof item.owner_role === 'string' && item.owner_role.length > 0, `${id} has owner_role`);
      assert(item.production_gate_required === true, `${id} has production_gate_required as true`);
      assert(item.status === "PLANNED_NOT_EXECUTED", `${id} status is PLANNED_NOT_EXECUTED`);
    }
  });

  // 6. Verify blocked actions
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

  const blockedList = blocked.remediation_closure_blocked_actions;
  assert(Array.isArray(blockedList), "remediation_closure_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 7. Verify no file claims execution performed
  const allJsonContents = [manifest, plan, boundary, blocked, seal];
  allJsonContents.forEach(jsonObj => {
    const str = JSON.stringify(jsonObj);
    assert(!str.includes('"production_deployment": true') && 
           !str.includes('"performed": true') && 
           !str.includes('"git_push": true') && 
           !str.includes('"main_merge": true'), 
           "No file claims execution was performed");
  });

  // 8. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("PRODUCTION SECURITY CONTROL CLOSURE PLAN CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL CLOSURE PLAN CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionClosureTests();
