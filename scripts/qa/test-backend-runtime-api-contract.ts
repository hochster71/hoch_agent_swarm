import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";

async function runApiContractTest() {
  console.log("==================================================");
  console.log("STARTING BACKEND RUNTIME API CONTRACT AUDIT");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];

  try {
    // 1. GET /api/status
    console.log("Testing GET /api/status...");
    const statusResp = await fetch(`${BASE_URL}/api/status`);
    if (statusResp.status !== 200) {
      errors.push(`GET /api/status returned status ${statusResp.status}`);
    } else {
      const statusData = await statusResp.json();
      findings.push("GET /api/status: 200 OK");
      if (statusData && statusData.nodes) {
        findings.push(`GET /api/status contains nodes list (count: ${statusData.nodes.length})`);
      } else {
        errors.push("GET /api/status payload did not contain nodes list");
      }
    }

    // 2. GET /api/v1/agents
    console.log("Testing GET /api/v1/agents...");
    const agentsResp = await fetch(`${BASE_URL}/api/v1/agents`);
    let agents: any[] = [];
    if (agentsResp.status !== 200) {
      errors.push(`GET /api/v1/agents returned status ${agentsResp.status}`);
    } else {
      agents = await agentsResp.json();
      findings.push(`GET /api/v1/agents: 200 OK, fetched ${agents.length} agents`);
      
      // Verify capability manifest fields on agents
      let manifestsChecked = 0;
      let manifestsEnforced = 0;
      agents.forEach((agent) => {
        if (!agent.capability) {
          errors.push(`Agent ${agent.id} (${agent.displayName}) is missing capability manifest object`);
        } else {
          manifestsChecked++;
          const cap = agent.capability;
          const requiredFields = [
            "allowed_tools",
            "denied_tools",
            "file_scopes",
            "network_scopes",
            "approval_threshold",
            "risk_class"
          ];
          requiredFields.forEach((field) => {
            if (!(field in cap)) {
              errors.push(`Agent ${agent.id} capability manifest is missing field: ${field}`);
            }
          });
          if (cap.allowed_tools && cap.denied_tools) {
            manifestsEnforced++;
          }
        }
      });
      findings.push(`Verified capability manifests for ${manifestsChecked}/${agents.length} agents`);
    }

    // 3. GET /api/v1/runs
    console.log("Testing GET /api/v1/runs...");
    const runsResp = await fetch(`${BASE_URL}/api/v1/runs`);
    if (runsResp.status !== 200) {
      errors.push(`GET /api/v1/runs returned status ${runsResp.status}`);
    } else {
      const runs = await runsResp.json();
      findings.push(`GET /api/v1/runs: 200 OK, current run count: ${runs.length}`);
    }

    // 4. POST /api/v1/runs
    console.log("Testing POST /api/v1/runs...");
    const createRunResp = await fetch(`${BASE_URL}/api/v1/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "API Contract Verification Run" })
    });
    let runId = "";
    if (createRunResp.status !== 200) {
      errors.push(`POST /api/v1/runs returned status ${createRunResp.status}`);
    } else {
      const runData = await createRunResp.json();
      runId = runData.run_id;
      findings.push(`POST /api/v1/runs: 200 OK, created run_id: ${runId}`);
      if (!runId) {
        errors.push("POST /api/v1/runs response did not contain a valid run_id");
      }
    }

    if (runId) {
      // 5. GET /api/v1/runs/{run_id}/tasks
      console.log(`Testing GET /api/v1/runs/${runId}/tasks...`);
      const tasksResp = await fetch(`${BASE_URL}/api/v1/runs/${runId}/tasks`);
      if (tasksResp.status !== 200) {
        errors.push(`GET /api/v1/runs/${runId}/tasks returned status ${tasksResp.status}`);
      } else {
        const tasks = await tasksResp.json();
        findings.push(`GET /api/v1/runs/${runId}/tasks: 200 OK, retrieved ${tasks.length} tasks`);
        const hasT2 = tasks.some((t: any) => t.id === "T2-SPEC");
        if (!hasT2) {
          errors.push("Run task list does not contain expected T2-SPEC task");
        }
      }

      // 6. GET /api/v1/runs/{run_id}/artifacts
      console.log(`Testing GET /api/v1/runs/${runId}/artifacts...`);
      const artifactsResp = await fetch(`${BASE_URL}/api/v1/runs/${runId}/artifacts`);
      if (artifactsResp.status !== 200) {
        errors.push(`GET /api/v1/runs/${runId}/artifacts returned status ${artifactsResp.status}`);
      } else {
        const artifacts = await artifactsResp.json();
        findings.push(`GET /api/v1/runs/${runId}/artifacts: 200 OK, retrieved ${artifacts.length} artifacts`);
      }

      // 7. GET /api/approval/requests
      console.log("Testing GET /api/approval/requests...");
      const approvalsResp = await fetch(`${BASE_URL}/api/approval/requests`);
      let initialApprovals: any[] = [];
      if (approvalsResp.status !== 200) {
        errors.push(`GET /api/approval/requests returned status ${approvalsResp.status}`);
      } else {
        initialApprovals = await approvalsResp.json();
        findings.push(`GET /api/approval/requests: 200 OK, initial approvals count: ${initialApprovals.length}`);
      }

      // 8. POST /api/v1/runs/{run_id}/tasks/T0-RECON/execute (Starts the run to propagate to T2-SPEC)
      console.log("Dispatching execution for T0-RECON (starts the run)...");
      const executeT0Resp = await fetch(`${BASE_URL}/api/v1/runs/${runId}/tasks/T0-RECON/execute`, {
        method: "POST"
      });
      if (executeT0Resp.status !== 200) {
        errors.push(`POST execute T0-RECON returned status ${executeT0Resp.status}`);
      } else {
        findings.push("POST execute T0-RECON: dispatched successfully");
      }

      // 9. Poll approvals list until a pending approval request is created (up to 8 seconds)
      console.log("Polling for created approval request (T2-SPEC requires approval)...");
      let approvalId = "";
      let pollCount = 16; // 8 seconds total (16 * 500ms)
      while (pollCount > 0) {
        const approvalsResp2 = await fetch(`${BASE_URL}/api/approval/requests`);
        if (approvalsResp2.status === 200) {
          const approvals = await approvalsResp2.json();
          const newApproval = approvals.find((a: any) => a.approval_id && a.status === "pending");
          if (newApproval) {
            approvalId = newApproval.approval_id;
            findings.push(`Found pending approval request: ${approvalId} after ${8 - pollCount * 0.5}s`);
            break;
          }
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
        pollCount--;
      }

      if (!approvalId) {
        errors.push("Failed to find the pending approval request for T2-SPEC after execution propagation");
      }

      if (approvalId) {
        // 10. POST /api/approval/requests/{approval_id}/decisions (First Decision)
        console.log(`Submitting decision for approval_id: ${approvalId}...`);
        const decisionResp1 = await fetch(`${BASE_URL}/api/approval/requests/${approvalId}/decisions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision: "approve", operator: "Contract Audit Operator" })
        });
        if (decisionResp1.status !== 200) {
          errors.push(`POST /api/approval/requests/${approvalId}/decisions (first submission) returned status ${decisionResp1.status}`);
        } else {
          const decisionData = await decisionResp1.json();
          findings.push("POST /api/approval/requests/{approval_id}/decisions (first submission): 200 OK");
          
          // Verify presence of nonce & signature/hash evidence in the decisions array
          const approvalsCheck = await fetch(`${BASE_URL}/api/approval/requests`);
          const apps = await approvalsCheck.json();
          const targetApp = apps.find((a: any) => a.approval_id === approvalId);
          if (targetApp && targetApp.decisions && targetApp.decisions.length > 0) {
            const dec = targetApp.decisions[0];
            if (dec.nonce && dec.decision_id) {
              findings.push(`Replay protection check: Found nonce (${dec.nonce}) and decision_id (${dec.decision_id})`);
            } else {
              errors.push("Replay protection failure: nonce or decision_id missing in decision metadata");
            }
          }
        }

        // 11. POST /api/approval/requests/{approval_id}/decisions (Second Duplicate Decision - Should be blocked)
        console.log(`Testing replay protection for approval_id: ${approvalId}...`);
        const decisionResp2 = await fetch(`${BASE_URL}/api/approval/requests/${approvalId}/decisions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision: "approve", operator: "Contract Audit Operator" })
        });
        if (decisionResp2.status === 400) {
          const blockData = await decisionResp2.json();
          if (blockData.detail && blockData.detail.toLowerCase().includes("replay blocked")) {
            findings.push(`Replay protection confirmed: Second submission blocked with 400 Bad Request. Detail: "${blockData.detail}"`);
          } else {
            errors.push(`Second submission returned 400 but detail did not mention replay blocking: "${JSON.stringify(blockData)}"`);
          }
        } else {
          errors.push(`Replay protection failure: Second decision submission did not return 400 (returned status: ${decisionResp2.status})`);
        }
      }
    }
  } catch (err: any) {
    errors.push(`Exception in API contract tests: ${err.message}`);
  }

  writeReport(errors, findings);
}

function writeReport(errors: string[], findings: string[]) {
  const status = errors.length === 0 ? "PASS" : "FAIL";
  const report = {
    generated_at: new Date().toISOString(),
    status,
    errors,
    findings
  };

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/backend-runtime-api-contract-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`Backend API Contract Audit completed with status: ${status}`);
  if (errors.length > 0) {
    console.error("Errors found:", errors);
    process.exit(1);
  } else {
    console.log("All Backend API contract checks passed!");
    process.exit(0);
  }
}

runApiContractTest();
