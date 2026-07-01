import * as fs from 'fs';
import * as path from 'path';

function runOrchestratorContractTests() {
  console.log("==================================================");
  console.log("PHASE ORCHESTRATOR CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  
  const controlDir = path.join(baseDir, 'control');
  const templatesDir = path.join(baseDir, 'templates/phases');
  const scriptsDir = path.join(baseDir, 'scripts/orchestrator');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify all control files exist
  const controlFiles = ['phase_registry.json', 'authority_policy.json', 'blocked_actions.json', 'phase_state.json'];
  controlFiles.forEach(f => {
    assert(fs.existsSync(path.join(controlDir, f)), `Control file ${f} exists`);
  });

  // 2. Verify all scripts exist
  const orchestratorScripts = [
    'next_phase_runner.py',
    'render_phase_prompt.py',
    'verify_no_drift.py',
    'gatekeeper.py',
    'write_phase_report.py'
  ];
  orchestratorScripts.forEach(f => {
    assert(fs.existsSync(path.join(scriptsDir, f)), `Orchestrator script ${f} exists`);
  });

  // 3. Verify templates exist
  const expectedTemplates = [
    'PR14-controlled-staging-deployment-package.md',
    'PR15-controlled-staging-validation.md',
    'PR16-production-cutover-plan.md',
    'PR17-production-cutover-execution.md',
    'PR18-post-cutover-validation.md'
  ];
  expectedTemplates.forEach(f => {
    assert(fs.existsSync(path.join(templatesDir, f)), `Phase template ${f} exists`);
  });

  // 4. Verify authority policy contains every blocked action
  const blockedFile = path.join(controlDir, 'blocked_actions.json');
  const policyFile = path.join(controlDir, 'authority_policy.json');
  
  if (fs.existsSync(blockedFile) && fs.existsSync(policyFile)) {
    const blockedData = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    const policyData = JSON.parse(fs.readFileSync(policyFile, 'utf-8'));
    
    const blockedActions: string[] = blockedData.blocked_actions.map((x: any) => x.action);
    const humanRequired: string[] = policyData.human_approval_required;
    
    blockedActions.forEach(act => {
      assert(humanRequired.includes(act), `Authority policy lists blocked action: ${act}`);
    });
  }

  // 5. Verify no script contains bypass logic or enables forbidden actions
  const allScripts = fs.readdirSync(scriptsDir)
    .map(file => path.join(scriptsDir, file))
    .filter(file => fs.statSync(file).isFile());
  allScripts.forEach(scriptPath => {
    const content = fs.readFileSync(scriptPath, 'utf-8');
    assert(!content.includes('push_allowed = true') &&
           !content.includes('main_merge_allowed = true') &&
           !content.includes('production_deployment_allowed = true') &&
           !content.includes('production_secrets_allowed = true'),
           `Script ${path.basename(scriptPath)} does not bypass authority policies`);
  });

  // 6. Verify generated prompt file exists and includes blocked-action text
  const pr14GeneratedPath = path.join(baseDir, 'artifacts/orchestrator/generated-prompts/PR14.md');
  if (!fs.existsSync(pr14GeneratedPath)) {
    console.log("Generating PR14 prompt using render_phase_prompt.py...");
    try {
      const { execSync } = require("child_process");
      execSync("python3 scripts/orchestrator/render_phase_prompt.py PR14", { stdio: "inherit" });
    } catch (e: any) {
      console.error("Failed to generate PR14 prompt:", e.message);
    }
  }

  assert(fs.existsSync(pr14GeneratedPath), "PR14 rendered prompt generated successfully");
  if (fs.existsSync(pr14GeneratedPath)) {
    const pr14Content = fs.readFileSync(pr14GeneratedPath, 'utf-8');
    assert(pr14Content.includes('Blocked Actions (MUST STOP)'), "Generated prompt contains blocked action section header");
    assert(pr14Content.includes('No production deployment'), "Generated prompt contains blocked deployment line");
    assert(pr14Content.includes('No git push'), "Generated prompt contains blocked push line");
  }

  console.log("==================================================");
  if (failed) {
    console.error("PHASE ORCHESTRATOR CONTRACT TEST FAILED");
    process.exit(1);
  } else {
    console.log("PHASE ORCHESTRATOR CONTRACT TEST PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runOrchestratorContractTests();
