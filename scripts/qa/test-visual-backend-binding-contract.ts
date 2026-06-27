import * as fs from 'fs';
import * as path from 'path';

function runBackendBindingTests() {
  console.log("==================================================");
  console.log("VISUAL BACKEND BINDING CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/backend-binding/visual-control-plane-local-v1.md');
  const configJsonFile = path.join(baseDir, 'config/visual_control_plane_backend_binding.json');

  const normalizedDir = path.join(baseDir, 'artifacts/backend-runtime-binding-readiness/visual-control-plane-local-v1');
  const manifestFile = path.join(normalizedDir, 'backend_runtime_binding_manifest.json');
  const mapFile = path.join(normalizedDir, 'backend_contract_map.json');
  const reportFile = path.join(normalizedDir, 'backend_readiness_report.json');
  const inventoryFile = path.join(normalizedDir, 'endpoint_inventory.json');
  const policyFile = path.join(normalizedDir, 'mutation_blocking_policy.json');
  const resultsFile = path.join(normalizedDir, 'contract_test_results.json');
  const sealFile = path.join(normalizedDir, 'p2_final_seal.json');

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
  assert(fs.existsSync(docFile), "docs/backend-binding/visual-control-plane-local-v1.md exists");
  assert(fs.existsSync(configJsonFile), "config/visual_control_plane_backend_binding.json exists");
  assert(fs.existsSync(manifestFile), "backend_runtime_binding_manifest.json exists");
  assert(fs.existsSync(mapFile), "backend_contract_map.json exists");
  assert(fs.existsSync(reportFile), "backend_readiness_report.json exists");
  assert(fs.existsSync(inventoryFile), "endpoint_inventory.json exists");
  assert(fs.existsSync(policyFile), "mutation_blocking_policy.json exists");
  assert(fs.existsSync(resultsFile), "contract_test_results.json exists");
  assert(fs.existsSync(sealFile), "p2_final_seal.json exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let seal: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_control_plane_backend_binding.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p2_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal JSON: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify config details
  assert(config.track === "P2_BACKEND_RUNTIME_BINDING_READINESS", "Track is P2_BACKEND_RUNTIME_BINDING_READINESS");
  assert(config.release_tag === "visual-control-plane-local-v1.0.0", "Release tag check");
  assert(config.integration_branch === "integration/visual-control-plane-local-v1", "Integration branch check");
  assert(config.binding_readiness_status === "READINESS_VERIFIED", "Binding readiness status check");
  assert(config.mutation_endpoints_enabled === false, "Mutation endpoints are disabled");

  // 4. Verify seal details
  assert(seal.phase === "P2_BACKEND_RUNTIME_BINDING_READINESS", "Seal phase check");
  assert(seal.final_certification === "P2 BACKEND RUNTIME BINDING READINESS — ACCEPTED FOR LOCAL PREVIEW READINESS REVIEW ONLY", "Final certification matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 5. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL BACKEND BINDING CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL BACKEND BINDING CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runBackendBindingTests();
