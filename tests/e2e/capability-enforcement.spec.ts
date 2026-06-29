import { test, expect } from "@playwright/test";
import { execSync } from "child_process";

test.describe("@legacy @compat @deorbited Capability Enforcement E2E", () => {
  test.afterAll(async () => {
    // Restore manifest database changes just in case
    try {
      execSync(`sqlite3 backend/swarm_ledger.db "UPDATE agent_capability_manifests SET denied_tools = '[]' WHERE agent_id = 'repo-recon-agent'"`);
    } catch (e) {
      console.warn("Failed to restore repo-recon-agent manifest:", e);
    }
  });

  test("runs capability allowed, blocked, and approval flow", async ({ request }) => {
    // 1. Create a run
    const createRunResponse = await request.post("/api/v1/runs", {
      data: { name: "Capability E2E Test Run" }
    });
    expect(createRunResponse.ok()).toBeTruthy();
    const run = await createRunResponse.json();
    const runId = run.run_id;
    expect(runId).toBeDefined();

    // 2. Execute T0-RECON (allowed)
    const execT0 = await request.post(`/api/v1/runs/${runId}/tasks/T0-RECON/execute`);
    expect(execT0.ok()).toBeTruthy();

    // Verify capability GET endpoint lists decisions
    let capAllowed = false;
    let maxPoll = 15;
    while (maxPoll > 0) {
      const capResp = await request.get(`/api/v1/agents/repo-recon-agent/capability`);
      expect(capResp.ok()).toBeTruthy();
      const capData = await capResp.json();
      const decisions = capData.last_decisions || [];
      const dec = decisions.find((d: any) => d.tool === "research" && d.allowed === true);
      if (dec) {
        capAllowed = true;
        break;
      }
      await new Promise(r => setTimeout(r, 500));
      maxPoll--;
    }
    expect(capAllowed).toBe(true);

    // 3. Poll T2-SPEC until it gets blocked_pending_approval
    let approvalId = "";
    maxPoll = 15;
    while (maxPoll > 0) {
      const approvalsResp = await request.get("/api/approval/requests");
      expect(approvalsResp.ok()).toBeTruthy();
      const approvals = await approvalsResp.json();
      const relevant = approvals.find((a: any) => a.command?.command_id === "cmd-T2-SPEC" && a.target?.id === runId);
      if (relevant) {
        approvalId = relevant.approval_id;
        break;
      }
      await new Promise(r => setTimeout(r, 500));
      maxPoll--;
    }
    expect(approvalId).not.toBe("");

    // Verify capability GET endpoint lists decisions for T2-SPEC (APPROVAL_REQUIRED)
    const capResp = await request.get(`/api/v1/agents/product-strategy-agent/capability`);
    expect(capResp.ok()).toBeTruthy();
    const capData = await capResp.json();
    const specDecision = capData.last_decisions.find((d: any) => d.tool === "write_spec");
    expect(specDecision).toBeDefined();
    expect(specDecision.decision).toBe("APPROVAL_REQUIRED");

    // 4. Submit approval decision
    const approveResp = await request.post(`/api/approval/requests/${approvalId}/decisions`, {
      data: {
        decision: "approve",
        approver: "Operator",
        timestamp: new Date().toISOString()
      }
    });
    expect(approveResp.ok()).toBeTruthy();

    // 5. Verify duplicate approvals still blocked (returns 400)
    const dupResp = await request.post(`/api/approval/requests/${approvalId}/decisions`, {
      data: {
        decision: "approve",
        approver: "Operator",
        timestamp: new Date().toISOString()
      }
    });
    expect(dupResp.status()).toBe(400);

    // 6. Simulate a denied tool request: UPDATE sqlite database to deny research tool for repo-recon-agent
    execSync(`sqlite3 backend/swarm_ledger.db "UPDATE agent_capability_manifests SET denied_tools = '[\\\"research\\\"]' WHERE agent_id = 'repo-recon-agent'"`);

    // Create a new run to execute T0-RECON with denied tool
    const createRun2 = await request.post("/api/v1/runs", {
      data: { name: "Denied Capability Test Run" }
    });
    expect(createRun2.ok()).toBeTruthy();
    const run2 = await createRun2.json();
    const runId2 = run2.run_id;

    // Execute T0-RECON (will be blocked now)
    const execT0_2 = await request.post(`/api/v1/runs/${runId2}/tasks/T0-RECON/execute`);
    expect(execT0_2.ok()).toBeTruthy();

    // Poll until T0-RECON is blocked
    let t0Blocked = false;
    maxPoll = 15;
    while (maxPoll > 0) {
      const getTasksResponse = await request.get(`/api/v1/runs/${runId2}/tasks`);
      expect(getTasksResponse.ok()).toBeTruthy();
      const tasks = await getTasksResponse.json();
      const t0 = tasks.find((t: any) => t.id === "T0-RECON");
      if (t0 && t0.status === "blocked") {
        t0Blocked = true;
        break;
      }
      await new Promise(r => setTimeout(r, 500));
      maxPoll--;
    }
    expect(t0Blocked).toBe(true);

    // Verify artifact/evidence record includes evidence_type capability_enforcement
    const artifactsResp = await request.get(`/api/v1/runs/${runId2}/artifacts`);
    expect(artifactsResp.ok()).toBeTruthy();
    const artifacts = await artifactsResp.json();
    const capArt = artifacts.find((a: any) => a.evidence_type === "capability_enforcement");
    expect(capArt).toBeDefined();
    expect(capArt.signature_status).toBe("unsigned");
  });
});
