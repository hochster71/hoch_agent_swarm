import * as fs from 'fs';
import * as path from 'path';

function runOperatorAcceptancePackageTests() {
  console.log("==================================================");
  console.log("VISUAL OPERATOR ACCEPTANCE PACKAGE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p8Dir = path.join(baseDir, 'artifacts/operator-acceptance-package/visual-control-plane-local-v1');

  const manifestFile = path.join(p8Dir, 'operator_acceptance_manifest.json');
  const crosswalkFile = path.join(p8Dir, 'accepted_track_crosswalk.json');
  const humanChecklistFile = path.join(p8Dir, 'human_review_checklist.json');
  const demoChecklistFile = path.join(p8Dir, 'demo_review_checklist.json');
  const matrixFile = path.join(p8Dir, 'operator_decision_matrix.json');
  const riskFile = path.join(p8Dir, 'risk_acknowledgement_register.json');
  const attestationFile = path.join(p8Dir, 'blocked_actions_operator_attestation.json');
  const sealFile = path.join(p8Dir, 'p8_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "operator_acceptance_manifest.json exists");
  assert(fs.existsSync(crosswalkFile), "accepted_track_crosswalk.json exists");
  assert(fs.existsSync(humanChecklistFile), "human_review_checklist.json exists");
  assert(fs.existsSync(demoChecklistFile), "demo_review_checklist.json exists");
  assert(fs.existsSync(matrixFile), "operator_decision_matrix.json exists");
  assert(fs.existsSync(riskFile), "risk_acknowledgement_register.json exists");
  assert(fs.existsSync(attestationFile), "blocked_actions_operator_attestation.json exists");
  assert(fs.existsSync(sealFile), "p8_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "operator_acceptance_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p8_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P8_HUMAN_REVIEW_OPERATOR_ACCEPTANCE_PACKAGE", "Track is P8_HUMAN_REVIEW_OPERATOR_ACCEPTANCE_PACKAGE");
  assert(manifest.scope === "local_preview_human_review_only", "Scope is correct");

  assert(seal.final_certification === "P8 HUMAN REVIEW / OPERATOR ACCEPTANCE PACKAGE — ACCEPTED FOR LOCAL PREVIEW HUMAN REVIEW ONLY", "Final certification matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL OPERATOR ACCEPTANCE PACKAGE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL OPERATOR ACCEPTANCE PACKAGE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runOperatorAcceptancePackageTests();
