import * as fs from 'fs';
import * as path from 'path';

function runOperatorGoNoGoDecisionTests() {
  console.log("==================================================");
  console.log("OPERATOR GO / NO-GO DECISION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p17Dir = path.join(baseDir, 'artifacts/operator-go-no-go-decision/visual-control-plane-local-v1');

  const manifestFile = path.join(p17Dir, 'operator_go_no_go_manifest.json');
  const matrixFile = path.join(p17Dir, 'decision_basis_traceability_matrix.json');
  const optionsFile = path.join(p17Dir, 'go_no_go_decision_options.json');
  const decisionFile = path.join(p17Dir, 'operator_decision_record.json');
  const boundaryFile = path.join(p17Dir, 'decision_boundary_attestation.json');
  const attestationFile = path.join(p17Dir, 'final_non_production_attestation.json');
  const riskFile = path.join(p17Dir, 'decision_risk_acceptance_register.json');
  const sealFile = path.join(p17Dir, 'p17_final_seal.json');

  const p16Seal = path.join(baseDir, 'artifacts/local-preview-final-candidate-seal/visual-control-plane-local-v1/p16_final_seal.json');
  const p15Residual = path.join(baseDir, 'artifacts/post-remediation-visual-review/visual-control-plane-local-v1/residual_visual_findings_register.json');

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
  assert(fs.existsSync(manifestFile), "operator_go_no_go_manifest.json exists");
  assert(fs.existsSync(matrixFile), "decision_basis_traceability_matrix.json exists");
  assert(fs.existsSync(optionsFile), "go_no_go_decision_options.json exists");
  assert(fs.existsSync(decisionFile), "operator_decision_record.json exists");
  assert(fs.existsSync(boundaryFile), "decision_boundary_attestation.json exists");
  assert(fs.existsSync(attestationFile), "final_non_production_attestation.json exists");
  assert(fs.existsSync(riskFile), "decision_risk_acceptance_register.json exists");
  assert(fs.existsSync(sealFile), "p17_final_seal.json exists");

  assert(fs.existsSync(p16Seal), "P16 final candidate seal exists");
  assert(fs.existsSync(p15Residual), "P15 residual findings register exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(decisionFile) || !fs.existsSync(riskFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let decision: any;
  let riskObj: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "operator_go_no_go_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p17_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  try {
    decision = JSON.parse(fs.readFileSync(decisionFile, 'utf-8'));
    assert(true, "operator_decision_record.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse decision record: ${e.message}`);
    process.exit(1);
  }

  try {
    riskObj = JSON.parse(fs.readFileSync(riskFile, 'utf-8'));
    assert(true, "decision_risk_acceptance_register.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse risk register: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P17_OPERATOR_GO_NO_GO_DECISION_RECORD", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P17 OPERATOR GO / NO-GO DECISION RECORD — ACCEPTED FOR LOCAL PREVIEW DECISION REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // Verify P15 residual findings register records no unresolved findings
  if (fs.existsSync(p15Residual)) {
    try {
      const p15Res = JSON.parse(fs.readFileSync(p15Residual, 'utf-8'));
      assert(p15Res.residual_issues && p15Res.residual_issues.length === 0, "P15 residual findings register has no unresolved accepted findings");
    } catch (e: any) {
      assert(false, `Failed to parse P15 residual findings register: ${e.message}`);
    }
  }

  // Verify decision record explicitly limits any GO decision to local preview review only
  assert(decision.operator_decision.selected_option === "GO", "Operator selected option is GO");
  assert(decision.operator_decision.authorized_scope === "local preview review only", "Operator authorized scope is limited to local preview review only");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("OPERATOR GO / NO-GO DECISION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("OPERATOR GO / NO-GO DECISION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runOperatorGoNoGoDecisionTests();
