import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

function runBuilderRunnerTests() {
  console.log("==================================================");
  console.log("HOCH BUILDER RUNNER CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const runnerScript = path.join(baseDir, 'scripts/orchestrator/builder_runner.py');
  const registryPath = path.join(baseDir, 'control/phase_registry.json');
  const statePath = path.join(baseDir, 'control/phase_state.json');
  const decisionsDir = path.join(baseDir, 'artifacts/approvals/decisions');
  const mainPyPath = path.join(baseDir, 'backend/main.py');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Basic exist checks
  assert(fs.existsSync(runnerScript), "builder_runner.py exists");
  assert(fs.existsSync(registryPath), "phase_registry.json exists");
  assert(fs.existsSync(statePath), "phase_state.json exists");

  // Read current registry/state to restore them later
  const originalRegistry = fs.readFileSync(registryPath, 'utf-8');
  const originalState = fs.readFileSync(statePath, 'utf-8');

  // Ensure decisions directory exists
  if (!fs.existsSync(decisionsDir)) {
    fs.mkdirSync(decisionsDir, { recursive: true });
  }

  // Find and back up any existing PR16 decisions
  const decisionBackup: { [file: string]: string } = {};
  fs.readdirSync(decisionsDir).forEach(file => {
    if (file.startsWith("decision_") && file.endsWith(".json")) {
      const full = path.join(decisionsDir, file);
      const content = fs.readFileSync(full, 'utf-8');
      if (content.toLowerCase().includes("pr16")) {
        decisionBackup[file] = content;
        fs.unlinkSync(full); // Temporarily remove to test unapproved block
      }
    }
  });

  // Ensure no PR16 approved decision exists in queue.json as well
  const queuePath = path.join(baseDir, 'artifacts/approvals/queue.json');
  let originalQueue = "";
  if (fs.existsSync(queuePath)) {
    originalQueue = fs.readFileSync(queuePath, 'utf-8');
    try {
      const queueObj = JSON.parse(originalQueue);
      queueObj.approvals = queueObj.approvals.filter((app: any) => 
        !(app.task_description && app.task_description.toLowerCase().includes("pr16"))
      );
      fs.writeFileSync(queuePath, JSON.stringify(queueObj, null, 2), 'utf-8');
    } catch (e) {}
  }

  // Restore registry next_phase to PR16 if it progressed
  try {
    const regObj = JSON.parse(originalRegistry);
    regObj.next_phase = "PR16";
    fs.writeFileSync(registryPath, JSON.stringify(regObj, null, 2), 'utf-8');
  } catch (e) {}

  // 2. Test unapproved execution block
  console.log("[test] Running builder runner without operator approval...");
  try {
    execSync(`python3 ${runnerScript}`, { cwd: baseDir, stdio: 'pipe' });
    assert(false, "builder_runner.py should exit non-zero when unapproved");
  } catch (err: any) {
    const output = err.stdout?.toString() || "" + err.stderr?.toString() || "";
    assert(err.status !== 0, "builder_runner.py exited non-zero when unapproved");
    assert(output.includes("PENDING operator approval"), "Logs contain PENDING operator approval warning");
  }

  // 3. Write mock approved decision
  const mockDecisionFile = path.join(decisionsDir, 'decision_mock_pr16.json');
  const mockDecision = {
    approval_id: "app-mockpr16",
    status: "APPROVED",
    task_description: "Execute phase PR16 prompt and compile local evidence plan",
    created_at: new Date().toISOString(),
    decision_at: new Date().toISOString()
  };
  fs.writeFileSync(mockDecisionFile, JSON.stringify(mockDecision, null, 2), 'utf-8');

  // 4. Test approved execution success
  console.log("[test] Running builder runner with operator approval...");
  try {
    const stdout = execSync(`python3 ${runnerScript}`, { cwd: baseDir, stdio: 'pipe' }).toString();
    assert(stdout.includes("Commencing execution for PR16"), "Logs show execution started");
    assert(stdout.includes("Successfully completed phase PR16"), "Logs show execution succeeded");
    
    // Verify output files exist
    const evidenceDir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');
    assert(fs.existsSync(path.join(evidenceDir, 'production_cutover_plan.md')), "production_cutover_plan.md created");
    assert(fs.existsSync(path.join(evidenceDir, 'production_cutover_manifest.json')), "production_cutover_manifest.json created");
    assert(fs.existsSync(path.join(evidenceDir, 'pr16_final_seal.json')), "pr16_final_seal.json created");

    // Verify registry advanced
    const advancedReg = JSON.parse(fs.readFileSync(registryPath, 'utf-8'));
    assert(advancedReg.last_completed_phase === "PR16", "last_completed_phase advanced to PR16");
    assert(advancedReg.next_phase === "PR17", "next_phase advanced to PR17");

  } catch (err: any) {
    console.error(err.stdout?.toString() || "");
    console.error(err.stderr?.toString() || "");
    assert(false, "builder_runner.py failed to execute successfully with approval");
  }

  // 5. Clean up mock decisions and restore backups
  if (fs.existsSync(mockDecisionFile)) {
    fs.unlinkSync(mockDecisionFile);
  }
  Object.keys(decisionBackup).forEach(file => {
    fs.writeFileSync(path.join(decisionsDir, file), decisionBackup[file], 'utf-8');
  });
  if (originalQueue) {
    fs.writeFileSync(queuePath, originalQueue, 'utf-8');
  }

  // Restore original registry and state
  fs.writeFileSync(registryPath, originalRegistry, 'utf-8');
  fs.writeFileSync(statePath, originalState, 'utf-8');

  // Clean up any generated PR16 output files
  const evidenceDir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');
  ['production_cutover_plan.md', 'production_cutover_manifest.json', 'pr16_final_seal.json'].forEach(f => {
    const full = path.join(evidenceDir, f);
    if (fs.existsSync(full)) {
      fs.unlinkSync(full);
    }
  });

  // 6. Verify main.py endpoints
  const pyContent = fs.readFileSync(mainPyPath, 'utf-8');
  assert(pyContent.includes('/api/v1/orchestrator/execute-phase'), "FastAPI serves execute-phase endpoint");
  assert(pyContent.includes('/api/v1/orchestrator/request-execution'), "FastAPI serves request-execution endpoint");

  console.log("==================================================");
  if (failed) {
    console.error("HOCH BUILDER RUNNER CONTRACT CHECK FAILED");
    process.exit(1);
  } else {
    console.log("HOCH BUILDER RUNNER CONTRACT CHECK PASSED");
    process.exit(0);
  }
}

runBuilderRunnerTests();
