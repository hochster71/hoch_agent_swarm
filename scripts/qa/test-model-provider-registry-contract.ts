import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/model-provider-registry-report.json";
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
assertFileContains("backend/runtime_execution_store.py", "model_providers", "db_has_model_providers_table");
assertFileContains("backend/runtime_execution_store.py", "inference_runs", "db_has_inference_runs_table");
assertFileContains("backend/model_provider_registry.py", "register_model_provider", "backend_has_provider_registry_register");
assertFileContains("backend/inference_gateway.py", "route_inference_request", "backend_has_inference_gateway");
assertFileContains("backend/main.py", "/api/v1/models/providers", "api_has_providers_endpoint");
assertFileContains("backend/main.py", "/api/v1/inference/chat", "api_has_inference_chat_endpoint");
assertFileContains("backend/main.py", "/api/v1/mock/llm", "api_has_mock_llm_endpoint");
assertFileContains("frontend/index.html", "model-provider-registry-panel", "html_has_model_registry_panel");
assertFileContains("frontend/index.html", "inference-test-panel", "html_has_inference_test_panel");
assertFileContains("frontend/app.js", "initModelProviderRegistryUI", "js_has_registry_ui_init");
assertFileContains("frontend/app.js", "loadModelProviders", "js_has_load_providers_function");

// 2. Active API Simulation & Verification
async function runApiChecks() {
  try {
    // A. Register a new provider pointing to the local mock LLM
    const regRes = await fetch("http://localhost:8000/api/v1/models/providers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: "Local Gemma 4 12B Mock",
        endpoint_url: "http://localhost:8000/api/v1/mock/llm/v1/chat/completions",
        node_id: "IPAD_PRO_12",
        provider_type: "openai_compatible",
        default_model: "gemma-4-12b",
        api_key_required: false,
        trusted_for_sensitive_context: false,
        allowed_agent_roles: ["research", "summarize"],
        allowed_task_types: ["summarization", "local_reasoning"]
      })
    });

    if (!regRes.ok) {
      results["register_provider_api"] = false;
      issues.push(`Registering provider failed with status ${regRes.status}`);
      return;
    }
    const regData = await regRes.json();
    const pid = regData.provider ? regData.provider.model_provider_id : regData.model_provider_id;
    results["register_provider_api"] = !!pid;

    // B. Run health check
    const healthRes = await fetch(`http://localhost:8000/api/v1/models/providers/${pid}/health-check`, {
      method: "POST"
    });
    if (!healthRes.ok) {
      results["health_check_api"] = false;
      issues.push(`Health check failed with status ${healthRes.status}`);
    } else {
      const healthData = await healthRes.json();
      results["health_check_api"] = healthData.provider.health_status === "available";
      if (!results["health_check_api"]) {
        issues.push(`Expected provider status "available", got "${healthData.provider.health_status}"`);
      }
    }

    // C. Discover models
    const discRes = await fetch(`http://localhost:8000/api/v1/models/providers/${pid}/discover-models`, {
      method: "POST"
    });
    if (!discRes.ok) {
      results["discover_models_api"] = false;
      issues.push(`Discover models failed with status ${discRes.status}`);
    } else {
      const discData = await discRes.json();
      results["discover_models_api"] = discData.models.includes("gemma-4-12b");
      if (!results["discover_models_api"]) {
        issues.push(`Expected discovered models to include "gemma-4-12b", got "${JSON.stringify(discData.models)}"`);
      }
    }

    // D. Approve provider
    const appRes = await fetch(`http://localhost:8000/api/v1/models/providers/${pid}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator: "Michael Hoch",
        allowed_agent_roles: ["research", "summarize", "review"],
        allowed_task_types: ["summarization", "local_reasoning", "code_review"]
      })
    });
    if (!appRes.ok) {
      results["approve_provider_api"] = false;
      issues.push(`Approval failed with status ${appRes.status}`);
    } else {
      const appData = await appRes.json();
      results["approve_provider_api"] = appData.provider.approved_for_inference === true;
      if (!results["approve_provider_api"]) {
        issues.push(`Expected approved_for_inference to be true`);
      }
    }

    // E. Execute chat completion via the gateway
    const chatRes = await fetch("http://localhost:8000/api/v1/inference/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_provider_id: pid,
        model: "gemma-4-12b",
        agent_id: "researcher",
        task_id: "contract-test-task-1",
        messages: [{ role: "user", content: "Explain quantum computing in one sentence" }],
        options: { temperature: 0.1 }
      })
    });
    let inferenceRunId = "";
    if (!chatRes.ok) {
      results["inference_chat_api"] = false;
      issues.push(`Inference chat failed with status ${chatRes.status}`);
    } else {
      const chatData = await chatRes.json();
      results["inference_chat_api"] = chatData.response.length > 0 && !!chatData.inference_run_id;
      inferenceRunId = chatData.inference_run_id;
      if (!results["inference_chat_api"]) {
        issues.push(`Expected valid response and inference_run_id, got: ${JSON.stringify(chatData)}`);
      }
    }

    // F. Verify evidence artifact generation
    if (inferenceRunId) {
      const evidencePath = `artifacts/inference/${inferenceRunId}.json`;
      if (fs.existsSync(evidencePath)) {
        const evidenceContent = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
        results["evidence_artifact_generated"] = evidenceContent.inference_run_id === inferenceRunId && evidenceContent.status === "success";
        if (!results["evidence_artifact_generated"]) {
          issues.push(`Evidence file content mismatch or failed: ${evidenceContent.status}`);
        }
      } else {
        results["evidence_artifact_generated"] = false;
        issues.push(`Evidence artifact file missing at: ${evidencePath}`);
      }
    } else {
      results["evidence_artifact_generated"] = false;
      issues.push("Cannot verify evidence file since inference run ID is missing");
    }

    // G. Verify inference history retrieval
    const historyRes = await fetch("http://localhost:8000/api/v1/inference/history");
    if (!historyRes.ok) {
      results["inference_history_api"] = false;
      issues.push(`Failed to fetch history: ${historyRes.status}`);
    } else {
      const historyData = await historyRes.json();
      results["inference_history_api"] = historyData.some((h: any) => h.inference_run_id === inferenceRunId);
      if (!results["inference_history_api"]) {
        issues.push(`Expected history to contain run ${inferenceRunId}`);
      }
    }

  } catch (err: any) {
    results["api_checks"] = false;
    issues.push(`Failed to run API checks: ${err.message}`);
  }
}

async function main() {
  await runApiChecks();

  const allPassed = Object.values(results).every((v) => v === true);
  const status = allPassed ? "PASS" : "FAIL";

  const report = {
    timestamp: new Date().toISOString(),
    status,
    results,
    issues,
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
  console.log(`Model Provider Registry Contract Test Finished. Status: ${status}`);
  if (!allPassed) {
    console.error("Issues found:", issues);
    process.exit(1);
  }
  process.exit(0);
}

main();
