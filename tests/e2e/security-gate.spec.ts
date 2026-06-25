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

  test("asserts the full chain with browser interaction and database state checks", async ({ page, request }) => {
    // 1. Navigate to the dashboard
    await page.goto("/", { waitUntil: "networkidle" });

    // 2. Click "NEW RUN" button to launch a run
    const newRunBtn = page.locator("#btn-create-run");
    await expect(newRunBtn).toBeVisible();
    await newRunBtn.click();

    // Wait for run selector to have a value (meaning the run was created and selected)
    const runSelector = page.locator("#run-selector");
    await expect(runSelector).not.toHaveValue("");
    const runId = await runSelector.inputValue();
    expect(runId).toBeDefined();
    expect(runId).not.toBeNull();

    // Assert database state: backend creates run row in DB
    const getRunResponse = await request.get(`/api/v1/runs`);
    expect(getRunResponse.ok()).toBeTruthy();
    const runs = await getRunResponse.json();
    const dbRun = runs.find((r: any) => r.run_id === runId);
    expect(dbRun).toBeDefined();
    expect(dbRun.status).toBe("running");

    // 3. Click "START EXECUTION" to start the run
    const startBtn = page.locator("#btn-start-run");
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // Assert database state: task row pending/running
    let t0Status = "";
    let maxPoll = 15;
    while (maxPoll > 0) {
      const tasksResp = await request.get(`/api/v1/runs/${runId}/tasks`);
      if (tasksResp.ok()) {
        const tasks = await tasksResp.json();
        const t0 = tasks.find((t: any) => t.id === "T0-RECON");
        if (t0 && (t0.status === "running" || t0.status === "completed")) {
          t0Status = t0.status;
          break;
        }
      }
      await page.waitForTimeout(500);
      maxPoll--;
    }
    expect(["running", "completed"]).toContain(t0Status);

    // 4. Poll until approval gate row is created (T2-SPEC becomes blocked_pending_approval)
    let approvalRequest: any = null;
    maxPoll = 30;
    while (maxPoll > 0) {
      const tasksResp = await request.get(`/api/v1/runs/${runId}/tasks`);
      if (tasksResp.ok()) {
        const tasks = await tasksResp.json();
        const t2 = tasks.find((t: any) => t.id === "T2-SPEC");
        if (t2 && t2.status === "blocked_pending_approval") {
          const approvalsResp = await request.get("/api/approval/requests");
          if (approvalsResp.ok()) {
            const approvals = await approvalsResp.json();
            approvalRequest = approvals.find((a: any) => a.command?.command_id === `cmd-T2-SPEC` && a.target?.id === runId);
            if (approvalRequest && approvalRequest.status === "pending") {
              break;
            }
          }
        }
      }
      await page.waitForTimeout(500);
      maxPoll--;
    }
    expect(approvalRequest).toBeDefined();
    expect(approvalRequest.status).toBe("pending");

    // Verify that the UI displays the task as blocked in the task flow grid
    // Verify that the Human Operator Approval Queue renders the request
    const approvalItem = page.locator(`#approval-queue-list div:has-text("Approval Request")`);
    await expect(approvalItem.first()).toBeVisible();

    // 5. Operator approves all tasks that require approval via the UI
    let runFinalStatus = "";
    maxPoll = 60; // 60 seconds limit
    while (maxPoll > 0) {
      const runStatusText = await page.locator("#run-status-text").textContent();
      if (runStatusText && runStatusText.toLowerCase().includes("completed")) {
        runFinalStatus = runStatusText;
        break;
      }

      // If there's an approval button visible in the queue, click it
      const count = await approvalItem.count();
      if (count > 0) {
        const approveBtn = approvalItem.first().getByRole("button", { name: "APPROVE" });
        if (await approveBtn.isVisible()) {
          await approveBtn.click();
        }
      }

      await page.waitForTimeout(1000);
      maxPoll--;
    }
    expect(runFinalStatus.toLowerCase()).toContain("completed");

    // Assert database state: artifact row created for T2-SPEC (prd.md)
    const artifactsResp = await request.get(`/api/v1/runs/${runId}/artifacts`);
    expect(artifactsResp.ok()).toBeTruthy();
    const artifacts = await artifactsResp.json();
    const prdArtifact = artifacts.find((a: any) => a.name === "prd.md");
    expect(prdArtifact).toBeDefined();
    expect(prdArtifact.status).toBe("completed");
  });
});
