import * as fs from 'fs';
import * as path from 'path';

function runProductionControlPlanTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL PLAN VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr4Dir = path.join(baseDir, 'artifacts/production-control-implementation-plan/visual-control-plane-local-v1');

  const manifestFile = path.join(pr4Dir, 'production_implementation_plan_manifest.json');
  const planFile = path.join(pr4Dir, 'production_control_implementation_plan.json');
  const boundaryFile = path.join(pr4Dir, 'plan_boundary_attestation.json');
  const blockedFile = path.join(pr4Dir, 'plan_blocked_actions.json');
  const sealFile = path.join(pr4Dir, 'pr4_final_seal.json');

  const pr3Manifest = path.join(baseDir, 'artifacts/production-architecture-design/visual-control-plane-local-v1/production_architecture_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR4 files exist
  assert(fs.existsSync(manifestFile), "production_implementation_plan_manifest.json exists");
  assert(fs.existsSync(planFile), "production_control_implementation_plan.json exists");
  assert(fs.existsSync(boundaryFile), "plan_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "plan_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr4_final_seal.json exists");

  assert(fs.existsSync(pr3Manifest), "PR3 architecture manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(planFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_implementation_plan_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr4_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR4_PRODUCTION_CONTROL_IMPLEMENTATION_PLAN", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR4 PRODUCTION SECURITY CONTROL IMPLEMENTATION PLAN — ACCEPTED FOR PRODUCTION SECURITY CONTROL IMPLEMENTATION PLAN ONLY";
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
    console.error("PRODUCTION SECURITY CONTROL PLAN CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL PLAN CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionControlPlanTests();
