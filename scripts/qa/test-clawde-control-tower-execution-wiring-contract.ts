import * as fs from 'fs';
import * as path from 'path';

function runWiringContractTests() {
  console.log("==================================================");
  console.log("CLAWDE CONTROL TOWER WIRING CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const mainPyPath = path.join(baseDir, 'backend/main.py');
  const indexHtmlPath = path.join(baseDir, 'frontend/index.html');
  const appJsPath = path.join(baseDir, 'frontend/app.js');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Files existence check
  assert(fs.existsSync(mainPyPath), "main.py exists");
  assert(fs.existsSync(indexHtmlPath), "index.html exists");
  assert(fs.existsSync(appJsPath), "app.js exists");

  // 2. Read backend/main.py and verify endpoints
  const pyContent = fs.readFileSync(mainPyPath, 'utf-8');
  assert(pyContent.includes('/api/v1/orchestrator/debug'), "FastAPI supports /api/v1/orchestrator/debug GET route");
  assert(pyContent.includes('decision_{phase}_execute.json'), "FastAPI writes deterministic approval file decision_{phase}_execute.json");
  assert(pyContent.includes('artifacts/orchestrator/approvals'), "FastAPI uses artifacts/orchestrator/approvals directory");
  assert(pyContent.includes('"--phase", phase'), "FastAPI calls builder_runner.py with --phase argument");

  // 3. Read frontend/index.html and verify UI elements
  const htmlContent = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(htmlContent.includes('CLAWDE Control Tower UI Build: FIX1'), "index.html contains UI Build: FIX1 version indicator");
  assert(htmlContent.includes('id="clawde-status-banner"'), "index.html contains #clawde-status-banner element");
  assert(htmlContent.includes('id="clawde-dbg-api-status"'), "index.html contains #clawde-dbg-api-status");
  assert(htmlContent.includes('id="clawde-dbg-cwd"'), "index.html contains #clawde-dbg-cwd");
  assert(htmlContent.includes('id="clawde-dbg-repo-root"'), "index.html contains #clawde-dbg-repo-root");
  assert(htmlContent.includes('id="clawde-dbg-active-phase"'), "index.html contains #clawde-dbg-active-phase");
  assert(htmlContent.includes('id="clawde-dbg-approval-path"'), "index.html contains #clawde-dbg-approval-path");
  assert(htmlContent.includes('id="clawde-dbg-approval-exists"'), "index.html contains #clawde-dbg-approval-exists");
  assert(htmlContent.includes('id="clawde-dbg-runner-exists"'), "index.html contains #clawde-dbg-runner-exists");
  assert(htmlContent.includes('id="clawde-dbg-prompt-exists"'), "index.html contains #clawde-dbg-prompt-exists");
  assert(htmlContent.includes('id="clawde-dbg-returncode"'), "index.html contains #clawde-dbg-returncode");
  assert(htmlContent.includes('src="app.js?v=FIX1"'), "index.html has app.js?v=FIX1 version script tag");

  // 4. Read frontend/app.js and verify event listener logs
  const jsContent = fs.readFileSync(appJsPath, 'utf-8');
  assert(jsContent.includes('[REQUEST CLICKED]'), "app.js logs [REQUEST CLICKED] on Request Execution click");
  assert(jsContent.includes('[APPROVE CLICKED]'), "app.js logs [APPROVE CLICKED] on Approve Execution click");
  assert(jsContent.includes('[EXECUTE CLICKED]'), "app.js logs [EXECUTE CLICKED] on Execute Next Phase click");
  assert(jsContent.includes('triggerRunner(\'execute phase\''), "app.js triggers execution endpoint");
  assert(jsContent.includes('/api/v1/orchestrator/request-execution'), "app.js invokes request-execution endpoint");
  assert(jsContent.includes('clawde-status-banner'), "app.js controls visible telemetry banner");

  // 5. Restrict production push, merge or deployment triggers in orchestrator endpoints
  const orchestratorBlock = pyContent.substring(pyContent.indexOf('/api/v1/orchestrator/'));
  assert(!orchestratorBlock.includes('git push'), "Orchestrator endpoints contain no git push mechanisms");
  assert(!orchestratorBlock.includes('git merge'), "Orchestrator endpoints contain no git merge mechanisms");

  console.log("==================================================");
  if (failed) {
    console.error("WIRING CONTRACT CHECK FAILED");
    process.exit(1);
  } else {
    console.log("WIRING CONTRACT CHECK PASSED");
    process.exit(0);
  }
}

runWiringContractTests();
