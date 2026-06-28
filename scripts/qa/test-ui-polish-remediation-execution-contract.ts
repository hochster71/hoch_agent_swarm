import * as fs from 'fs';
import * as path from 'path';

function runUiPolishRemediationExecutionTests() {
  console.log("==================================================");
  console.log("VISUAL UI POLISH REMEDIATION EXECUTION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p14Dir = path.join(baseDir, 'artifacts/ui-polish-remediation-execution/visual-control-plane-local-v1');

  const manifestFile = path.join(p14Dir, 'ui_polish_execution_manifest.json');
  const matrixFile = path.join(p14Dir, 'applied_fix_traceability_matrix.json');
  const inventoryFile = path.join(p14Dir, 'changed_file_inventory.json');
  const changeAttestationFile = path.join(p14Dir, 'visual_only_change_attestation.json');
  const screenshotInvFile = path.join(p14Dir, 'post_remediation_screenshot_inventory.json');
  const validationResultsFile = path.join(p14Dir, 'remediation_validation_results.json');
  const attestationFile = path.join(p14Dir, 'remediation_boundary_attestation.json');
  const sealFile = path.join(p14Dir, 'p14_final_seal.json');
  const screenshotsDir = path.join(p14Dir, 'screenshots');

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
  assert(fs.existsSync(manifestFile), "ui_polish_execution_manifest.json exists");
  assert(fs.existsSync(matrixFile), "applied_fix_traceability_matrix.json exists");
  assert(fs.existsSync(inventoryFile), "changed_file_inventory.json exists");
  assert(fs.existsSync(changeAttestationFile), "visual_only_change_attestation.json exists");
  assert(fs.existsSync(screenshotInvFile), "post_remediation_screenshot_inventory.json exists");
  assert(fs.existsSync(validationResultsFile), "remediation_validation_results.json exists");
  assert(fs.existsSync(attestationFile), "remediation_boundary_attestation.json exists");
  assert(fs.existsSync(sealFile), "p14_final_seal.json exists");
  assert(fs.existsSync(screenshotsDir), "screenshots directory exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "ui_polish_execution_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p14_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P14_LOCAL_PREVIEW_UI_POLISH_REMEDIATION_EXECUTION", "Track is P14_LOCAL_PREVIEW_UI_POLISH_REMEDIATION_EXECUTION");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P14 LOCAL PREVIEW UI POLISH REMEDIATION EXECUTION — ACCEPTED FOR LOCAL PREVIEW UI POLISH REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // Verify screenshots content
  if (fs.existsSync(screenshotsDir)) {
    const files = fs.readdirSync(screenshotsDir);
    const pngs = files.filter(f => f.endsWith('.png'));
    assert(pngs.length > 0, `Screenshots folder contains files (${pngs.length} found)`);
  } else {
    assert(false, "Screenshots folder does not exist");
  }

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL UI POLISH REMEDIATION EXECUTION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL UI POLISH REMEDIATION EXECUTION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runUiPolishRemediationExecutionTests();
