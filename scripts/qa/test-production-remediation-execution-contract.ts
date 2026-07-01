import * as fs from 'fs';
import * as path from 'path';

function runProductionExecutionTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL EXECUTION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr10Dir = path.join(baseDir, 'artifacts/production-readiness-remediation-execution/visual-control-plane-local-v1');

  const manifestFile = path.join(pr10Dir, 'production_remediation_manifest.json');
  const evidenceFile = path.join(pr10Dir, 'remediation_execution_evidence.json');
  const boundaryFile = path.join(pr10Dir, 'remediation_boundary_attestation.json');
  const blockedFile = path.join(pr10Dir, 'remediation_blocked_actions.json');
  const sealFile = path.join(pr10Dir, 'pr10_final_seal.json');

  const pr9Manifest = path.join(baseDir, 'artifacts/production-readiness-remediation-closure-plan/visual-control-plane-local-v1/production_remediation_closure_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR10 files exist
  assert(fs.existsSync(manifestFile), "production_remediation_manifest.json exists");
  assert(fs.existsSync(evidenceFile), "remediation_execution_evidence.json exists");
  assert(fs.existsSync(boundaryFile), "remediation_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "remediation_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr10_final_seal.json exists");

  assert(fs.existsSync(pr9Manifest), "PR9 manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(evidenceFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let evidence: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_remediation_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    evidence = JSON.parse(fs.readFileSync(evidenceFile, 'utf-8'));
    assert(true, "remediation_execution_evidence.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse evidence: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "remediation_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "remediation_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr10_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify manifest details
  assert(manifest.track_id === "PR10", "Track ID is correct");
  assert(manifest.track_name === "Production Readiness Remediation Execution", "Track Name is correct");
  assert(manifest.prior_dependency === "PR9", "Prior dependency is correct");

  // 4. Verify seal
  const requiredCert = "PR10 PRODUCTION READINESS REMEDIATION EXECUTION — ACCEPTED FOR REMEDIATION EXECUTION ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 5. Verify evidence contains all 8 risk IDs with RESOLVED_LOCAL_PREVIEW status
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

  const items = evidence.remediation_execution_evidence;
  assert(Array.isArray(items), "remediation_execution_evidence is an array");
  requiredRiskIds.forEach(id => {
    const item = items.find((x: any) => x.risk_id === id);
    assert(!!item, `Evidence contains entry for ${id}`);
    if (item) {
      assert(item.status === "RESOLVED_LOCAL_PREVIEW", `${id} status is RESOLVED_LOCAL_PREVIEW`);
      assert(typeof item.validation_command === 'string' && item.validation_command.length > 0, `${id} has validation_command`);
      assert(typeof item.outcome === 'string' && item.outcome.length > 0, `${id} has validation outcome`);
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

  const blockedList = blocked.remediation_blocked_actions;
  assert(Array.isArray(blockedList), "remediation_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 7. Verify no file claims execution performed
  const allJsonContents = [manifest, evidence, boundary, blocked, seal];
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
    console.error("PRODUCTION SECURITY CONTROL EXECUTION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL EXECUTION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionExecutionTests();
