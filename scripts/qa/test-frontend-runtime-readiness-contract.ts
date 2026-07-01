import * as fs from 'fs';
import * as path from 'path';

function runFrontendRuntimeReadinessTests() {
  console.log("==================================================");
  console.log("VISUAL FRONTEND RUNTIME READINESS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p3Dir = path.join(baseDir, 'artifacts/frontend-runtime-readiness/visual-control-plane-local-v1');
  
  const manifestFile = path.join(p3Dir, 'frontend_runtime_readiness_manifest.json');
  const contractFile = path.join(p3Dir, 'frontend_panel_contract_map.json');
  const fixtureFile = path.join(p3Dir, 'frontend_fixture_inventory.json');
  const adapterFile = path.join(p3Dir, 'frontend_readonly_adapter_report.json');
  const policyFile = path.join(p3Dir, 'frontend_no_mutation_policy.json');
  const resultsFile = path.join(p3Dir, 'frontend_contract_test_results.json');
  const sealFile = path.join(p3Dir, 'p3_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "frontend_runtime_readiness_manifest.json exists");
  assert(fs.existsSync(contractFile), "frontend_panel_contract_map.json exists");
  assert(fs.existsSync(fixtureFile), "frontend_fixture_inventory.json exists");
  assert(fs.existsSync(adapterFile), "frontend_readonly_adapter_report.json exists");
  assert(fs.existsSync(policyFile), "frontend_no_mutation_policy.json exists");
  assert(fs.existsSync(resultsFile), "frontend_contract_test_results.json exists");
  assert(fs.existsSync(sealFile), "p3_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "frontend_runtime_readiness_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p3_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P3_FRONTEND_RUNTIME_READINESS", "Track is P3_FRONTEND_RUNTIME_READINESS");
  assert(manifest.release_tag === "visual-control-plane-local-v1.0.0", "Release tag is correct");
  assert(manifest.safety_status === "LOCAL_PREVIEW_ONLY", "Safety status is LOCAL_PREVIEW_ONLY");
  assert(manifest.deployment_performed === false, "Deployment performed check");

  assert(seal.final_certification === "P3 FRONTEND RUNTIME READINESS — ACCEPTED FOR LOCAL PREVIEW READINESS REVIEW ONLY", "Final certification matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL FRONTEND RUNTIME READINESS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL FRONTEND RUNTIME READINESS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runFrontendRuntimeReadinessTests();
