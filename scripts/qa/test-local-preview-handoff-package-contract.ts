import * as fs from 'fs';
import * as path from 'path';

function runLocalPreviewHandoffPackageTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL PREVIEW HANDOFF PACKAGE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p9Dir = path.join(baseDir, 'artifacts/local-preview-handoff-package/visual-control-plane-local-v1');

  const manifestFile = path.join(p9Dir, 'local_preview_handoff_manifest.json');
  const indexFile = path.join(p9Dir, 'accepted_track_handoff_index.json');
  const inventoryFile = path.join(p9Dir, 'evidence_archive_inventory.json');
  const summaryFile = path.join(p9Dir, 'operator_review_handoff_summary.json');
  const instructionsFile = path.join(p9Dir, 'local_preview_review_instructions.json');
  const attestationFile = path.join(p9Dir, 'archive_boundary_attestation.json');
  const registerFile = path.join(p9Dir, 'handoff_risk_and_limitations_register.json');
  const sealFile = path.join(p9Dir, 'p9_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "local_preview_handoff_manifest.json exists");
  assert(fs.existsSync(indexFile), "accepted_track_handoff_index.json exists");
  assert(fs.existsSync(inventoryFile), "evidence_archive_inventory.json exists");
  assert(fs.existsSync(summaryFile), "operator_review_handoff_summary.json exists");
  assert(fs.existsSync(instructionsFile), "local_preview_review_instructions.json exists");
  assert(fs.existsSync(attestationFile), "archive_boundary_attestation.json exists");
  assert(fs.existsSync(registerFile), "handoff_risk_and_limitations_register.json exists");
  assert(fs.existsSync(sealFile), "p9_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "local_preview_handoff_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p9_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P9_LOCAL_PREVIEW_ARCHIVE_HANDOFF_PACKAGE", "Track is P9_LOCAL_PREVIEW_ARCHIVE_HANDOFF_PACKAGE");
  assert(manifest.handoff_status === "READY_FOR_HANDOFF", "Handoff status is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  assert(seal.final_certification === "P9 LOCAL PREVIEW ARCHIVE / HANDOFF PACKAGE — ACCEPTED FOR LOCAL PREVIEW HANDOFF REVIEW ONLY", "Final certification matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL PREVIEW HANDOFF PACKAGE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL PREVIEW HANDOFF PACKAGE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalPreviewHandoffPackageTests();
