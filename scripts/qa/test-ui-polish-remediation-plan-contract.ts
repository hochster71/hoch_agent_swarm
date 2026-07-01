import * as fs from 'fs';
import * as path from 'path';

function runUiPolishRemediationPlanTests() {
  console.log("==================================================");
  console.log("VISUAL UI POLISH REMEDIATION PLAN VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p13Dir = path.join(baseDir, 'artifacts/ui-polish-remediation-plan/visual-control-plane-local-v1');

  const manifestFile = path.join(p13Dir, 'ui_polish_remediation_manifest.json');
  const matrixFile = path.join(p13Dir, 'p12_backlog_to_fix_traceability_matrix.json');
  const registerFile = path.join(p13Dir, 'proposed_ui_fix_register.json');
  const modelFile = path.join(p13Dir, 'remediation_priority_and_risk_model.json');
  const validationFile = path.join(p13Dir, 'remediation_validation_plan.json');
  const attestationFile = path.join(p13Dir, 'remediation_boundary_attestation.json');
  const decisionFile = path.join(p13Dir, 'operator_remediation_decision_matrix.json');
  const sealFile = path.join(p13Dir, 'p13_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "ui_polish_remediation_manifest.json exists");
  assert(fs.existsSync(matrixFile), "p12_backlog_to_fix_traceability_matrix.json exists");
  assert(fs.existsSync(registerFile), "proposed_ui_fix_register.json exists");
  assert(fs.existsSync(modelFile), "remediation_priority_and_risk_model.json exists");
  assert(fs.existsSync(validationFile), "remediation_validation_plan.json exists");
  assert(fs.existsSync(attestationFile), "remediation_boundary_attestation.json exists");
  assert(fs.existsSync(decisionFile), "operator_remediation_decision_matrix.json exists");
  assert(fs.existsSync(sealFile), "p13_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "ui_polish_remediation_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p13_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P13_LOCAL_PREVIEW_UI_POLISH_REMEDIATION_PLAN", "Track is P13_LOCAL_PREVIEW_UI_POLISH_REMEDIATION_PLAN");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P13 LOCAL PREVIEW UI POLISH REMEDIATION PLAN — ACCEPTED FOR LOCAL PREVIEW REMEDIATION PLANNING ONLY";
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
    console.error("VISUAL UI POLISH REMEDIATION PLAN CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL UI POLISH REMEDIATION PLAN CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runUiPolishRemediationPlanTests();
