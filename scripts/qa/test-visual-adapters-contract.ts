import * as fs from 'fs';
import * as path from 'path';

function runVisualAdaptersTests() {
  console.log("==================================================");
  console.log("VISUAL ADAPTERS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const adaptersFile = path.join(baseDir, 'frontend/visual_adapters.js');
  const fixturesFile = path.join(baseDir, 'frontend/visual_adapters.test-fixtures.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/13_controlled_dashboard_adapters.md');

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
  assert(fs.existsSync(adaptersFile), "frontend/visual_adapters.js file exists");
  assert(fs.existsSync(fixturesFile), "frontend/visual_adapters.test-fixtures.json file exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/13_controlled_dashboard_adapters.md exists");

  if (!fs.existsSync(adaptersFile) || !fs.existsSync(fixturesFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Scan file content for disallowed APIs
  const code = fs.readFileSync(adaptersFile, 'utf-8');
  assert(!code.includes('document.'), "Safety check: No DOM mutations ('document.') used");
  assert(!code.includes('window.'), "Safety check: No window side effects ('window.') used");
  assert(!code.includes('fetch(') && !code.includes('fetch ('), "Safety check: No HTTP fetch calls ('fetch') used");
  assert(!code.includes('WebSocket'), "Safety check: No WebSocket connections used");
  assert(!code.includes('EventSource'), "Safety check: No EventSource (SSE) connections used");

  // 3. Load fixtures and adapters
  const fixtures = JSON.parse(fs.readFileSync(fixturesFile, 'utf-8'));
  const adapters = require(adaptersFile);

  const requiredExports = [
    'normalizeState',
    'isFresh',
    'adaptCockpitTelemetry',
    'adaptPromptRegistry',
    'adaptKnownAssets',
    'adaptApprovalQueue',
    'adaptEvidenceManifest',
    'adaptPromptRouterPlan',
    'adaptModelRuntime',
    'adaptMetricStrip',
    'adaptAgentCard',
    'adaptPipelineStage'
  ];

  requiredExports.forEach(fn => {
    assert(typeof adapters[fn] === 'function', `Exported function '${fn}' exists`);
  });

  // 4. Test State Normalization
  assert(adapters.normalizeState("live") === "LIVE", "State label normalized: 'live' -> 'LIVE'");
  assert(adapters.normalizeState("fail_closed") === "FAIL-CLOSED", "State label normalized: 'fail_closed' -> 'FAIL-CLOSED'");
  assert(adapters.normalizeState("degraded") === "DEGRADED", "State label normalized: 'degraded' -> 'DEGRADED'");
  assert(adapters.normalizeState(null) === "UNAVAILABLE", "Null input returns UNAVAILABLE");

  // 5. Test Freshness Logic
  // Mock time is 2026-06-27T18:00:00Z
  assert(adapters.isFresh("2026-06-27T17:59:50Z", 30) === true, "Timestamp within 30 seconds is fresh");
  assert(adapters.isFresh("2026-06-27T17:59:00Z", 30) === false, "Timestamp older than 30 seconds is stale");

  // 6. Test Cockpit Telemetry Adaptations
  const teleHealthy = adapters.adaptCockpitTelemetry(fixtures.cockpit_healthy);
  assert(teleHealthy.state === "LIVE", "Healthy cockpit payload adapts to LIVE");

  const teleMissing = adapters.adaptCockpitTelemetry(fixtures.cockpit_missing);
  assert(teleMissing.state === "UNAVAILABLE", "Missing cockpit payload adapts to UNAVAILABLE");

  const teleStale = adapters.adaptCockpitTelemetry(fixtures.cockpit_stale);
  assert(teleStale.state === "STALE", "Stale cockpit payload adapts to STALE");

  // 7. Test Prompt Registry Adaptations
  const reg103 = adapters.adaptPromptRegistry(fixtures.prompt_registry_103);
  assert(reg103.state === "LIVE", "Populated prompt registry adapts to LIVE");
  assert(reg103.metrics.count === 103, "Registry count is 103");

  const regMissing = adapters.adaptPromptRegistry(fixtures.prompt_registry_missing);
  assert(regMissing.state === "UNAVAILABLE", "Missing prompt registry adapts to UNAVAILABLE");

  // 8. Test Known Assets Adaptations
  const assets9 = adapters.adaptKnownAssets(fixtures.known_assets_9_devices);
  assert(assets9.state === "LIVE", "Known assets payload adapts to LIVE");
  assert(assets9.metrics.count === 9, "Known assets count is 9");

  const assetsMissing = adapters.adaptKnownAssets(null);
  assert(assetsMissing.state === "UNAVAILABLE", "Missing known assets adapts to UNAVAILABLE");

  // 9. Test Approval Queue Adaptations
  const appPending = adapters.adaptApprovalQueue(fixtures.approval_queue_pending);
  assert(appPending.state === "PENDING", "Pending approval queue adapts to PENDING");
  assert(appPending.approval.required === true, "Approval queue maps human_approval_required");

  const appFailClosed = adapters.adaptApprovalQueue(fixtures.approval_queue_fail_closed);
  assert(appFailClosed.state === "FAIL-CLOSED", "Fail-closed approval queue adapts to FAIL-CLOSED");

  // 10. Test Evidence Manifest Adaptations
  const evPresent = adapters.adaptEvidenceManifest(fixtures.evidence_manifest_present);
  assert(evPresent.state === "LIVE", "Present evidence manifest adapts to LIVE");

  const evMissing = adapters.adaptEvidenceManifest(fixtures.evidence_manifest_missing);
  assert(evMissing.state === "UNAVAILABLE", "Missing evidence manifest adapts to UNAVAILABLE");

  // 11. Test Prompt Router Plan Adaptations
  const planApproval = adapters.adaptPromptRouterPlan(fixtures.prompt_router_plan_approval);
  assert(planApproval.state === "DEGRADED", "Approval-required route plan adapts to DEGRADED");
  assert(planApproval.approval.required === true, "Approval required is true");

  const planFailClosed = adapters.adaptPromptRouterPlan(fixtures.prompt_router_fail_closed);
  assert(planFailClosed.state === "FAIL-CLOSED", "Fail-closed route plan adapts to FAIL-CLOSED");

  // 12. Allowed state label check
  const allowedStates = ["LIVE", "DEGRADED", "PENDING", "SIMULATED", "STALE", "FAIL-CLOSED", "UNAVAILABLE", "UNKNOWN"];
  [
    teleHealthy, teleMissing, teleStale, reg103, regMissing,
    assets9, assetsMissing, appPending, appFailClosed, evPresent,
    evMissing, planApproval, planFailClosed
  ].forEach(vm => {
    assert(allowedStates.includes(vm.state), `Resulting state '${vm.state}' is in allowed state labels list`);
  });

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL ADAPTERS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL ADAPTERS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runVisualAdaptersTests();
