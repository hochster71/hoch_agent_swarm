import * as fs from 'fs';
import * as path from 'path';

function runUiContractTests() {
  console.log("==================================================");
  console.log("CLAWDE CONTROL TOWER UI CONTRACT CHECK");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const indexHtmlPath = path.join(baseDir, 'frontend/index.html');
  const appJsPath = path.join(baseDir, 'frontend/app.js');
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

  // 1. Verify files exist
  assert(fs.existsSync(indexHtmlPath), "frontend/index.html exists");
  assert(fs.existsSync(appJsPath), "frontend/app.js exists");
  assert(fs.existsSync(mainPyPath), "backend/main.py exists");

  if (!fs.existsSync(indexHtmlPath) || !fs.existsSync(appJsPath) || !fs.existsSync(mainPyPath)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  const htmlContent = fs.readFileSync(indexHtmlPath, 'utf-8');
  const jsContent = fs.readFileSync(appJsPath, 'utf-8');
  const pyContent = fs.readFileSync(mainPyPath, 'utf-8');

  // 2. UI route/tab exists
  assert(htmlContent.includes('id="view-clawde"') || htmlContent.includes("id='view-clawde'"), "UI view-clawde container exists");
  assert(htmlContent.includes('id="nav-clawde"') || htmlContent.includes("id='nav-clawde'"), "Sidebar nav-clawde item exists");
  assert(jsContent.includes("'clawde'") || jsContent.includes('"clawde"'), "app.js registers clawde view");

  // 3. CLAWDE name appears
  assert(htmlContent.includes('CLAWDE HOCH') && htmlContent.includes('Chief Code Predator'), "CLAWDE HOCH identity and role are rendered");

  // 4. phase registry data appears
  assert(htmlContent.includes('id="clawde-current-phase"'), "clawde-current-phase span exists");
  assert(htmlContent.includes('id="clawde-last-completed"'), "clawde-last-completed span exists");

  // 5. no-drift status appears
  assert(htmlContent.includes('id="clawde-drift-status"'), "clawde-drift-status element exists");

  // 6. blocked actions appear
  assert(htmlContent.includes('id="clawde-blocked-actions-container"'), "clawde-blocked-actions-container exists");

  // 7. generated prompt link/path appears
  assert(htmlContent.includes('id="clawde-generated-prompt-path"'), "clawde-generated-prompt-path code block exists");
  assert(htmlContent.includes('id="clawde-latest-report-path"'), "clawde-latest-report-path code block exists");
  assert(htmlContent.includes('id="clawde-evidence-seal-path"'), "clawde-evidence-seal-path code block exists");

  // 8. No production action buttons or deploy/push/merge actions exist
  const forbiddenKeywords = [
    "production_deployment",
    "git_push",
    "main_merge",
    "deploy_to_production",
    "trigger_production_deploy",
    "run_production_deploy"
  ];

  forbiddenKeywords.forEach(kw => {
    assert(!htmlContent.includes(kw), `No references to '${kw}' in index.html`);
  });

  // Verify that app.js only initiates safe local fetch operations
  assert(!jsContent.includes('push_allowed: true') && 
         !jsContent.includes('main_merge_allowed: true') && 
         !jsContent.includes('production_deployment_allowed: true'),
         "app.js does not bypass registry permissions or trigger authority gates");

  // Verify backend endpoints are registered
  assert(pyContent.includes('/api/v1/orchestrator/status'), "FastAPI serves orchestrator status endpoint");
  assert(pyContent.includes('/api/v1/orchestrator/run-runner'), "FastAPI serves orchestrator runner endpoint");

  console.log("==================================================");
  if (failed) {
    console.error("CLAWDE CONTROL TOWER UI CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("CLAWDE CONTROL TOWER UI CONTRACT PASSED");
    process.exit(0);
  }
}

runUiContractTests();
