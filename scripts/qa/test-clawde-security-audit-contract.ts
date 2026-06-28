import * as fs from 'fs';
import * as path from 'path';

function runSecurityAuditContractTests() {
  console.log("==================================================");
  console.log("CLAWDE SECURITY AUDIT CONTRACT VALIDATION");
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

  // 2. Read backend/main.py and verify endpoints security controls
  const pyContent = fs.readFileSync(mainPyPath, 'utf-8');
  assert(pyContent.includes('valid_phases = ["PR16", "PR17", "PR18"]'), "FastAPI enforces whitelist on execute endpoint");
  assert(pyContent.includes('valid_phases = ["PR16", "PR17", "PR18", "COMPLETED"]'), "FastAPI enforces whitelist on request endpoint");
  assert(pyContent.includes('".." in phase or "/" in phase or "\\\\" in phase'), "FastAPI rejects path traversal sequences in phase");
  assert(pyContent.includes('re.match(r"^[a-zA-Z0-9_\\-\\s\\.]+$", operator)'), "FastAPI validates operator input parameter regex");
  assert(pyContent.includes('re.match(r"^[a-zA-Z0-9_\\-\\s\\.]+$", scope)'), "FastAPI validates scope input parameter regex");
  assert(pyContent.includes('/api/v1/orchestrator/history/verify'), "FastAPI supports /api/v1/orchestrator/history/verify GET route");
  assert(pyContent.includes('verify_ledger_chain()'), "FastAPI verify route validates ledger hash chain");
  assert(pyContent.includes('get_ledger_blocks()'), "FastAPI verify route fetches ledger blocks");
  assert(pyContent.includes('add_event_to_ledger(event)'), "log_orchestrator_action logs action cryptographically in ledger blocks");

  // 3. Read frontend/index.html and verify UI elements
  const htmlContent = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(htmlContent.includes('CLAWDE Control Tower UI Build: SEC1'), "index.html contains UI Build: SEC1 version indicator");
  assert(htmlContent.includes('id="clawde-audit-integrity"'), "index.html contains #clawde-audit-integrity badge element");
  assert(htmlContent.includes('src="app.js?v=SEC1"'), "index.html has app.js?v=SEC1 version script tag");

  // 4. Read frontend/app.js and verify timeline loader security check
  const jsContent = fs.readFileSync(appJsPath, 'utf-8');
  assert(jsContent.includes('/api/v1/orchestrator/history/verify'), "app.js fetches log verification endpoint");
  assert(jsContent.includes('clawde-audit-integrity'), "app.js updates integrity badge styling dynamically");

  // 5. Restrict production push, merge or deployment triggers in orchestrator endpoints
  const orchestratorBlock = pyContent.substring(pyContent.indexOf('/api/v1/orchestrator/'));
  assert(!orchestratorBlock.includes('git push'), "Orchestrator endpoints contain no git push mechanisms");
  assert(!orchestratorBlock.includes('git merge'), "Orchestrator endpoints contain no git merge mechanisms");

  console.log("==================================================");
  if (failed) {
    console.error("SECURITY AUDIT CONTRACT CHECK FAILED");
    process.exit(1);
  } else {
    console.log("SECURITY AUDIT CONTRACT CHECK PASSED");
    process.exit(0);
  }
}

runSecurityAuditContractTests();
