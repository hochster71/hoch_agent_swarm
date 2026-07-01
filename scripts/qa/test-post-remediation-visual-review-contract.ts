import * as fs from 'fs';
import * as path from 'path';

function runPostRemediationVisualReviewTests() {
  console.log("==================================================");
  console.log("POST-REMEDIATION VISUAL REVIEW VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p15Dir = path.join(baseDir, 'artifacts/post-remediation-visual-review/visual-control-plane-local-v1');

  const manifestFile = path.join(p15Dir, 'post_remediation_visual_review_manifest.json');
  const matrixFile = path.join(p15Dir, 'before_after_screenshot_comparison_matrix.json');
  const validationFile = path.join(p15Dir, 'applied_fix_visual_validation_matrix.json');
  const residualFile = path.join(p15Dir, 'residual_visual_findings_register.json');
  const notesFile = path.join(p15Dir, 'post_remediation_operator_review_notes.json');
  const attestationFile = path.join(p15Dir, 'visual_review_boundary_attestation.json');
  const decisionFile = path.join(p15Dir, 'post_remediation_decision_record.json');
  const sealFile = path.join(p15Dir, 'p15_final_seal.json');

  const p11Inv = path.join(baseDir, 'artifacts/ui-screenshot-evidence/visual-control-plane-local-v1/screenshot_inventory.json');
  const p14Inv = path.join(baseDir, 'artifacts/ui-polish-remediation-execution/visual-control-plane-local-v1/post_remediation_screenshot_inventory.json');

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
  assert(fs.existsSync(manifestFile), "post_remediation_visual_review_manifest.json exists");
  assert(fs.existsSync(matrixFile), "before_after_screenshot_comparison_matrix.json exists");
  assert(fs.existsSync(validationFile), "applied_fix_visual_validation_matrix.json exists");
  assert(fs.existsSync(residualFile), "residual_visual_findings_register.json exists");
  assert(fs.existsSync(notesFile), "post_remediation_operator_review_notes.json exists");
  assert(fs.existsSync(attestationFile), "visual_review_boundary_attestation.json exists");
  assert(fs.existsSync(decisionFile), "post_remediation_decision_record.json exists");
  assert(fs.existsSync(sealFile), "p15_final_seal.json exists");

  assert(fs.existsSync(p11Inv), "P11 screenshot inventory exists");
  assert(fs.existsSync(p14Inv), "P14 post-remediation screenshot inventory exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(matrixFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let matrix: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "post_remediation_visual_review_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p15_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  try {
    matrix = JSON.parse(fs.readFileSync(matrixFile, 'utf-8'));
    assert(true, "before_after_screenshot_comparison_matrix.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse comparison matrix: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P15_POST_REMEDIATION_EVIDENCE_REVIEW" || manifest.track === "P15_POST_REMEDIATION_VISUAL_EVIDENCE_REVIEW", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P15 POST-REMEDIATION VISUAL EVIDENCE REVIEW — ACCEPTED FOR LOCAL PREVIEW VISUAL REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // Verify matrix contains all 13 expected screenshots
  const expectedScreenshots = [
    "cockpit-overview.png",
    "runtime-health.png",
    "process-monitor.png",
    "evidence-status.png",
    "blocked-actions.png",
    "security-ato-readiness.png",
    "backend-binding-readiness.png",
    "frontend-runtime-readiness.png",
    "local-preview-release-candidate.png",
    "controlled-local-demo-readiness.png",
    "operator-acceptance-package.png",
    "local-preview-handoff-package.png",
    "final-local-preview-closure.png"
  ];

  const comparisonFiles = matrix.comparisons.map((c: any) => c.file);
  expectedScreenshots.forEach(name => {
    assert(comparisonFiles.includes(name), `before_after_screenshot_comparison_matrix.json references expected screenshot ${name}`);
  });

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("POST-REMEDIATION VISUAL REVIEW CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("POST-REMEDIATION VISUAL REVIEW CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runPostRemediationVisualReviewTests();
