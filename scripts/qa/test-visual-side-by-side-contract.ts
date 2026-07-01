import * as fs from 'fs';
import * as path from 'path';

function runSideBySideTests() {
  console.log("==================================================");
  console.log("VISUAL SIDE-BY-SIDE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const reviewHtmlFile = path.join(baseDir, 'mockups/visual-control-plane/side-by-side-review.html');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/16_side_by_side_verification.md');
  const checklistJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/side_by_side_review_checklist.json');

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
  assert(fs.existsSync(reviewHtmlFile), "side-by-side-review.html exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/16_side_by_side_verification.md exists");
  assert(fs.existsSync(checklistJsonFile), "side_by_side_review_checklist.json exists");

  if (!fs.existsSync(reviewHtmlFile) || !fs.existsSync(docFile) || !fs.existsSync(checklistJsonFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON Checklist
  let checklist: any;
  try {
    const rawJson = fs.readFileSync(checklistJsonFile, 'utf-8');
    checklist = JSON.parse(rawJson);
    assert(true, "side_by_side_review_checklist.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse side_by_side_review_checklist.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify checklist parameters
  assert(checklist.active_cockpit_replacement_enabled === false, "Checklist safety flag: active_cockpit_replacement_enabled is false");
  assert(checklist.local_only === true, "Checklist safety flag: local_only is true");
  assert(checklist.michael_hoch_approval_required === true, "Checklist safety flag: michael_hoch_approval_required is true");
  assert(checklist.review_status === "PENDING_OPERATOR_REVIEW", "Checklist review status: PENDING_OPERATOR_REVIEW");

  const blocked = [
    "active cockpit replacement",
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blocked.forEach(action => {
    assert(checklist.blocked_actions.includes(action), `Checklist blocks action: '${action}'`);
  });

  // 4. Verify HTML contents
  const htmlContent = fs.readFileSync(reviewHtmlFile, 'utf-8');
  assert(htmlContent.includes("REVIEW ONLY — NO LIVE REPLACEMENT"), "HTML page contains warning banner 'REVIEW ONLY — NO LIVE REPLACEMENT'");
  assert(htmlContent.includes("Current Cockpit / Baseline"), "HTML page contains baseline panel header 'Current Cockpit / Baseline'");
  assert(htmlContent.includes("Visual Control Plane Preview"), "HTML page contains preview panel header 'Visual Control Plane Preview'");

  const decisions = ["APPROVE VISUAL DIRECTION", "APPROVE WITH CHANGES", "REJECT"];
  decisions.forEach(opt => {
    assert(htmlContent.includes(opt), `HTML page contains decision control: '${opt}'`);
  });

  assert(htmlContent.includes("control-plane.html"), "HTML page links/frames control-plane.html");
  assert(htmlContent.includes("dashboard-preview.html"), "HTML page links/frames dashboard-preview.html");

  // 5. Safety checks: No fetch, WebSocket, EventSource, decision, or execution endpoints
  assert(!htmlContent.includes("WebSocket"), "Safety check: No WebSocket usage in HTML script blocks");
  assert(!htmlContent.includes("EventSource"), "Safety check: No EventSource usage in HTML script blocks");
  assert(!htmlContent.includes("POST") && !htmlContent.includes("PUT") && !htmlContent.includes("DELETE"), "Safety check: No POST/PUT/DELETE fetch calls in HTML script blocks");
  assert(!htmlContent.includes("/decision"), "Safety check: No decision API endpoints referenced in HTML script blocks");
  assert(!htmlContent.includes("/execute") && !htmlContent.includes("/kickoff"), "Safety check: No execution API endpoints referenced in HTML script blocks");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL SIDE-BY-SIDE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL SIDE-BY-SIDE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runSideBySideTests();
