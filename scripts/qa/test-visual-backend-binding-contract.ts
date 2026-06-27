import * as fs from 'fs';
import * as path from 'path';

function runBackendBindingTests() {
  console.log("==================================================");
  console.log("VISUAL BACKEND BINDING CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/backend-binding/visual-control-plane-local-v1.md');
  const configJsonFile = path.join(baseDir, 'config/visual_control_plane_backend_binding.json');

  const bindingDir = path.join(baseDir, 'artifacts/backend-binding/visual-control-plane-local-v1');
  const contractFile = path.join(bindingDir, 'backend_data_contract.json');
  const readinessFile = path.join(bindingDir, 'binding_readiness.json');

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
  assert(fs.existsSync(contractFile), "backend_data_contract.json exists");
  assert(fs.existsSync(readinessFile), "binding_readiness.json exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(contractFile) || !fs.existsSync(readinessFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let contract: any;
  let readiness: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_control_plane_backend_binding.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    contract = JSON.parse(fs.readFileSync(contractFile, 'utf-8'));
    assert(true, "backend_data_contract.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse contract: ${e.message}`);
    process.exit(1);
  }

  try {
    readiness = JSON.parse(fs.readFileSync(readinessFile, 'utf-8'));
    assert(true, "binding_readiness.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse readiness: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify config details
  assert(config.track === "P2_BACKEND_RUNTIME_BINDING_READINESS", "Track is P2_BACKEND_RUNTIME_BINDING_READINESS");
  assert(config.release_tag === "visual-control-plane-local-v1.0.0", "Release tag check");
  assert(config.integration_branch === "integration/visual-control-plane-local-v1", "Integration branch check");
  assert(config.binding_readiness_status === "READINESS_VERIFIED", "Binding readiness status check");
  assert(config.mutation_endpoints_enabled === false, "Mutation endpoints are disabled");

  // 4. Verify contract details
  assert(contract.contract_name === "Visual Control Plane Backend Data Contract", "Contract name check");
  assert(contract.endpoints["/api/v1/runtime/process/animation-state"].method === "GET", "animation-state is GET");
  assert(contract.endpoints["/api/v1/runtime/process/health"].method === "GET", "health is GET");
  assert(contract.safety_guarantees.read_only === true, "Safety guarantees: read-only is true");

  // 5. Verify readiness details
  assert(readiness.phase === "P2_BACKEND_RUNTIME_BINDING_READINESS", "Readiness phase check");
  assert(readiness.binding_readiness_verified === true, "Binding readiness verified is true");
  assert(readiness.endpoints_mapped.includes("/api/v1/runtime/process/animation-state"), "Mapped animation-state");
  assert(readiness.endpoints_mapped.includes("/api/v1/runtime/process/health"), "Mapped health");
  assert(readiness.mutation_endpoints_blocked === true, "Mutation endpoints blocked");

  // 6. Safety check: No mutations or websocket interfaces in preview JS
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
