import * as fs from 'fs';
import * as path from 'path';

function runVisualReviewFindingsTests() {
  console.log("==================================================");
  console.log("VISUAL REVIEW FINDINGS VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p12Dir = path.join(baseDir, 'artifacts/visual-review-findings/visual-control-plane-local-v1');

  const manifestFile = path.join(p12Dir, 'visual_review_findings_manifest.json');
  const matrixFile = path.join(p12Dir, 'screenshot_review_matrix.json');
  const backlogFile = path.join(p12Dir, 'ui_polish_backlog_register.json');
  const classificationFile = path.join(p12Dir, 'backlog_classification_policy.json');
  const attestationFile = path.join(p12Dir, 'operator_visual_attestation.json');
  const memoFile = path.join(p12Dir, 'visual_review_findings_memo.md');
  const sealFile = path.join(p12Dir, 'p12_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "visual_review_findings_manifest.json exists");
  assert(fs.existsSync(matrixFile), "screenshot_review_matrix.json exists");
  assert(fs.existsSync(backlogFile), "ui_polish_backlog_register.json exists");
  assert(fs.existsSync(classificationFile), "backlog_classification_policy.json exists");
  assert(fs.existsSync(attestationFile), "operator_visual_attestation.json exists");
  assert(fs.existsSync(memoFile), "visual_review_findings_memo.md exists");
  assert(fs.existsSync(sealFile), "p12_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(memoFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "visual_review_findings_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p12_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P12_VISUAL_REVIEW_FINDINGS_UI_POLISH_BACKLOG", "Track is P12_VISUAL_REVIEW_FINDINGS_UI_POLISH_BACKLOG");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P12 VISUAL REVIEW FINDINGS / UI POLISH BACKLOG — ACCEPTED FOR LOCAL PREVIEW BACKLOG REVIEW ONLY";
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
    console.error("VISUAL REVIEW FINDINGS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL REVIEW FINDINGS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runVisualReviewFindingsTests();
