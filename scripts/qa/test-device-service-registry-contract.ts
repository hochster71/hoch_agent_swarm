import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/device-service-registry-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const results: Record<string, boolean> = {};
const issues: string[] = [];

function assertFileContains(filePath: string, term: string, checkName: string) {
  if (!fs.existsSync(filePath)) {
    results[checkName] = false;
    issues.push(`File missing: ${filePath}`);
    return;
  }
  const content = fs.readFileSync(filePath, "utf8");
  if (content.includes(term)) {
    results[checkName] = true;
  } else {
    results[checkName] = false;
    issues.push(`File ${filePath} does not contain term "${term}"`);
  }
}

// 1. Check REST API route declarations in main.py
assertFileContains("backend/main.py", "/api/v1/devices/discovery/policy", "backend_has_discovery_policy_route");
assertFileContains("backend/main.py", "/api/v1/devices/discovered", "backend_has_discovered_list_route");
assertFileContains("backend/main.py", "/api/v1/devices/discover", "backend_has_discover_trigger_route");
assertFileContains("backend/main.py", "/api/v1/devices/service-registry", "backend_has_service_registry_list_route");
assertFileContains("backend/main.py", "/approve", "backend_has_approve_route");
assertFileContains("backend/main.py", "/reject", "backend_has_reject_route");

// 2. Check DOM Elements in index.html
assertFileContains("frontend/archive/unused_views.html", "device-service-registry-panel", "html_has_registry_panel");
assertFileContains("frontend/archive/unused_views.html", "device-discovery-policy-panel", "html_has_discovery_policy_panel");
assertFileContains("frontend/archive/unused_views.html", "device-discovery-run-button", "html_has_discovery_run_btn");
assertFileContains("frontend/archive/unused_views.html", "device-discovery-status", "html_has_discovery_status_span");
assertFileContains("frontend/archive/unused_views.html", "discovered-device-list", "html_has_discovered_list_div");
assertFileContains("frontend/archive/unused_views.html", "service-node-registry-list", "html_has_service_node_registry_list");
assertFileContains("frontend/archive/unused_views.html", "device-service-approval-panel", "html_has_approval_panel_div");
assertFileContains("frontend/archive/unused_views.html", "device-service-role-list", "html_has_service_role_list_div");

// 3. Check App.js UI methods
assertFileContains("frontend/archive/unused_views.js", "initDeviceRegistry", "js_has_initDeviceRegistry");
assertFileContains("frontend/archive/unused_views.js", "loadRegistryData", "js_has_loadRegistryData");
assertFileContains("frontend/archive/unused_views.js", "executeDeviceDiscovery", "js_has_executeDeviceDiscovery");
assertFileContains("frontend/archive/unused_views.js", "renderDiscoveredDevices", "js_has_renderDiscoveredDevices");
assertFileContains("frontend/archive/unused_views.js", "selectDiscoveredDevice", "js_has_selectDiscoveredDevice");
assertFileContains("frontend/archive/unused_views.js", "executeDeviceApproval", "js_has_executeDeviceApproval");
assertFileContains("frontend/archive/unused_views.js", "executeDeviceRejection", "js_has_executeDeviceRejection");
assertFileContains("frontend/archive/unused_views.js", "renderApprovedServiceNodes", "js_has_renderApprovedServiceNodes");

// 4. Check status schema response includes service_nodes & devices.services
assertFileContains("backend/main.py", "list_service_nodes()", "backend_status_exposes_service_nodes");

// 5. Active API validation
async function runApiChecks() {
  try {
    const res = await fetch("http://localhost:8000/api/status");
    if (!res.ok) {
      results["api_status_check"] = false;
      issues.push(`API status returned non-200: ${res.status}`);
      return;
    }
    const data = await res.json();
    
    results["api_status_has_service_nodes_field"] = "service_nodes" in data;
    results["api_status_has_devices_services_field"] = "devices" in data && "services" in data.devices;
    results["api_status_check"] = true;
    
    if (!results["api_status_has_service_nodes_field"]) issues.push("API status payload missing 'service_nodes' field");
    if (!results["api_status_has_devices_services_field"]) issues.push("API status payload missing 'devices.services' field");
  } catch (err: any) {
    results["api_status_check"] = false;
    issues.push(`Failed to reach API status endpoint: ${err.message}`);
  }
}

async function main() {
  await runApiChecks();
  
  const allPassed = Object.values(results).every(v => v === true);
  const report = {
    generated_at: new Date().toISOString(),
    status: allPassed ? "PASS" : "BLOCK",
    results,
    issues
  };
  
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));
  
  if (allPassed) {
    console.log("\n[PASS] Device service registry contract validation succeeded!");
    process.exit(0);
  } else {
    console.error("\n[FAIL] Device service registry contract validation failed!");
    process.exit(1);
  }
}

main();
