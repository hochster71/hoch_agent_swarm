import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/device-registry-contract-report.json";
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

function assertFileNotContains(filePath: string, term: string, checkName: string) {
  if (!fs.existsSync(filePath)) {
    results[checkName] = false;
    issues.push(`File missing: ${filePath}`);
    return;
  }
  const content = fs.readFileSync(filePath, "utf8");
  if (!content.includes(term)) {
    results[checkName] = true;
  } else {
    results[checkName] = false;
    issues.push(`File ${filePath} contains forbidden term "${term}"`);
  }
}

function assertFileExists(filePath: string, checkName: string) {
  if (fs.existsSync(filePath)) {
    results[checkName] = true;
  } else {
    results[checkName] = false;
    issues.push(`Expected file to exist: ${filePath}`);
  }
}

// 1. Source configuration iPad model assertions
assertFileContains("backend/cluster_manager.py", "MTXQ2LL/A", "backend_has_ipad_pro_11");
assertFileContains("backend/cluster_manager.py", "MUU62LL/A", "backend_has_ipad_mini_5");
assertFileContains("backend/cluster_manager.py", "MGNV2LL/A", "backend_has_ipad_mini_3");

// 2. DOM IDs assertions in index.html
assertFileContains("frontend/index.html", "cluster-command-map-v2", "html_has_command_map");
assertFileContains("frontend/index.html", "cluster-device-fleet-drawer", "html_has_fleet_drawer");
assertFileContains("frontend/index.html", "cluster-selected-node-inspector", "html_has_selected_inspector");

// 3. Frontend functions assertions in app.js
assertFileContains("frontend/app.js", "renderClusterCommandMapV2", "js_has_renderClusterCommandMapV2");
assertFileContains("frontend/app.js", "groupClusterDevicesByFleet", "js_has_groupClusterDevicesByFleet");
assertFileContains("frontend/app.js", "renderDeviceFleetDrawer", "js_has_renderDeviceFleetDrawer");
assertFileContains("frontend/app.js", "renderSelectedNodeInspector", "js_has_renderSelectedNodeInspector");

// 4. Package.json script name assertion
assertFileContains("package.json", "qa:device-registry-contract", "pkg_has_registry_contract_script");

// 5. Tailwind and entrypoint safety/non-pollution assertions
assertFileNotContains("frontend/index.html", "cdn.tailwindcss.com", "no_tailwind_cdn");
assertFileNotContains("frontend/index.html", "/src/main.tsx", "no_react_main_tsx");
assertFileExists("frontend/dist/tailwind.css", "tailwind_css_compiled_exists");

// 6. Active API validation
async function runApiChecks() {
  try {
    const res = await fetch("http://localhost:8000/api/status");
    if (!res.ok) {
      results["api_status_check"] = false;
      issues.push(`API status returned non-200: ${res.status}`);
      return;
    }
    const data = await res.json();
    const dataStr = JSON.stringify(data);
    
    results["api_exposes_ipad_pro_11"] = dataStr.includes("MTXQ2LL/A");
    results["api_exposes_ipad_mini_5"] = dataStr.includes("MUU62LL/A");
    results["api_exposes_ipad_mini_3"] = dataStr.includes("MGNV2LL/A");
    results["api_status_check"] = true;
    
    if (!results["api_exposes_ipad_pro_11"]) issues.push("API status payload missing MTXQ2LL/A");
    if (!results["api_exposes_ipad_mini_5"]) issues.push("API status payload missing MUU62LL/A");
    if (!results["api_exposes_ipad_mini_3"]) issues.push("API status payload missing MGNV2LL/A");
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
    console.log("\n[PASS] Device registry contract validation succeeded!");
    process.exit(0);
  } else {
    console.error("\n[FAIL] Device registry contract validation failed!");
    process.exit(1);
  }
}

main();
