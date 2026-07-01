import * as fs from 'fs';
import * as path from 'path';

function runProductionReadinessTests() {
  console.log("==================================================");
  console.log("PRODUCTION READINESS AUTHORIZATION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr1Dir = path.join(baseDir, 'artifacts/production-readiness-authorization/visual-control-plane-local-v1');

  const manifestFile = path.join(pr1Dir, 'production_readiness_manifest.json');
  const gapFile = path.join(pr1Dir, 'production_gap_analysis.json');
  const boundaryFile = path.join(pr1Dir, 'production_readiness_boundary_attestation.json');
  const blockedFile = path.join(pr1Dir, 'production_readiness_blocked_actions.json');
  const sealFile = path.join(pr1Dir, 'pr1_final_seal.json');

  const p20Manifest = path.join(baseDir, 'artifacts/terminal-local-preview-closure/visual-control-plane-local-v1/terminal_closure_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR1 files exist
  assert(fs.existsSync(manifestFile), "production_readiness_manifest.json exists");
  assert(fs.existsSync(gapFile), "production_gap_analysis.json exists");
  assert(fs.existsSync(boundaryFile), "production_readiness_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "production_readiness_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr1_final_seal.json exists");

  assert(fs.existsSync(p20Manifest), "P20 terminal closure manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(gapFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_readiness_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr1_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR1_PRODUCTION_READINESS_AUTHORIZATION", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR1 PRODUCTION READINESS AUTHORIZATION — ACCEPTED FOR PRODUCTION READINESS GAP ANALYSIS ONLY";
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
    console.error("PRODUCTION READINESS AUTHORIZATION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION READINESS AUTHORIZATION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionReadinessTests();
