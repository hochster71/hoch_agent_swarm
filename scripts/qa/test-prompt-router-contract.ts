import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

function runPromptRouterTests() {
  console.log("==================================================");
  console.log("PROMPT ROUTER CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const routerFile = path.join(baseDir, 'backend/prompt_router.py');
  const mainFile = path.join(baseDir, 'backend/main.py');
  const reportFile = path.join(baseDir, 'artifacts/qa/prompt_router/prompt_router_report.json');

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
  assert(fs.existsSync(routerFile), "Router file exists: backend/prompt_router.py");
  assert(fs.existsSync(mainFile), "FastAPI main app file exists: backend/main.py");

  // 2. Verify API routes are registered in main.py
  if (fs.existsSync(mainFile)) {
    const mainContent = fs.readFileSync(mainFile, 'utf-8');
    assert(mainContent.includes('/api/v1/prompts/router/rules'), "Route /api/v1/prompts/router/rules exists in main.py");
    assert(mainContent.includes('/api/v1/prompts/router/plan'), "Route /api/v1/prompts/router/plan exists in main.py");
    
    // Ensure no execution endpoints exist
    const hasExecutionEndpoint = mainContent.includes('/api/v1/prompts/execute') ||
                                 mainContent.includes('/api/v1/prompts/run') ||
                                 mainContent.includes('/api/v1/prompts/kickoff') ||
                                 mainContent.includes('/api/v1/prompts/evaluate/execute');
    assert(!hasExecutionEndpoint, "Safety check: No prompt execution endpoints exist");
  }

  // 3. Compile backend files to verify syntax
  try {
    execSync('python3 -m py_compile backend/main.py backend/prompt_router.py', { cwd: baseDir });
    assert(true, "Python syntax and import validation successful");
  } catch (e: any) {
    assert(false, `Python compile/import failed: ${e.message}`);
  }

  // Helper function to run a route planning test via python stdin
  const getPlan = (taskDesc: string, riskLevel: string = "LOW"): any => {
    try {
      const code = `import json
from backend.prompt_router import get_router
router = get_router()
plan = router.plan_route(${JSON.stringify(taskDesc)}, ${JSON.stringify(riskLevel)})
print(json.dumps(plan))`;
      const output = execSync('python3', { input: code, cwd: baseDir }).toString().trim();
      return JSON.parse(output);
    } catch (e: any) {
      console.error(`Subprocess execution failed for task [${taskDesc}]: ${e.message}`);
      failed = true;
      return {};
    }
  };

  // Helper function to get router rules
  const getRules = (): any => {
    try {
      const code = `import json
from backend.prompt_router import get_router
router = get_router()
print(json.dumps(router.get_rules()))`;
      const output = execSync('python3', { input: code, cwd: baseDir }).toString().trim();
      return JSON.parse(output);
    } catch (e: any) {
      console.error(`Subprocess rules check failed: ${e.message}`);
      failed = true;
      return {};
    }
  };

  // 4. Verify rules endpoint behaves correctly
  const rules = getRules();
  assert(rules.routing_policies && Object.keys(rules.routing_policies).length > 0, "Rules endpoint returns routing policies");

  // 5. Test Router Plan scenarios
  
  // A. Coding task selects CODE-001, CODE-002, SAST-001, QA-001
  const codingPlan = getPlan("Build a visual landing page mockup in react");
  assert(codingPlan.execution_allowed === false, "Coding plan returns execution_allowed=false");
  assert(codingPlan.selected_prompt_ids && codingPlan.selected_prompt_ids.includes("CODE-001"), "Coding task selects CODE-001");
  assert(codingPlan.selected_prompt_ids && codingPlan.selected_prompt_ids.includes("CODE-002"), "Coding task selects CODE-002");
  assert(codingPlan.selected_prompt_ids && codingPlan.selected_prompt_ids.includes("SAST-001"), "Coding task selects SAST-001");
  assert(codingPlan.selected_prompt_ids && codingPlan.selected_prompt_ids.includes("QA-001"), "Coding task selects QA-001");

  // B. Cybersecurity task selects THREAT-002 and AUD-003 or AUD-002
  const cyberPlan = getPlan("Perform threat modeling and cybersecurity scan on router configuration");
  assert(cyberPlan.selected_prompt_ids && cyberPlan.selected_prompt_ids.includes("THREAT-002"), "Cybersecurity task selects THREAT-002");
  assert(cyberPlan.selected_prompt_ids && (cyberPlan.selected_prompt_ids.includes("AUD-002") || cyberPlan.selected_prompt_ids.includes("AUD-003")), "Cybersecurity task selects AUD-002 or AUD-003");

  // C. Pen test task selects PENTEST-007
  const pentestPlan = getPlan("Review pen test report findings for API leaks");
  assert(pentestPlan.selected_prompt_ids && pentestPlan.selected_prompt_ids.includes("PENTEST-007"), "Pen test task selects PENTEST-007");

  // D. App-store task requires human approval
  const appStorePlan = getPlan("Submit the finished iOS application to the Apple App Store");
  assert(appStorePlan.human_approval_required === true, "App-store task requires human approval");

  // E. Delete/deploy/security posture task requires human approval
  const deletePlan = getPlan("Delete older model templates from locally active LM Studio node");
  assert(deletePlan.human_approval_required === true, "Delete/decommission task requires human approval");

  const deployPlan = getPlan("Deploy visual-control-plane app to production cluster");
  assert(deployPlan.human_approval_required === true, "Deploy task requires human approval");

  // F. Bypass approval task returns FAIL_CLOSED
  const bypassPlan = getPlan("Force deploy visual assets and bypass approval gate");
  assert(bypassPlan.risk_level === 'FAIL_CLOSED', `Bypass task returns risk_level='FAIL_CLOSED' (got '${bypassPlan.risk_level}')`);
  assert(bypassPlan.fail_closed_triggers && bypassPlan.fail_closed_triggers.includes("BYPASS_APPROVAL_ATTEMPTED"), "Bypass task triggers FAIL_CLOSED for bypass attempt");

  // G. Missing prompt IDs fail closed
  try {
    const code = `from backend.prompt_router import PromptRouter; r = PromptRouter(); r.registry.prompts = []; print(r.plan_route('test')['risk_level'])`;
    const output = execSync('python3', { input: code, cwd: baseDir }).toString().trim();
    assert(output === 'FAIL_CLOSED', "Missing prompt library / empty registry fails closed");
  } catch (e: any) {
    assert(false, `Registry error fail-closed check failed: ${e.message}`);
  }

  // 6. Verify QA artifact prompt_router_report.json is written
  assert(fs.existsSync(reportFile), "QA artifact report exists: artifacts/qa/prompt_router/prompt_router_report.json");

  console.log("==================================================");
  if (failed) {
    console.error("PROMPT ROUTER CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PROMPT ROUTER CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runPromptRouterTests();
