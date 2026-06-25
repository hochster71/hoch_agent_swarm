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

// 1. Source configuration assertions
assertFileContains("backend/cluster_manager.py", "MTXQ2LL/A", "backend_has_ipad_pro_11");
assertFileContains("backend/cluster_manager.py", "MUU62LL/A", "backend_has_ipad_mini_5");
assertFileContains("backend/cluster_manager.py", "MGNV2LL/A", "backend_has_ipad_mini_3");

assertFileContains("frontend/src/lib/assets/assetStore.ts", "MTXQ2LL/A", "store_has_ipad_pro_11");
assertFileContains("frontend/src/lib/assets/assetStore.ts", "MUU62LL/A", "store_has_ipad_mini_5");
assertFileContains("frontend/src/lib/assets/assetStore.ts", "MGNV2LL/A", "store_has_ipad_mini_3");

// 2. Active API validation
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
