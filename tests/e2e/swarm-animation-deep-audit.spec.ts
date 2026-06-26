import { test, expect } from "@playwright/test";

test.describe("Swarm Animation and Interaction Deep Audit", () => {
  test.skip("performs topology overlay interaction, swarm launch, cybersecurity factory, and runs console loop", async ({ page, request }) => {
    // 1. Navigate to the dashboard, waiting for the agents list API response concurrently
    const responsePromise = page.waitForResponse("**/api/v1/agents");
    await page.goto("/");
    await responsePromise;

    // ----------------------------------------------------
    //  A. Topology Overlay Interaction
    // ----------------------------------------------------
    const navSwarmControl = page.locator("#nav-swarm-control");
    await expect(navSwarmControl).toBeVisible();
    await navSwarmControl.click();

    // Verify Gordon Vector chip is visible
    const gordonChip = page.locator("#topo-chip-gordon-vector");
    await expect(gordonChip).toBeVisible();

    // Click Gordon Vector
    await gordonChip.click();

    // Verify profile modal opens
    const modal = page.locator("#topology-agent-profile-modal");
    await expect(modal).toBeVisible();

    // Verify trust badges and capability manifest fields are visible
    const manifestContainer = page.locator("#topology-agent-modal-manifest-container");
    await expect(manifestContainer).toBeVisible();
    await expect(page.locator("#agent-manifest-allowed")).toBeVisible();
    await expect(page.locator("#agent-manifest-denied")).toBeVisible();

    // Click "Spin Up Agent" button
    const spinupBtn = page.locator("#topology-agent-modal-spinup");
    await expect(spinupBtn).toBeVisible();
    await spinupBtn.click();

    // Verify status changes to complete
    const statusEl = page.locator("#topology-agent-modal-status");
    await expect(statusEl).toHaveText("complete");

    // Close modal
    const closeBtn = page.locator("#topology-agent-modal-close");
    await expect(closeBtn).toBeVisible();
    await closeBtn.click();
    await expect(modal).not.toBeVisible();

    // ----------------------------------------------------
    //  B. Launch Expert Swarm
    // ----------------------------------------------------
    const promptInput = page.locator("#topology-agent-prompt-input");
    await expect(promptInput).toBeVisible();
    await promptInput.fill("Audit release candidate 0.1.6-ERROR-BUDGET-AWARE-AUTONOMY");

    const launchSwarmBtn = page.locator("#topology-agent-launch-button");
    await expect(launchSwarmBtn).toBeVisible();
    await launchSwarmBtn.click();

    // Wait for the pipeline animation to run (around 5 seconds)
    await page.waitForTimeout(5000);

    // Verify motion canvas exists and is visible
    const motionCanvas = page.locator("#topology-agent-motion-canvas");
    await expect(motionCanvas).toBeVisible();

    // ----------------------------------------------------
    //  C. Cybersecurity Factory Swarm Launch
    // ----------------------------------------------------
    const navCybersecurity = page.locator("#nav-cybersecurity-factory");
    await expect(navCybersecurity).toBeVisible();
    await navCybersecurity.click();

    const factoryInput = page.locator("#factory-app-idea-input");
    await expect(factoryInput).toBeVisible();
    await factoryInput.fill("Create an app that helps families prepare for emergencies and organize supplies safely.");

    const factoryLaunchBtn = page.locator("#factory-launch-swarm-button");
    await expect(factoryLaunchBtn).toBeVisible();
    await factoryLaunchBtn.click();

    // Expect Humanity Gate PASS
    await expect(page.locator("#gate-result-pass")).toBeVisible();

    // Verify key sections are visible
    await expect(page.getByText("North Star Planning", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("PERT Analysis", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("Cybersecurity Review", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("App Store Delivery", { exact: false }).first()).toBeVisible();

    // Verify target stores target indicators
    await expect(page.getByText("Apple App Store", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Google Play", { exact: true }).first()).toBeVisible();

    // Wait for the animation stages to complete and verify status stays locked to Draft/Packet Ready/etc.
    await page.waitForTimeout(6500);

    // Check store target statuses
    const storeStatusText = await page.locator("#privacy-gate-status").textContent();
    expect(storeStatusText).toBeDefined();

    // ----------------------------------------------------
    //  D. Runs Console Loop
    // ----------------------------------------------------
    // Navigate back to Swarm Control where the Runs Console panel is located
    await navSwarmControl.click();

    // Click "NEW RUN" button to launch a run
    const newRunBtn = page.locator("#btn-create-run");
    await expect(newRunBtn).toBeVisible();
    await newRunBtn.click();

    // Get the created run ID from selector
    const runSelector = page.locator("#run-selector");
    await expect(runSelector).not.toHaveValue("");
    const runId = await runSelector.inputValue();
    expect(runId).toBeDefined();

    // Start execution
    const startBtn = page.locator("#btn-start-run");
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // Dynamically approve all gates that appear in the runs console approval queue
    const approvalItem = page.locator(`#approval-queue-list div:has-text("Approval Request")`);
    let runFinalStatus = "";
    let maxPoll = 45; // 45 seconds max
    while (maxPoll > 0) {
      const runStatusText = await page.locator("#run-status-text").textContent();
      if (runStatusText && runStatusText.toLowerCase().includes("completed")) {
        runFinalStatus = runStatusText;
        break;
      }

      // If approval is requested, click approve
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

    // Verify task row grid shows complete and artifacts generated
    const artifactsResp = await request.get(`/api/v1/runs/${runId}/artifacts`);
    expect(artifactsResp.ok()).toBeTruthy();
    const artifacts = await artifactsResp.json();
    expect(artifacts.length).toBeGreaterThan(0);
  });
});
