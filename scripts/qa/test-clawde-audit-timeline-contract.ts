import * as fs from 'fs';
import * as path from 'path';

function runAuditTimelineContractTests() {
  console.log("==================================================");
  console.log("CLAWDE AUDIT TIMELINE CONTRACT VALIDATION");
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
  assert(pyContent.includes('CREATE TABLE IF NOT EXISTS orchestrator_run_history'), "FastAPI initializes history table");
  assert(pyContent.includes('/api/v1/orchestrator/history'), "FastAPI supports /api/v1/orchestrator/history GET route");
  assert(pyContent.includes('log_orchestrator_action('), "FastAPI defines helper function to log orchestrator events");
  assert(pyContent.includes('execute_start'), "FastAPI logs execute_start action in history database");
  assert(pyContent.includes('transition'), "FastAPI logs transition action on successful runs");

  // 3. Read frontend/index.html and verify UI elements
  const htmlContent = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(htmlContent.includes('CLAWDE Control Tower UI Build: OPS1') || htmlContent.includes('CLAWDE Control Tower UI Build: SEC1') || htmlContent.includes('CLAWDE Control Tower UI Build: UX2'), "index.html contains UI Build version indicator");
  assert(htmlContent.includes('id="clawde-audit-timeline-area"'), "index.html contains #clawde-audit-timeline-area element");
  assert(htmlContent.includes('id="clawde-audit-timeline-content"'), "index.html contains #clawde-audit-timeline-content container");
  assert(htmlContent.includes('src="app.js?v=OPS1"') || htmlContent.includes('src="app.js?v=SEC1"') || htmlContent.includes('src="app.js?v=UX2"'), "index.html has versioned script tag");

  // 4. Read frontend/app.js and verify timeline loader
  const jsContent = fs.readFileSync(appJsPath, 'utf-8');
  assert(jsContent.includes('loadClawdeHistory()') || jsContent.includes('loadClawdeHistory'), "app.js defines loadClawdeHistory logic");
  assert(jsContent.includes('/api/v1/orchestrator/history'), "app.js fetches history endpoint");
  assert(jsContent.includes('clawde-audit-timeline-content'), "app.js updates timeline content dynamically");

  // 5. Check no external publication or git push/merge mechanisms in history loggers
  const historyBlock = pyContent.substring(pyContent.indexOf('def log_orchestrator_action'));
  assert(!historyBlock.includes('git push'), "History helpers contain no git push mechanisms");
  assert(!historyBlock.includes('git merge'), "History helpers contain no git merge mechanisms");

  console.log("==================================================");
  if (failed) {
    console.error("AUDIT TIMELINE CONTRACT CHECK FAILED");
    process.exit(1);
  } else {
    console.log("AUDIT TIMELINE CONTRACT CHECK PASSED");
    process.exit(0);
  }
}

runAuditTimelineContractTests();
