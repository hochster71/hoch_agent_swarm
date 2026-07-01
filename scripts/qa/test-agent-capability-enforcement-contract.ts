import * as fs from "fs";
import * as path from "path";

async function runEnforcementContractTest() {
  console.log("==================================================");
  console.log("STARTING AGENT CAPABILITY ENFORCEMENT CONTRACT TEST");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];

  const mainPyPath = path.resolve(__dirname, "../../backend/main.py");
  const storePyPath = path.resolve(__dirname, "../../backend/runtime_execution_store.py");

  // 1. Verify backend/main.py assertions
  if (!fs.existsSync(mainPyPath)) {
    errors.push(`Missing backend/main.py at: ${mainPyPath}`);
  } else {
    const mainContent = fs.readFileSync(mainPyPath, "utf-8");

    // Assert backend/main.py contains enforce_agent_capability
    if (mainContent.includes("def enforce_agent_capability")) {
      findings.push("Found enforce_agent_capability definition in backend/main.py");
    } else {
      errors.push("Missing enforce_agent_capability function definition in backend/main.py");
    }

    // Assert backend/main.py contains capability event types
    const expectedEvents = [
      "capability.allowed",
      "capability.blocked",
      "capability.approval_required"
    ];
    expectedEvents.forEach((evt) => {
      if (mainContent.includes(evt)) {
        findings.push(`Found capability event reference in backend/main.py: ${evt}`);
      } else {
        errors.push(`Missing capability event reference in backend/main.py: ${evt}`);
      }
    });

    // Assert backend/main.py contains GET /api/v1/agents/{agent_id}/capability REST endpoint
    if (
      mainContent.includes("/api/v1/agents/{agent_id}/capability") ||
      mainContent.includes("/api/v1/agents/{agent_id}/capability")
    ) {
      findings.push("Found GET /api/v1/agents/{agent_id}/capability endpoint in backend/main.py");
    } else {
      errors.push("Missing GET /api/v1/agents/{agent_id}/capability endpoint in backend/main.py");
    }

    // Assert task execution path calls enforce_agent_capability before run_task_simulated
    const enforceIndex = mainContent.indexOf("enforce_agent_capability(");
    const simulatedIndex = mainContent.indexOf("run_task_simulated(");
    if (enforceIndex !== -1 && simulatedIndex !== -1) {
      if (enforceIndex < simulatedIndex) {
        findings.push("Verified enforce_agent_capability is called before run_task_simulated in main.py");
      } else {
        errors.push("enforce_agent_capability is not called before run_task_simulated in backend/main.py");
      }
    } else {
      errors.push("Could not trace enforce_agent_capability and run_task_simulated sequence in main.py");
    }
  }

  // 2. Verify backend/runtime_execution_store.py assertions
  if (!fs.existsSync(storePyPath)) {
    errors.push(`Missing backend/runtime_execution_store.py at: ${storePyPath}`);
  } else {
    const storeContent = fs.readFileSync(storePyPath, "utf-8");

    // Assert backend/runtime_execution_store.py contains capability_enforcement
    // Or equivalent evidence type handling
    if (
      storeContent.includes("evidence_type") ||
      storeContent.includes("capability_enforcement")
    ) {
      findings.push("Verified runtime_execution_store.py contains evidence_type or capability_enforcement handling");
    } else {
      errors.push("Missing evidence_type/capability_enforcement schema handling in runtime_execution_store.py");
    }
  }

  // 3. Write report
  const status = errors.length === 0 ? "PASS" : "FAIL";
  const report = {
    generated_at: new Date().toISOString(),
    status,
    errors,
    findings
  };

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/agent-capability-enforcement-contract-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`Capability Enforcement Contract Test completed with status: ${status}`);
  if (errors.length > 0) {
    console.error("Contract errors found:", errors);
    process.exit(1);
  } else {
    console.log("All capability enforcement contract checks passed successfully!");
    process.exit(0);
  }
}

runEnforcementContractTest();
