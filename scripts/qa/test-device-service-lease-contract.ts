import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/device-service-lease-contract-report.json";
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
assertFileContains("backend/runtime_execution_store.py", "service_node_leases", "db_has_leases_table");
assertFileContains("backend/runtime_execution_store.py", "update_service_node_lease", "db_has_update_lease_helper");
assertFileContains("backend/runtime_execution_store.py", "get_service_node_leases", "db_has_get_leases_helper");
assertFileContains("backend/capability_router.py", "service_node_leases", "router_reads_leases_table");
assertFileContains("backend/capability_router.py", "sleeping", "router_excludes_sleeping_leases");
assertFileContains("backend/capability_router.py", "expired", "router_excludes_expired_leases");
assertFileContains("backend/main.py", "/api/v1/devices/lease/refresh", "api_has_lease_refresh_route");
assertFileContains("backend/main.py", "/api/v1/devices/leases", "api_has_list_leases_route");
assertFileContains("frontend/app.js", "node.lease", "js_renders_node_lease_details");
assertFileContains("package.json", "qa:device-service-lease", "pkg_has_lease_contract_script");

// 2. Active API Lease Refresh & Routing Validation
async function runApiLeaseChecks() {
  const nodeId = "discovery-ipad-mock";
  try {
    // A. Inject/Refresh lease as available
    const refreshRes = await fetch("http://localhost:8000/api/v1/devices/lease/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: nodeId,
        battery_level: 88.5,
        power_source: "Battery",
        network_status: "connected",
        availability: "available",
        lease_duration_seconds: 300
      })
    });
    if (!refreshRes.ok) {
      results["refresh_lease_api"] = false;
      issues.push(`Lease refresh API failed with status ${refreshRes.status}`);
      return;
    }
    const refreshData = await refreshRes.json();
    results["refresh_lease_api"] = refreshData.status === "SUCCESS";

    // B. Run task simulation - should route to discovery-ipad-mock since lease is active and CPU is 15 (lower than L1)
    const run1Res = await fetch("http://localhost:8000/api/tasks/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_type: "approval",
        prompt: "Verify and approve this release draft",
        mode: "Simulate"
      })
    });
    if (run1Res.ok) {
      const run1Data = await run1Res.json();
      results["task_routes_to_active_lease"] = ["discovery-ipad-mock", "IPAD_PRO_11", "IPAD_MINI_1", "IPAD_MINI_2"].includes(run1Data.routed_node?.id);
      if (!results["task_routes_to_active_lease"]) {
        issues.push(`Expected task to route to an eligible iPad, but routed to: ${run1Data.routed_node?.id}`);
      }
    } else {
      results["task_routes_to_active_lease"] = false;
      issues.push(`Task run simulator returned status ${run1Res.status}`);
    }

    // C. Set lease to sleeping
    const sleepRes = await fetch("http://localhost:8000/api/v1/devices/lease/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: nodeId,
        battery_level: 88.5,
        power_source: "Battery",
        network_status: "connected",
        availability: "sleeping",
        lease_duration_seconds: 300
      })
    });
    if (!sleepRes.ok) {
      results["set_lease_sleeping"] = false;
      issues.push(`Setting lease to sleeping failed: ${sleepRes.status}`);
      return;
    }
    results["set_lease_sleeping"] = true;

    // D. Run task simulation - should reject discovery-ipad-mock and fallback to L1
    const run2Res = await fetch("http://localhost:8000/api/tasks/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_type: "approval",
        prompt: "Verify and approve this release draft",
        mode: "Simulate"
      })
    });
    if (run2Res.ok) {
      const run2Data = await run2Res.json();
      results["task_excludes_sleeping_lease"] = run2Data.routed_node?.id !== nodeId;
      if (!results["task_excludes_sleeping_lease"]) {
        issues.push(`Expected task to exclude sleeping ${nodeId}, but it still routed to it.`);
      }
    } else {
      results["task_excludes_sleeping_lease"] = false;
      issues.push(`Task run simulator (sleeping lease check) returned status ${run2Res.status}`);
    }

  } catch (err: any) {
    results["api_lease_validation"] = false;
    issues.push(`API lease checks failed: ${err.message}`);
  }
}

async function main() {
  await runApiLeaseChecks();

  const allPassed = Object.values(results).every((v) => v === true);
  const status = allPassed ? "PASS" : "FAIL";

  const report = {
    timestamp: new Date().toISOString(),
    status,
    results,
    issues,
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
  console.log(`Lease Manager Contract Test Finished. Status: ${status}`);
  if (!allPassed) {
    console.error("Issues found:", issues);
    process.exit(1);
  }
  process.exit(0);
}

main();
