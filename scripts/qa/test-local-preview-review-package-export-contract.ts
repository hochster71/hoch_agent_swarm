import * as fs from 'fs';
import * as path from 'path';

function runLocalPreviewReviewPackageExportTests() {
  console.log("==================================================");
  console.log("LOCAL PREVIEW REVIEW PACKAGE EXPORT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p18Dir = path.join(baseDir, 'artifacts/local-preview-review-package-export/visual-control-plane-local-v1');

  const manifestFile = path.join(p18Dir, 'review_package_export_manifest.json');
  const mapFile = path.join(p18Dir, 'exported_evidence_directory_map.json');
  const checksumsFile = path.join(p18Dir, 'exported_file_checksums.json');
  const boundaryFile = path.join(p18Dir, 'export_package_boundary_attestation.json');
  const blockedFile = path.join(p18Dir, 'export_blocked_actions_register.json');
  const sealFile = path.join(p18Dir, 'p18_final_seal.json');

  const p17Decision = path.join(baseDir, 'artifacts/operator-go-no-go-decision/visual-control-plane-local-v1/operator_decision_record.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify P18 files exist
  assert(fs.existsSync(manifestFile), "review_package_export_manifest.json exists");
  assert(fs.existsSync(mapFile), "exported_evidence_directory_map.json exists");
  assert(fs.existsSync(checksumsFile), "exported_file_checksums.json exists");
  assert(fs.existsSync(boundaryFile), "export_package_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "export_blocked_actions_register.json exists");
  assert(fs.existsSync(sealFile), "p18_final_seal.json exists");

  assert(fs.existsSync(p17Decision), "P17 operator decision record exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(checksumsFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let checksums: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "review_package_export_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p18_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  try {
    checksums = JSON.parse(fs.readFileSync(checksumsFile, 'utf-8'));
    assert(true, "exported_file_checksums.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse checksums: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P18_LOCAL_PREVIEW_REVIEW_PACKAGE_EXPORT", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P18 LOCAL PREVIEW REVIEW PACKAGE EXPORT — ACCEPTED FOR LOCAL PREVIEW REVIEW PACKAGE EXPORT ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // Verify all prior seals exist on filesystem
  Object.keys(checksums.prior_seals).forEach((trackKey: string) => {
    const relativePath = checksums.prior_seals[trackKey];
    const absPath = path.join(baseDir, relativePath);
    assert(fs.existsSync(absPath), `Track ${trackKey} seal exists: ${relativePath}`);
  });

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("LOCAL PREVIEW REVIEW PACKAGE EXPORT CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("LOCAL PREVIEW REVIEW PACKAGE EXPORT CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalPreviewReviewPackageExportTests();
