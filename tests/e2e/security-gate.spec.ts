import { test, expect } from "@playwright/test";

test.describe("Security Gate E2E Regression", () => {
  test("asserts that approval-required tasks block and resume correctly on operator decisions", async ({ request }) => {
    // 1. Create a new Swarm run
    const createRunResponse = await request.post("/api/v1/runs", {
      data: { name: "Security Gate Test Run" }
    });
    expect(createRunResponse.ok()).toBeTruthy();
    const run = await createRunResponse.json();
    const runId = run.run_id;
    expect(runId).toBeDefined();

    // Verify task T2-SPEC is in the list of tasks and requires approval
    const tasksBefore = run.tasks;
    const t2Spec = tasksBefore.find((t: any) => t.id === "T2-SPEC");
    expect(t2Spec).toBeDefined();
    expect(t2Spec.approvalRequired).toBe(true);

    // Verify no artifacts exist for this run
    const artifactsResponse = await request.get(`/api/v1/runs/${runId}/artifacts`);
    expect(artifactsResponse.ok()).toBeTruthy();
    const artifactsBefore = await artifactsResponse.json();
    expect(artifactsBefore.length).toBe(0);

    // 2. Start the run by executing T0-RECON
    const executeT0Response = await request.post(`/api/v1/runs/${runId}/tasks/T0-RECON/execute`);
    expect(executeT0Response.ok()).toBeTruthy();

    // 3. Poll tasks until T2-SPEC is blocked pending approval
    // T0-RECON (1.5s) -> T1-ROSTER-PLAN (1.5s) -> T2-SPEC (blocked_pending_approval)
    // Total simulated time is ~3 seconds, so we poll for up to 10 seconds.
    let t2Status = "";
    let maxPoll = 25;
    while (maxPoll > 0) {
      const getTasksResponse = await request.get(`/api/v1/runs/${runId}/tasks`);
      expect(getTasksResponse.ok()).toBeTruthy();
      const tasks = await getTasksResponse.json();
      const t2 = tasks.find((t: any) => t.id === "T2-SPEC");
      t2Status = t2.status;
      if (t2Status === "blocked_pending_approval") {
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 500));
      maxPoll--;
    }
    expect(t2Status).toBe("blocked_pending_approval");

    // 4. Assert that no artifact for T2-SPEC (prd.md) has been generated
    const artifactsMidResponse = await request.get(`/api/v1/runs/${runId}/artifacts`);
    expect(artifactsMidResponse.ok()).toBeTruthy();
    const artifactsMid = await artifactsMidResponse.json();
    const prdArtifact = artifactsMid.find((a: any) => a.name === "prd.md");
    expect(prdArtifact).toBeUndefined();

    // 5. Verify the approval request is visible in the queue
    const getApprovalsResponse = await request.get("/api/approval/requests");
    expect(getApprovalsResponse.ok()).toBeTruthy();
    const approvals = await getApprovalsResponse.json();
    const relevantApproval = approvals.find((a: any) => a.command?.command_id === `cmd-T2-SPEC` && a.target?.id === runId);
    expect(relevantApproval).toBeDefined();
    expect(relevantApproval.status).toBe("pending");
    const approvalId = relevantApproval.approval_id;

    // 6. Submit an approved decision
    const submitDecisionResponse = await request.post(`/api/approval/requests/${approvalId}/decisions`, {
      data: {
        decision: "approve",
        approver: "Operator",
        timestamp: new Date().toISOString()
      }
    });
    expect(submitDecisionResponse.ok()).toBeTruthy();

    // 7. Verify the approval request is approved
    const getApprovalsAfterResponse = await request.get("/api/approval/requests");
    expect(getApprovalsAfterResponse.ok()).toBeTruthy();
    const approvalsAfter = await getApprovalsAfterResponse.json();
    const approvedRequest = approvalsAfter.find((a: any) => a.approval_id === approvalId);
    expect(approvedRequest.status).toBe("approved");

    // 8. Poll tasks until T2-SPEC is completed (takes 1.5s simulated run time after approval)
    let t2FinalStatus = "";
    maxPoll = 20;
    while (maxPoll > 0) {
      const getTasksResponse = await request.get(`/api/v1/runs/${runId}/tasks`);
      expect(getTasksResponse.ok()).toBeTruthy();
      const tasks = await getTasksResponse.json();
      const t2 = tasks.find((t: any) => t.id === "T2-SPEC");
      t2FinalStatus = t2.status;
      if (t2FinalStatus === "completed") {
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 500));
      maxPoll--;
    }
    expect(t2FinalStatus).toBe("completed");

    // 9. Verify the artifact (prd.md) has been generated
    const artifactsAfterResponse = await request.get(`/api/v1/runs/${runId}/artifacts`);
    expect(artifactsAfterResponse.ok()).toBeTruthy();
    const artifactsAfter = await artifactsAfterResponse.json();
    const finalPrdArtifact = artifactsAfter.find((a: any) => a.name === "prd.md");
    expect(finalPrdArtifact).toBeDefined();
    expect(finalPrdArtifact.status).toBe("completed");
  });
});
