import * as fs from 'fs';
import * as path from 'path';

function runProductionValidationTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL VALIDATION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr11Dir = path.join(baseDir, 'artifacts/production-readiness-remediation-validation/visual-control-plane-local-v1');

  const manifestFile = path.join(pr11Dir, 'production_validation_manifest.json');
  const riskFile = path.join(pr11Dir, 'remediation_validation_residual_risk.json');
  const boundaryFile = path.join(pr11Dir, 'validation_boundary_attestation.json');
  const blockedFile = path.join(pr11Dir, 'validation_blocked_actions.json');
  const sealFile = path.join(pr11Dir, 'pr11_final_seal.json');

  const pr10Manifest = path.join(baseDir, 'artifacts/production-readiness-remediation-execution/visual-control-plane-local-v1/production_remediation_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR11 files exist
  assert(fs.existsSync(manifestFile), "production_validation_manifest.json exists");
  assert(fs.existsSync(riskFile), "remediation_validation_residual_risk.json exists");
  assert(fs.existsSync(boundaryFile), "validation_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "validation_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr11_final_seal.json exists");

  assert(fs.existsSync(pr10Manifest), "PR10 manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(riskFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let risk: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_validation_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    risk = JSON.parse(fs.readFileSync(riskFile, 'utf-8'));
    assert(true, "remediation_validation_residual_risk.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse risk: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "validation_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "validation_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr11_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR11_PRODUCTION_READINESS_REMEDIATION_VALIDATION_RESIDUAL_RISK_REVIEW", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR11 PRODUCTION READINESS REMEDIATION VALIDATION & RESIDUAL RISK REVIEW — ACCEPTED FOR VALIDATION & RESIDUAL RISK REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify risk reviews contains all 8 risk IDs with VALIDATED_LOCAL_TESTS_PASS status
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

  const items = risk.remediation_validation_residual_risk;
  assert(Array.isArray(items), "remediation_validation_residual_risk is an array");
  requiredRiskIds.forEach(id => {
    const item = items.find((x: any) => x.risk_id === id);
    assert(!!item, `Residual risk contains entry for ${id}`);
    if (item) {
      assert(item.validation_status === "VALIDATED_LOCAL_TESTS_PASS", `${id} validation_status is VALIDATED_LOCAL_TESTS_PASS`);
      assert(typeof item.validation_summary === 'string' && item.validation_summary.length > 0, `${id} has validation_summary`);
      assert(typeof item.residual_risk_description === 'string' && item.residual_risk_description.length > 0, `${id} has residual_risk_description`);
      assert(item.residual_severity === "LOW" || item.residual_severity === "NONE", `${id} residual_severity is valid`);
    }
  });

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

  const blockedList = blocked.validation_blocked_actions;
  assert(Array.isArray(blockedList), "validation_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 6. Verify no file claims execution performed
  const allJsonContents = [manifest, risk, boundary, blocked, seal];
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
    console.error("PRODUCTION SECURITY CONTROL VALIDATION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL VALIDATION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionValidationTests();
