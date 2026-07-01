import * as fs from 'fs';
import * as path from 'path';

function runLocalPreviewReleaseCandidateTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL PREVIEW RELEASE CANDIDATE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p6Dir = path.join(baseDir, 'artifacts/local-preview-release-candidate/visual-control-plane-local-v1');

  const manifestFile = path.join(p6Dir, 'local_preview_release_candidate_manifest.json');
  const indexFile = path.join(p6Dir, 'accepted_track_index.json');
  const inventoryFile = path.join(p6Dir, 'evidence_bundle_inventory.json');
  const rollupFile = path.join(p6Dir, 'qa_ci_rollup_report.json');
  const boundaryFile = path.join(p6Dir, 'local_preview_boundary_report.json');
  const attestationFile = path.join(p6Dir, 'blocked_actions_attestation.json');
  const riskFile = path.join(p6Dir, 'release_candidate_risk_register.json');
  const sealFile = path.join(p6Dir, 'p6_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "local_preview_release_candidate_manifest.json exists");
  assert(fs.existsSync(indexFile), "accepted_track_index.json exists");
  assert(fs.existsSync(inventoryFile), "evidence_bundle_inventory.json exists");
  assert(fs.existsSync(rollupFile), "qa_ci_rollup_report.json exists");
  assert(fs.existsSync(boundaryFile), "local_preview_boundary_report.json exists");
  assert(fs.existsSync(attestationFile), "blocked_actions_attestation.json exists");
  assert(fs.existsSync(riskFile), "release_candidate_risk_register.json exists");
  assert(fs.existsSync(sealFile), "p6_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "local_preview_release_candidate_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p6_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P6_LOCAL_PREVIEW_RELEASE_CANDIDATE", "Track is P6_LOCAL_PREVIEW_RELEASE_CANDIDATE");
  assert(manifest.release_candidate_id === "RC-visual-control-plane-local-v1.0.0", "Release candidate ID is correct");
  assert(manifest.boundary_enforced === "LOCAL_PREVIEW_ONLY", "Boundary enforced is LOCAL_PREVIEW_ONLY");
  assert(manifest.deployment_performed === false, "Deployment performed check");

  assert(seal.final_certification === "P6 LOCAL PREVIEW RELEASE CANDIDATE — ACCEPTED FOR LOCAL PREVIEW REVIEW ONLY", "Final certification matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL PREVIEW RELEASE CANDIDATE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL PREVIEW RELEASE CANDIDATE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalPreviewReleaseCandidateTests();
