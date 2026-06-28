import * as fs from 'fs';
import * as path from 'path';

function runUXUpgradeContractTests() {
  console.log("==================================================");
  console.log("CLAWDE COCKPIT UX UPGRADE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
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
  assert(fs.existsSync(indexHtmlPath), "index.html exists");
  assert(fs.existsSync(appJsPath), "app.js exists");

  // 2. Read frontend/index.html and verify UI elements & CSS
  const htmlContent = fs.readFileSync(indexHtmlPath, 'utf-8');
  assert(htmlContent.includes('@keyframes led-pulse'), "index.html contains @keyframes led-pulse definition");
  assert(htmlContent.includes('.phase-card'), "index.html contains .phase-card class definition");
  assert(htmlContent.includes('.active-phase'), "index.html contains .active-phase class definition");
  assert(htmlContent.includes('.selected-phase'), "index.html contains .selected-phase class definition");
  assert(htmlContent.includes('.completed-phase'), "index.html contains .completed-phase class definition");
  assert(htmlContent.includes('id="clawde-phase-cards-container"'), "index.html contains #clawde-phase-cards-container row element");
  assert(htmlContent.includes('id="clawde-selected-status-light"'), "index.html contains #clawde-selected-status-light inspector element");
  assert(htmlContent.includes('id="clawde-gate-lockout-notice"'), "index.html contains #clawde-gate-lockout-notice element");
  assert(htmlContent.includes('CLAWDE Control Tower UI Build: UX2'), "index.html contains build marker: UX2");
  assert(htmlContent.includes('src="app.js?v=UX2"'), "index.html has app.js?v=UX2 version script tag");

  // 3. Read frontend/app.js and verify UI Controller Logic
  const jsContent = fs.readFileSync(appJsPath, 'utf-8');
  assert(jsContent.includes('selectedPhase'), "app.js tracks selectedPhase state variable");
  assert(jsContent.includes('phaseFilesMap'), "app.js references phaseFilesMap paths config dictionary");
  assert(jsContent.includes('clawde-phase-cards-container'), "app.js references phase cards container");
  assert(jsContent.includes('clawde-selected-status-light'), "app.js references details inspector selected status light");
  assert(jsContent.includes('clawde-gate-lockout-notice'), "app.js references lockout notice container");
  assert(jsContent.includes('phase-card'), "app.js maps and renders phase-card elements dynamically");
  assert(jsContent.includes('click'), "app.js binds click listeners to phase cards");

  console.log("==================================================");
  if (failed) {
    console.error("UX UPGRADE CONTRACT CHECK FAILED");
    process.exit(1);
  } else {
    console.log("UX UPGRADE CONTRACT CHECK PASSED");
    process.exit(0);
  }
}

runUXUpgradeContractTests();
