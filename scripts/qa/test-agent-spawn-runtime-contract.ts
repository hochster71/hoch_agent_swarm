import fs from "node:fs";
import path from "node:path";

const serverUrl = "http://localhost:8000";
const blockers: string[] = [];

async function runContractTest() {
  console.log("Starting Governed Agent Spawn Runtime Contract Verification...");

  // 1. Static Checks: Verify code integrations in main.py and app.js
  const mainPyPath = "backend/main.py";
  const appJsPath = "frontend/app.js";

  if (!fs.existsSync(mainPyPath)) {
    blockers.push("Missing backend/main.py file.");
  } else {
    const content = fs.readFileSync(mainPyPath, "utf8");
    if (!content.includes("execute_agent_run_real")) {
      blockers.push("backend/main.py must define 'execute_agent_run_real'.");
    }
    if (!content.includes('"T1-EXEC"')) {
      blockers.push("backend/main.py must handle custom task ID 'T1-EXEC'.");
    }
  }

  if (!fs.existsSync(appJsPath)) {
    blockers.push("Missing frontend/app.js file.");
  } else {
    const content = fs.readFileSync(appJsPath, "utf8");
    if (!content.includes("/api/approval/requests")) {
      blockers.push("frontend/app.js must fetch from '/api/approval/requests'.");
    }
    if (!content.includes("agent_launch")) {
      blockers.push("frontend/app.js must support 'agent_launch' approval type.");
    }
  }

  // If static checks fail, abort early
  if (blockers.length > 0) {
    writeReportAndExit();
    return;
  }

  // 2. Runtime API E2E Verification against localhost:8000
  try {
    // A. Stage agent prompt
    console.log("Staging a governed agent prompt...");
    const stageRes = await fetch(`${serverUrl}/api/v1/swarm/agent-chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent: "Mission Commander",
        target: "swarm",
        prompt: "Audit all model runtimes and stage QA self-heal agents.",
      }),
    });

    if (!stageRes.ok) {
      blockers.push(`Staging agent chat failed: HTTP ${stageRes.status}`);
      writeReportAndExit();
      return;
    }

    const stageData = await stageRes.json();
    const runId = stageData.run_id;
    const taskId = stageData.task_id;
    const approvalId = stageData.approval_id;

    if (!runId || !taskId || !approvalId) {
      blockers.push("Staging response must contain run_id, task_id, and approval_id.");
      writeReportAndExit();
      return;
    }

    console.log(`Staged successfully. Run ID: ${runId}, Task ID: ${taskId}, Approval ID: ${approvalId}`);

    // B. Check that approvals list includes the pending request
    console.log("Fetching pending approvals list...");
    const appListRes = await fetch(`${serverUrl}/api/approval/requests`);
    const appList = await appListRes.json();
    const pendingApp = appList.find((a: any) => a.approval_id === approvalId);

    if (!pendingApp) {
      blockers.push(`Pending approval ${approvalId} not found in /api/approval/requests.`);
    } else if (pendingApp.status !== "pending") {
      blockers.push(`Expected approval status to be 'pending', got '${pendingApp.status}'.`);
    }

    // C. Check that the task is blocked pending approval in SQLite
    console.log("Fetching task status...");
    const tasksRes = await fetch(`${serverUrl}/api/v1/runs/${runId}/tasks`);
    const tasks = await tasksRes.json();
    const targetTask = tasks.find((t: any) => t.id === taskId);

    if (!targetTask) {
      blockers.push(`Staged task ${taskId} not found in run ${runId}.`);
    } else if (targetTask.status !== "blocked_pending_approval") {
      blockers.push(`Expected task status to be 'blocked_pending_approval', got '${targetTask.status}'.`);
    }

    // D. Approve the launch request
    console.log(`Submitting approval decision for ${approvalId}...`);
    const decRes = await fetch(`${serverUrl}/api/approval/requests/${approvalId}/decisions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: "approve",
        reason: "Contract test auto-approval",
        operator: "QA Auto-Tester",
      }),
    });

    if (!decRes.ok) {
      blockers.push(`Submitting approval decision failed: HTTP ${decRes.status}`);
      writeReportAndExit();
      return;
    }

    // E. Wait for background execution to complete (max 5 seconds)
    console.log("Waiting for background agent execution to complete...");
    let completed = false;
    for (let i = 0; i < 10; i++) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      const pollRes = await fetch(`${serverUrl}/api/v1/runs/${runId}/tasks`);
      const pollTasks = await pollRes.json();
      const pollTask = pollTasks.find((t: any) => t.id === taskId);
      if (pollTask && pollTask.status === "completed") {
        completed = true;
        break;
      }
    }

    if (!completed) {
      blockers.push(`Background task ${taskId} failed to complete in allotted time.`);
      writeReportAndExit();
      return;
    }

    console.log("Background agent execution completed successfully.");

    // F. Verify evidence artifact was written and registered in SQLite
    console.log("Verifying evidence artifact...");
    const artRes = await fetch(`${serverUrl}/api/v1/runs/${runId}/artifacts`);
    const artifacts = await artRes.json();
    const targetArt = artifacts.find((a: any) => a.name === `agent_run_${runId}.json`);

    if (!targetArt) {
      blockers.push(`Evidence artifact 'agent_run_${runId}.json' not registered in run.`);
    } else {
      // Check physical file existence
      const localEvidencePath = path.join("artifacts/evidence", `agent_run_${runId}.json`);
      if (!fs.existsSync(localEvidencePath)) {
        blockers.push(`Physical evidence file not found at ${localEvidencePath}.`);
      } else {
        const fileContent = JSON.parse(fs.readFileSync(localEvidencePath, "utf8"));
        if (fileContent.run_id !== runId) {
          blockers.push(`Artifact json run_id '${fileContent.run_id}' does not match expected run_id '${runId}'.`);
        }
      }
    }

    // G. Verify audit event exists in ledger
    console.log("Verifying ledger audit trail...");
    const auditRes = await fetch(`${serverUrl}/api/audit/events`);
    const auditEvents = await auditRes.json();
    const event = auditEvents.find((e: any) => e.run_id === runId && e.action === "HOCHSTER_AGENT_EXECUTION_COMPLETED");

    if (!event) {
      blockers.push(`Ledger is missing audit event 'HOCHSTER_AGENT_EXECUTION_COMPLETED' for run ${runId}.`);
    } else {
      if (event.approval_state !== "approved") {
        blockers.push(`Expected audit event approval_state to be 'approved', got '${event.approval_state}'.`);
      }
      if (event.execution_state !== "completed") {
        blockers.push(`Expected audit event execution_state to be 'completed', got '${event.execution_state}'.`);
      }
    }

  } catch (err: any) {
    blockers.push(`Unexpected connection or runtime error during API E2E validation: ${err.message}`);
  }

  writeReportAndExit();
}

function writeReportAndExit() {
  const reportPath = "artifacts/qa/agent-spawn-runtime-contract-report.json";
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });

  const report = {
    generated_at: new Date().toISOString(),
    status: blockers.length === 0 ? "PASS" : "BLOCK",
    blockers,
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report, null, 2));

  if (blockers.length > 0) {
    console.error("Agent Spawn Runtime Contract FAILED!");
    process.exit(1);
  } else {
    console.log("Agent Spawn Runtime Contract PASSED!");
    process.exit(0);
  }
}

runContractTest();
