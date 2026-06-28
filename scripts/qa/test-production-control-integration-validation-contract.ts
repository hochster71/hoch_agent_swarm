import * as fs from 'fs';
import * as path from 'path';

function runProductionValidationTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL VALIDATION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr6Dir = path.join(baseDir, 'artifacts/production-control-integration-validation/visual-control-plane-local-v1');

  const manifestFile = path.join(pr6Dir, 'production_validation_manifest.json');
  const boundaryFile = path.join(pr6Dir, 'production_validation_boundary_attestation.json');
  const blockedFile = path.join(pr6Dir, 'production_validation_blocked_actions.json');
  const sealFile = path.join(pr6Dir, 'pr6_final_seal.json');

  const pr5Manifest = path.join(baseDir, 'artifacts/production-control-implementation-execution/visual-control-plane-local-v1/production_execution_manifest.json');
  const validationPythonScript = path.join(baseDir, 'backend/production_hardening/test_scaffolding_validation.py');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR6 files exist
  assert(fs.existsSync(manifestFile), "production_validation_manifest.json exists");
  assert(fs.existsSync(boundaryFile), "production_validation_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "production_validation_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr6_final_seal.json exists");

  assert(fs.existsSync(pr5Manifest), "PR5 implementation execution manifest exists");
  assert(fs.existsSync(validationPythonScript), "test_scaffolding_validation.py exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_validation_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr6_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR6_PRODUCTION_SECURITY_CONTROL_INTEGRATION_VALIDATION", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR6 PRODUCTION SECURITY CONTROL INTEGRATION VALIDATION — ACCEPTED FOR CONTROL INTEGRATION VALIDATION ONLY";
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
    console.error("PRODUCTION SECURITY CONTROL VALIDATION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL VALIDATION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionValidationTests();
