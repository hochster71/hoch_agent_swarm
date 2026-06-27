import * as fs from 'fs';
import * as path from 'path';

function runFinalLocalPreviewClosureTests() {
  console.log("==================================================");
  console.log("VISUAL FINAL LOCAL PREVIEW CLOSURE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p10Dir = path.join(baseDir, 'artifacts/final-local-preview-closure/visual-control-plane-local-v1');

  const manifestFile = path.join(p10Dir, 'final_local_preview_closure_manifest.json');
  const summaryFile = path.join(p10Dir, 'final_track_acceptance_summary.json');
  const matrixFile = path.join(p10Dir, 'final_evidence_traceability_matrix.json');
  const boundaryFile = path.join(p10Dir, 'final_boundary_and_blocked_actions_summary.json');
  const riskFile = path.join(p10Dir, 'final_risk_and_limitations_summary.json');
  const recommendationFile = path.join(p10Dir, 'final_human_review_recommendation.json');
  const memoFile = path.join(p10Dir, 'final_local_preview_closure_memo.md');
  const sealFile = path.join(p10Dir, 'p10_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "final_local_preview_closure_manifest.json exists");
  assert(fs.existsSync(summaryFile), "final_track_acceptance_summary.json exists");
  assert(fs.existsSync(matrixFile), "final_evidence_traceability_matrix.json exists");
  assert(fs.existsSync(boundaryFile), "final_boundary_and_blocked_actions_summary.json exists");
  assert(fs.existsSync(riskFile), "final_risk_and_limitations_summary.json exists");
  assert(fs.existsSync(recommendationFile), "final_human_review_recommendation.json exists");
  assert(fs.existsSync(memoFile), "final_local_preview_closure_memo.md exists");
  assert(fs.existsSync(sealFile), "p10_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(memoFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "final_local_preview_closure_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p10_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P10_FINAL_LOCAL_PREVIEW_CLOSURE_MEMO", "Track is P10_FINAL_LOCAL_PREVIEW_CLOSURE_MEMO");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P10 FINAL LOCAL PREVIEW CLOSURE MEMO — ACCEPTED FOR LOCAL PREVIEW CLOSURE REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  const memoContent = fs.readFileSync(memoFile, 'utf-8');
  assert(memoContent.includes(requiredCert), "Markdown memo includes required certification wording");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL FINAL LOCAL PREVIEW CLOSURE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL FINAL LOCAL PREVIEW CLOSURE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runFinalLocalPreviewClosureTests();
