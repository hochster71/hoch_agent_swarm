import * as fs from 'fs';
import * as path from 'path';

function runApprovedChangesTests() {
  console.log("==================================================");
  console.log("VISUAL APPROVED CHANGES CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const closureJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/approved_with_changes_closure.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/18_approved_with_changes_closure.md');

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
  assert(fs.existsSync(closureJsonFile), "approved_with_changes_closure.json exists");
  assert(fs.existsSync(docFile), "18_approved_with_changes_closure.md exists");

  if (!fs.existsSync(closureJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON Closure
  let closure: any;
  try {
    const rawJson = fs.readFileSync(closureJsonFile, 'utf-8');
    closure = JSON.parse(rawJson);
    assert(true, "approved_with_changes_closure.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse approved_with_changes_closure.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify prior decision and flags
  assert(closure.prior_decision === "APPROVE_WITH_CHANGES", "Prior decision check: APPROVE_WITH_CHANGES");
  assert(closure.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  
  // 4. Verify all V9 change IDs exist and status is CLOSED
  const changeIds = ["V9-001", "V9-002", "V9-003", "V9-004", "V9-005", "V9-006", "V9-007"];
  changeIds.forEach(id => {
    const change = closure.changes.find((c: any) => c.id === id);
    assert(!!change, `Change list contains ID ${id}`);
    if (change) {
      assert(change.status === "CLOSED", `Change status for ID ${id} is CLOSED`);
    }
  });

  // 5. Tablet review status
  assert(closure.tablet_readability.required === true, "Tablet review criteria is flagged as required");
  assert(closure.tablet_readability.status === "PENDING_MANUAL_REVIEW", "Tablet review status remains PENDING_MANUAL_REVIEW");

  // 6. Verify source and freshness visual copy
  const previewHtmlFile = path.join(baseDir, 'mockups/visual-control-plane/dashboard-preview.html');
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  
  const htmlContent = fs.readFileSync(previewHtmlFile, 'utf-8');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(htmlContent.includes("PREVIEW ONLY") || htmlContent.includes("LOCAL OPTIONAL"), "dashboard-preview.html contains PREVIEW ONLY or LOCAL OPTIONAL");
  assert(jsContent.includes("[SRC]") && jsContent.includes("[TIME]") && jsContent.includes("[EVID]"), "visual_dashboard_preview.js renders formatted source, freshness, and evidence tags");
  assert(jsContent.includes("isFailClosed") || jsContent.includes("FAIL-CLOSED"), "FAIL-CLOSED highlighting and states are rendered");

  // 7. Safety checks: No fetch mutations or stream interfaces
  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket usage in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource usage in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  // 8. Blocked actions registered in JSON
  const blocked = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blocked.forEach(action => {
    assert(closure.blocked_actions.includes(action), `Closure blocks action: '${action}'`);
  });

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL APPROVED CHANGES CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL APPROVED CHANGES CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runApprovedChangesTests();
