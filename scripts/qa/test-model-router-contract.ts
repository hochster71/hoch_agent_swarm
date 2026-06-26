import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/model-router-contract-report.json";
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

// 1. Check Configuration Files
results["models_config_exists"] = fs.existsSync("config/models.yaml");
results["escalation_config_exists"] = fs.existsSync("config/escalation.yaml");

// 2. Check Backend Files
results["router_py_exists"] = fs.existsSync("backend/model_router/router.py");
results["registry_py_exists"] = fs.existsSync("backend/model_router/model_registry.py");
results["confidence_py_exists"] = fs.existsSync("backend/model_router/confidence.py");
results["escalation_policy_py_exists"] = fs.existsSync("backend/model_router/escalation_policy.py");
results["audit_log_py_exists"] = fs.existsSync("backend/model_router/audit_log.py");

// 3. Static checks on main.py endpoints
assertFileContains("backend/main.py", "/api/v1/models/registry", "main_has_models_registry_route");
assertFileContains("backend/main.py", "/api/v1/models/status", "main_has_models_status_route");
assertFileContains("backend/main.py", "/api/v1/models/run", "main_has_models_run_route");
assertFileContains("backend/main.py", "/api/v1/models/audit-log", "main_has_models_audit_log_route");

// 4. Static checks on skill gate
assertFileContains("config/skill_registry.json", "SKILL-MODEL-ROUTE", "skill_registry_has_model_route_skill");

// 5. Static checks on UI panel & styling
assertFileContains("frontend/archive/unused_views.html", "model-router-panel", "html_has_model_router_panel");
assertFileContains("frontend/index.html", "theme-selector", "html_has_theme_selector");
assertFileContains("frontend/archive/unused_views.js", "initModelRouterUI", "js_has_model_router_ui_init");
assertFileContains("frontend/styles.css", "theme-blue", "css_has_blue_theme");
assertFileContains("frontend/styles.css", "theme-pink", "css_has_pink_theme");

// 6. Active API Simulation checks
async function runApiChecks() {
  try {
    const registryRes = await fetch("http://localhost:8000/api/v1/models/registry");
    if (!registryRes.ok) {
      results["api_get_registry"] = false;
      issues.push(`API /api/v1/models/registry failed: ${registryRes.status}`);
    } else {
      const data = await registryRes.json();
      results["api_get_registry"] = data.local_first === true;
    }

    const statusRes = await fetch("http://localhost:8000/api/v1/models/status");
    if (!statusRes.ok) {
      results["api_get_status"] = false;
      issues.push(`API /api/v1/models/status failed: ${statusRes.status}`);
    } else {
      const data = await statusRes.json();
      results["api_get_status"] = data.local_first === true && data.paid_models_enabled === false;
    }

    const runRes = await fetch("http://localhost:8000/api/v1/models/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: "Say LOCAL ROUTER OK only.",
        task_type: "smoke_test",
        caller_tier: "ALPHA",
        caller_node: "macbook-pro-l1",
        rationale: "contract test run"
      })
    });
    
    // We expect it to either return success or fail-closed (503 Service Unavailable)
    // because no local server is running by default in CI, but it should NOT return 404 or crash.
    results["api_post_run"] = runRes.status === 200 || runRes.status === 503;
    if (runRes.status === 503) {
      const errData = await runRes.json();
      results["api_post_run_fails_safely"] = errData.detail.includes("No local model providers");
    } else {
      results["api_post_run_fails_safely"] = true;
    }
  } catch (err) {
    console.warn("Active API checks skipped or backend not running: ", err);
    results["api_get_registry"] = false;
    results["api_get_status"] = false;
    results["api_post_run"] = false;
    issues.push(`API connection failed: ${err}`);
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
    console.log("\n[PASS] Model router contract validation succeeded!");
    process.exit(0);
  } else {
    console.error("\n[FAIL] Model router contract validation failed!");
    process.exit(1);
  }
}

main();
