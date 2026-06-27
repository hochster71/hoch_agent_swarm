import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

function runPromptRegistryTests() {
  console.log("==================================================");
  console.log("PROMPT REGISTRY LOADER CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const registryFile = path.join(baseDir, 'backend/prompt_registry.py');
  const mainFile = path.join(baseDir, 'backend/main.py');
  const reportFile = path.join(baseDir, 'artifacts/qa/prompt_registry/prompt_registry_report.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify files exist
  assert(fs.existsSync(registryFile), "Registry loader file exists: backend/prompt_registry.py");
  assert(fs.existsSync(mainFile), "FastAPI main app file exists: backend/main.py");

  // 2. Verify API routes are registered in main.py
  if (fs.existsSync(mainFile)) {
    const mainContent = fs.readFileSync(mainFile, 'utf-8');
    assert(mainContent.includes('/api/v1/prompts/registry'), "Route /api/v1/prompts/registry exists in main.py");
    assert(mainContent.includes('/api/v1/prompts/registry/{prompt_id}'), "Route /api/v1/prompts/registry/{prompt_id} exists in main.py");
    assert(mainContent.includes('/api/v1/prompts/categories'), "Route /api/v1/prompts/categories exists in main.py");
    
    // Ensure no execution endpoints are registered
    const hasExecutionEndpoint = mainContent.includes('/api/v1/prompts/execute') ||
                                 mainContent.includes('/api/v1/prompts/run') ||
                                 mainContent.includes('/api/v1/prompts/kickoff') ||
                                 mainContent.includes('/api/v1/prompts/evaluate/execute');
    assert(!hasExecutionEndpoint, "Safety check: No prompt execution/kickoff endpoints are registered in this phase");
  }

  // 3. Compile backend files to verify syntax
  try {
    execSync('python3 -m py_compile backend/main.py backend/prompt_registry.py', { cwd: baseDir });
    assert(true, "Python syntax and import validation successful");
  } catch (e: any) {
    assert(false, `Python compile/import failed: ${e.message}`);
  }

  // 4. Force registry initialization via python subprocess to write the report
  try {
    execSync('python3 -c "from backend.prompt_registry import get_registry; get_registry()"', { cwd: baseDir });
    assert(true, "Successfully initialized PromptRegistry and wrote report");
  } catch (e: any) {
    assert(false, `Failed to initialize PromptRegistry: ${e.message}`);
  }

  // 5. Verify the report exists and has the expected values
  assert(fs.existsSync(reportFile), "Report exists: artifacts/qa/prompt_registry/prompt_registry_report.json");
  if (fs.existsSync(reportFile)) {
    try {
      const report = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
      assert(report.status === 'LIVE', `Registry status is '${report.status}' (expected 'LIVE')`);
      assert(report.total_prompts >= 100, `Total prompts count is ${report.total_prompts} (expected >= 100)`);
      assert(report.security_critical_count > 0, `Security critical prompts count is ${report.security_critical_count} (expected > 0)`);
      assert(report.approval_gated_count > 0, `Approval gated prompts count is ${report.approval_gated_count} (expected > 0)`);
      assert(report.categories && Object.keys(report.categories).length > 0, "Categories count is non-empty");
      assert(report.industries && Object.keys(report.industries).length > 0, "Industries count is non-empty");
    } catch (e: any) {
      assert(false, `Report parsing/validation failed: ${e.message}`);
    }
  }

  // 6. Verify known prompt IDs exist in registry
  try {
    const idsToCheck = ["QA-001", "AUD-003", "DEV-001", "PENTEST-007", "AIRT-016", "BREAK-021"];
    for (const promptId of idsToCheck) {
      const output = execSync(`python3 -c "from backend.prompt_registry import get_registry; reg = get_registry(); print(any(p['id'] == '${promptId}' for p in reg.prompts))"`, { cwd: baseDir }).toString().trim();
      assert(output === 'True', `Known prompt ID '${promptId}' is present in the registry`);
    }
  } catch (e: any) {
    assert(false, `Known prompt IDs verification failed: ${e.message}`);
  }

  console.log("==================================================");
  if (failed) {
    console.error("PROMPT REGISTRY CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PROMPT REGISTRY CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runPromptRegistryTests();
