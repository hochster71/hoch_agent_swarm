import * as fs from 'fs';
import * as path from 'path';

function runImmutableLocalPreviewLockTests() {
  console.log("==================================================");
  console.log("IMMUTABLE LOCAL PREVIEW LOCK VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p19Dir = path.join(baseDir, 'artifacts/immutable-local-preview-lock/visual-control-plane-local-v1');

  const manifestFile = path.join(p19Dir, 'immutable_lock_manifest.json');
  const mapFile = path.join(p19Dir, 'evidence_lock_directory_map.json');
  const checksumsFile = path.join(p19Dir, 'immutable_archive_checksum_register.json');
  const boundaryFile = path.join(p19Dir, 'lock_boundary_attestation.json');
  const blockedFile = path.join(p19Dir, 'lock_blocked_actions_register.json');
  const sealFile = path.join(p19Dir, 'p19_final_seal.json');

  const p18Manifest = path.join(baseDir, 'artifacts/local-preview-review-package-export/visual-control-plane-local-v1/review_package_export_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify P19 files exist
  assert(fs.existsSync(manifestFile), "immutable_lock_manifest.json exists");
  assert(fs.existsSync(mapFile), "evidence_lock_directory_map.json exists");
  assert(fs.existsSync(checksumsFile), "immutable_archive_checksum_register.json exists");
  assert(fs.existsSync(boundaryFile), "lock_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "lock_blocked_actions_register.json exists");
  assert(fs.existsSync(sealFile), "p19_final_seal.json exists");

  assert(fs.existsSync(p18Manifest), "P18 export manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(checksumsFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "immutable_lock_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p19_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P19_IMMUTABLE_LOCAL_PREVIEW_LOCK", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P19 IMMUTABLE LOCAL PREVIEW ARCHIVE CHECKSUM / FINAL EVIDENCE LOCK — ACCEPTED FOR IMMUTABLE LOCAL PREVIEW LOCK ONLY";
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
    console.error("IMMUTABLE LOCAL PREVIEW LOCK CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("IMMUTABLE LOCAL PREVIEW LOCK CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runImmutableLocalPreviewLockTests();
