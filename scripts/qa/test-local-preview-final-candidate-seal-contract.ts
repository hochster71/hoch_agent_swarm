import * as fs from 'fs';
import * as path from 'path';

function runLocalPreviewFinalCandidateSealTests() {
  console.log("==================================================");
  console.log("LOCAL PREVIEW FINAL CANDIDATE SEAL VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p16Dir = path.join(baseDir, 'artifacts/local-preview-final-candidate-seal/visual-control-plane-local-v1');

  const manifestFile = path.join(p16Dir, 'final_candidate_seal_manifest.json');
  const indexFile = path.join(p16Dir, 'full_track_acceptance_index.json');
  const inventoryFile = path.join(p16Dir, 'final_evidence_bundle_inventory.json');
  const rollupFile = path.join(p16Dir, 'final_qa_ci_rollup_report.json');
  const summaryFile = path.join(p16Dir, 'final_visual_evidence_summary.json');
  const boundaryFile = path.join(p16Dir, 'final_boundary_attestation.json');
  const blockedFile = path.join(p16Dir, 'final_blocked_actions_attestation.json');
  const riskFile = path.join(p16Dir, 'final_residual_risk_register.json');
  const decisionFile = path.join(p16Dir, 'final_operator_decision_record.json');
  const sealFile = path.join(p16Dir, 'p16_final_seal.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify P16 files exist
  assert(fs.existsSync(manifestFile), "final_candidate_seal_manifest.json exists");
  assert(fs.existsSync(indexFile), "full_track_acceptance_index.json exists");
  assert(fs.existsSync(inventoryFile), "final_evidence_bundle_inventory.json exists");
  assert(fs.existsSync(rollupFile), "final_qa_ci_rollup_report.json exists");
  assert(fs.existsSync(summaryFile), "final_visual_evidence_summary.json exists");
  assert(fs.existsSync(boundaryFile), "final_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "final_blocked_actions_attestation.json exists");
  assert(fs.existsSync(riskFile), "final_residual_risk_register.json exists");
  assert(fs.existsSync(decisionFile), "final_operator_decision_record.json exists");
  assert(fs.existsSync(sealFile), "p16_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(inventoryFile) || !fs.existsSync(riskFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let inventory: any;
  let risk: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "final_candidate_seal_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p16_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  try {
    inventory = JSON.parse(fs.readFileSync(inventoryFile, 'utf-8'));
    assert(true, "final_evidence_bundle_inventory.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse inventory: ${e.message}`);
    process.exit(1);
  }

  try {
    risk = JSON.parse(fs.readFileSync(riskFile, 'utf-8'));
    assert(true, "final_residual_risk_register.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse risk register: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P16_LOCAL_PREVIEW_FINAL_CANDIDATE_SEAL", "Track is P16_LOCAL_PREVIEW_FINAL_CANDIDATE_SEAL");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P16 LOCAL PREVIEW FINAL CANDIDATE SEAL — ACCEPTED FOR LOCAL PREVIEW FINAL REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // Verify all referenced directories in inventory exist
  inventory.directories.forEach((dir: string) => {
    const absPath = path.join(baseDir, dir);
    assert(fs.existsSync(absPath), `Referenced evidence directory exists: ${dir}`);
  });

  // Verify P11 and P14 screenshot inventories exist
  const p11Inv = path.join(baseDir, 'artifacts/ui-screenshot-evidence/visual-control-plane-local-v1/screenshot_inventory.json');
  const p14Inv = path.join(baseDir, 'artifacts/ui-polish-remediation-execution/visual-control-plane-local-v1/post_remediation_screenshot_inventory.json');
  assert(fs.existsSync(p11Inv), "P11 screenshot inventory exists");
  assert(fs.existsSync(p14Inv), "P14 post-remediation screenshot inventory exists");

  // Verify P15 residual findings register exists and has no unresolved accepted findings
  const p15Residual = path.join(baseDir, 'artifacts/post-remediation-visual-review/visual-control-plane-local-v1/residual_visual_findings_register.json');
  assert(fs.existsSync(p15Residual), "P15 residual findings register exists");
  if (fs.existsSync(p15Residual)) {
    try {
      const p15ResObj = JSON.parse(fs.readFileSync(p15Residual, 'utf-8'));
      assert(p15ResObj.residual_issues && p15ResObj.residual_issues.length === 0, "No unresolved accepted findings in P15 residual findings register");
    } catch (e: any) {
      assert(false, `Failed to parse P15 residual findings register: ${e.message}`);
    }
  }

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("LOCAL PREVIEW FINAL CANDIDATE SEAL CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("LOCAL PREVIEW FINAL CANDIDATE SEAL CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalPreviewFinalCandidateSealTests();
