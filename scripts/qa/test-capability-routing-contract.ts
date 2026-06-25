import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/capability-routing-contract-report.json";
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

// 1. Static Invariant Assertions
assertFileContains("backend/capability_router.py", "route_task_by_capabilities", "backend_has_capability_routing_engine");
assertFileContains("backend/capability_router.py", "extract_required_capabilities", "backend_has_capability_extractor");
assertFileContains("backend/cluster_manager.py", "route_task_by_capabilities", "cluster_manager_integrates_capability_routing");
assertFileContains("backend/main.py", "/api/v1/devices/routing/history", "api_has_routing_history_endpoint");
assertFileContains("frontend/index.html", "device-routing-center-panel", "html_has_routing_panel");
assertFileContains("frontend/app.js", "initCapabilityRouterUI", "js_has_routing_ui_init");
assertFileContains("package.json", "qa:capability-routing-contract", "pkg_has_routing_contract_script");

// 2. Active API Simulation & Verification
async function runApiRoutingChecks() {
  try {
    // A. Simulate task 1: Operator approval task
    const t1Res = await fetch("http://localhost:8000/api/tasks/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_type: "approval",
        prompt: "Please approve the release seal attestation",
        mode: "Simulate"
      })
    });
    
    if (!t1Res.ok) {
      results["simulate_approval_task"] = false;
      issues.push(`Simulating approval task failed with status ${t1Res.status}`);
      return;
    }
    const t1Data = await t1Res.json();
    results["approval_task_routes_to_eligible_node"] = ["L1", "IPAD", "IPAD_PRO_11", "IPAD_MINI_1", "IPAD_MINI_2", "discovery-ipad-mock"].includes(t1Data.routed_node?.id);
    if (!results["approval_task_routes_to_eligible_node"]) {
      issues.push(`Approval task did not route to an eligible node, routed to: ${t1Data.routed_node?.id}`);
    }

    // B. Simulate task 2: General compute task
    const t2Res = await fetch("http://localhost:8000/api/tasks/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_type: "compute",
        prompt: "Execute python script for model training",
        mode: "Simulate"
      })
    });
    
    if (!t2Res.ok) {
      results["simulate_compute_task"] = false;
      issues.push(`Simulating compute task failed with status ${t2Res.status}`);
      return;
    }
    const t2Data = await t2Res.json();
    // Should route to one of the compute nodes: L1, L2, L3, W1
    results["compute_task_routes_to_compute_node"] = ["L1", "L2", "L3", "W1"].includes(t2Data.routed_node?.id);
    if (!results["compute_task_routes_to_compute_node"]) {
      issues.push(`Compute task did not route to a compute node, routed to: ${t2Data.routed_node?.id}`);
    }

    // C. Verify routing history log endpoint
    const historyRes = await fetch("http://localhost:8000/api/v1/devices/routing/history?limit=10");
    if (!historyRes.ok) {
      results["get_routing_history"] = false;
      issues.push(`Failed to fetch routing history endpoint: ${historyRes.status}`);
      return;
    }
    const historyData = await historyRes.json();
    results["routing_history_records_decisions"] = historyData.length >= 2;
    if (!results["routing_history_records_decisions"]) {
      issues.push(`Expected at least 2 records in routing history, found: ${historyData.length}`);
    }

  } catch (err: any) {
    results["api_routing_checks"] = false;
    issues.push(`Failed to run API routing checks: ${err.message}`);
  }
}

async function main() {
  await runApiRoutingChecks();

  const allPassed = Object.values(results).every((v) => v === true);
  const status = allPassed ? "PASS" : "FAIL";

  const report = {
    timestamp: new Date().toISOString(),
    status,
    results,
    issues,
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
  console.log(`Contract Test Finished. Status: ${status}`);
  if (!allPassed) {
    console.error("Issues found:", issues);
    process.exit(1);
  }
  process.exit(0);
}

main();
