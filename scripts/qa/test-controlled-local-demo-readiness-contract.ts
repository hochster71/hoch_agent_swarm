import * as fs from 'fs';
import * as path from 'path';

function runControlledLocalDemoReadinessTests() {
  console.log("==================================================");
  console.log("VISUAL CONTROLLED LOCAL DEMO READINESS VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p7Dir = path.join(baseDir, 'artifacts/controlled-local-demo-readiness/visual-control-plane-local-v1');

  const manifestFile = path.join(p7Dir, 'controlled_local_demo_manifest.json');
  const runbookFile = path.join(p7Dir, 'local_demo_runbook.json');
  const fixtureFile = path.join(p7Dir, 'demo_fixture_inventory.json');
  const mapFile = path.join(p7Dir, 'read_only_demo_panel_map.json');
  const boundaryFile = path.join(p7Dir, 'demo_boundary_attestation.json');
  const policyFile = path.join(p7Dir, 'demo_no_execution_policy.json');
  const resultsFile = path.join(p7Dir, 'demo_validation_results.json');
  const sealFile = path.join(p7Dir, 'p7_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "controlled_local_demo_manifest.json exists");
  assert(fs.existsSync(runbookFile), "local_demo_runbook.json exists");
  assert(fs.existsSync(fixtureFile), "demo_fixture_inventory.json exists");
  assert(fs.existsSync(mapFile), "read_only_demo_panel_map.json exists");
  assert(fs.existsSync(boundaryFile), "demo_boundary_attestation.json exists");
  assert(fs.existsSync(policyFile), "demo_no_execution_policy.json exists");
  assert(fs.existsSync(resultsFile), "demo_validation_results.json exists");
  assert(fs.existsSync(sealFile), "p7_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "controlled_local_demo_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p7_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P7_CONTROLLED_LOCAL_DEMO_READINESS", "Track is P7_CONTROLLED_LOCAL_DEMO_READINESS");
  assert(manifest.local_demo_mode_active === true, "local_demo_mode_active is true");
  assert(manifest.sandboxed === true, "sandboxed is true");

  assert(seal.final_certification === "P7 CONTROLLED LOCAL DEMO READINESS — ACCEPTED FOR LOCAL PREVIEW DEMO REVIEW ONLY", "Final certification matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL CONTROLLED LOCAL DEMO READINESS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL CONTROLLED LOCAL DEMO READINESS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runControlledLocalDemoReadinessTests();
