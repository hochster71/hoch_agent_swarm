import * as fs from 'fs';
import * as path from 'path';

function runProductionClosureTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL CLOSURE PLAN VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr9Dir = path.join(baseDir, 'artifacts/production-readiness-remediation-closure-plan/visual-control-plane-local-v1');

  const manifestFile = path.join(pr9Dir, 'production_closure_manifest.json');
  const planFile = path.join(pr9Dir, 'production_remediation_closure_plan.json');
  const boundaryFile = path.join(pr9Dir, 'closure_boundary_attestation.json');
  const blockedFile = path.join(pr9Dir, 'closure_blocked_actions.json');
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
  assert(fs.existsSync(manifestFile), "production_closure_manifest.json exists");
  assert(fs.existsSync(planFile), "production_remediation_closure_plan.json exists");
  assert(fs.existsSync(boundaryFile), "closure_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "closure_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr9_final_seal.json exists");

  assert(fs.existsSync(pr8Manifest), "PR8 risk manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(planFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_closure_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr9_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR9_PRODUCTION_READINESS_REMEDIATION_CLOSURE_PLAN", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR9 PRODUCTION READINESS REMEDIATION CLOSURE PLAN — ACCEPTED FOR REMEDIATION CLOSURE PLANNING ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
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
