import * as fs from 'fs';
import * as path from 'path';

function runProductionRequirementsTests() {
  console.log("==================================================");
  console.log("PRODUCTION REQUIREMENTS BASELINE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr2Dir = path.join(baseDir, 'artifacts/production-requirements-baseline/visual-control-plane-local-v1');

  const manifestFile = path.join(pr2Dir, 'production_requirements_manifest.json');
  const baselineFile = path.join(pr2Dir, 'production_requirements_baseline.json');
  const boundaryFile = path.join(pr2Dir, 'requirements_boundary_attestation.json');
  const blockedFile = path.join(pr2Dir, 'requirements_blocked_actions.json');
  const sealFile = path.join(pr2Dir, 'pr2_final_seal.json');

  const pr1Manifest = path.join(baseDir, 'artifacts/production-readiness-authorization/visual-control-plane-local-v1/production_readiness_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR2 files exist
  assert(fs.existsSync(manifestFile), "production_requirements_manifest.json exists");
  assert(fs.existsSync(baselineFile), "production_requirements_baseline.json exists");
  assert(fs.existsSync(boundaryFile), "requirements_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "requirements_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr2_final_seal.json exists");

  assert(fs.existsSync(pr1Manifest), "PR1 gap analysis manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(baselineFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_requirements_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr2_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR2_PRODUCTION_REQUIREMENTS_BASELINE", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR2 PRODUCTION CONTROL PLANE REQUIREMENTS BASELINE — ACCEPTED FOR PRODUCTION REQUIREMENTS BASELINE ONLY";
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
    console.error("PRODUCTION REQUIREMENTS BASELINE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION REQUIREMENTS BASELINE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionRequirementsTests();
