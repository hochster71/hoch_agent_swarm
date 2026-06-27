import * as fs from 'fs';
import * as path from 'path';

function runVisualDataBindingsTests() {
  console.log("==================================================");
  console.log("VISUAL DATA BINDINGS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const bindingsJsonFile = path.join(baseDir, 'config/visual_data_bindings.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/12_data_binding_plan.md');

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
  assert(fs.existsSync(bindingsJsonFile), "config/visual_data_bindings.json file exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/12_data_binding_plan.md doc file exists");

  if (!fs.existsSync(bindingsJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON
  let bindings: any;
  try {
    const rawJson = fs.readFileSync(bindingsJsonFile, 'utf-8');
    bindings = JSON.parse(rawJson);
    assert(true, "config/visual_data_bindings.json parses cleanly as JSON");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_data_bindings.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety/runtime flags
  assert(bindings.runtime_binding_enabled === false, "Safety check: runtime_binding_enabled is false");
  assert(bindings.live_dashboard_replacement_enabled === false, "Safety check: live_dashboard_replacement_enabled is false");

  // 4. Verify all 8 state labels are present in JSON
  const stateLabelsList = [
    "LIVE",
    "DEGRADED",
    "PENDING",
    "SIMULATED",
    "STALE",
    "FAIL-CLOSED",
    "UNAVAILABLE",
    "UNKNOWN"
  ];
  stateLabelsList.forEach(state => {
    assert(bindings.state_labels.includes(state), `State label '${state}' present in JSON config`);
  });

  // 5. Verify all 14 components have bindings in JSON
  const componentsList = [
    "ops-header",
    "status-pill",
    "telemetry-card",
    "agent-card",
    "approval-card",
    "evidence-card",
    "pipeline-stage",
    "node-map-card",
    "prompt-card",
    "risk-badge",
    "state-registry",
    "terminal-panel",
    "metric-strip",
    "section-rail"
  ];

  componentsList.forEach(compName => {
    const compBinding = bindings.component_bindings.find((b: any) => b.component_name === compName);
    assert(compBinding !== undefined, `Component '${compName}' has a defined binding`);
    if (compBinding) {
      assert(compBinding.source_type !== undefined, `Component '${compName}' binding has source_type`);
      assert(compBinding.source_path !== undefined, `Component '${compName}' binding has source_path`);
      assert(compBinding.refresh_strategy !== undefined, `Component '${compName}' binding has refresh_strategy`);
      assert(compBinding.required_fields !== undefined, `Component '${compName}' binding has required_fields`);
      assert(compBinding.state_mapping !== undefined, `Component '${compName}' binding has state_mapping`);
      assert(compBinding.fallback_state !== undefined, `Component '${compName}' binding has fallback_state`);
      assert(compBinding.evidence_required !== undefined, `Component '${compName}' binding has evidence_required`);
      assert(compBinding.fail_closed_conditions !== undefined, `Component '${compName}' binding has fail_closed_conditions`);
    }
  });

  // 6. Verify references to sources
  const cockpitRef = bindings.sources.some((s: any) => s.path === "/api/v1/live-runtime/cockpit");
  assert(cockpitRef, "Binding sources references /api/v1/live-runtime/cockpit");

  const registryRef = bindings.sources.some((s: any) => s.path === "/api/v1/prompts/registry");
  assert(registryRef, "Binding sources references /api/v1/prompts/registry");

  const assetRef = bindings.sources.some((s: any) => s.path.includes("known_asset_probe_report.json"));
  assert(assetRef, "Binding sources references known_asset_probe_report.json");

  const reportRef = bindings.sources.some((s: any) => s.path.includes("prompt_registry_report.json"));
  assert(reportRef, "Binding sources references prompt_registry_report.json");

  // 7. Verify documentation content
  const docContent = fs.readFileSync(docFile, 'utf-8');
  assert(docContent.includes('/api/v1/live-runtime/cockpit'), "Documentation references /api/v1/live-runtime/cockpit");
  assert(docContent.includes('/api/v1/prompts/registry'), "Documentation references /api/v1/prompts/registry");
  assert(docContent.includes('known_asset_probe_report.json'), "Documentation references known_asset_probe_report.json");
  assert(docContent.includes('prompt_registry_report.json'), "Documentation references prompt_registry_report.json");

  assert(docContent.toLowerCase().includes('polling'), "Documentation references polling strategy");
  assert(docContent.toLowerCase().includes('sse') || docContent.toLowerCase().includes('server-sent events'), "Documentation references SSE strategy");
  assert(docContent.toLowerCase().includes('websocket'), "Documentation references WebSocket strategy");

  // 8. Policy mappings verification
  const mapsMissingToLive = bindings.component_bindings.some((b: any) => {
    return b.state_mapping["missing"] === "LIVE" || b.state_mapping["missing_source"] === "LIVE";
  });
  assert(!mapsMissingToLive, "Safety check: No component maps missing data to LIVE");

  // Stale data maps to STALE
  assert(bindings.freshness_policy.expired_fallback === "STALE", "Freshness policy expired fallback maps to STALE");
  
  // Security ambiguity maps to FAIL-CLOSED
  assert(bindings.fallback_policy.security_ambiguity === "FAIL-CLOSED", "Fallback policy security ambiguity maps to FAIL-CLOSED");

  // Static mock data maps to SIMULATED
  assert(bindings.fallback_policy.static_mock === "SIMULATED", "Fallback policy static mock maps to SIMULATED");

  // Approval card requires human approval
  const appCard = bindings.component_bindings.find((b: any) => b.component_name === "approval-card");
  assert(appCard && appCard.human_approval_required === true, "Approval card binding enforces human_approval_required=true");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL DATA BINDINGS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL DATA BINDINGS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runVisualDataBindingsTests();
