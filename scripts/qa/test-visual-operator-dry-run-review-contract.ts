import * as fs from 'fs';
import * as path from 'path';

function runOperatorReviewTests() {
  console.log("==================================================");
  console.log("VISUAL OPERATOR REVIEW CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const reviewJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/operator_dry_run_review.json');
  const reportJsonFile = path.join(baseDir, 'artifacts/qa/visual_review/local_replacement_dry_run_report.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/22_operator_dry_run_review.md');

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
  assert(fs.existsSync(reviewJsonFile), "operator_dry_run_review.json exists");
  assert(fs.existsSync(reportJsonFile), "local_replacement_dry_run_report.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/22_operator_dry_run_review.md exists");

  if (!fs.existsSync(reviewJsonFile) || !fs.existsSync(reportJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON configs
  let review: any;
  let report: any;
  try {
    review = JSON.parse(fs.readFileSync(reviewJsonFile, 'utf-8'));
    assert(true, "operator_dry_run_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse operator_dry_run_review.json: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportJsonFile, 'utf-8'));
    assert(true, "local_replacement_dry_run_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse local_replacement_dry_run_report.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in review
  assert(review.review_status === "PENDING_OPERATOR_REVIEW", "Review status is PENDING_OPERATOR_REVIEW");
  assert(review.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  assert(review.replacement_performed === false, "Safety check: replacement_performed is false");

  // 4. Verify candidate and rollback paths are referenced
  assert(review.candidate_path === "artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html", "Candidate path referenced correctly");
  assert(review.rollback_path === "artifacts/qa/visual_review/dry_run_candidate/ROLLBACK.md", "Rollback path referenced correctly");

  const absCandidatePath = path.join(baseDir, review.candidate_path);
  const absRollbackPath = path.join(baseDir, review.rollback_path);
  assert(fs.existsSync(absCandidatePath), "Staged candidate cockpit file exists");
  assert(fs.existsSync(absRollbackPath), "Staged rollback file exists");

  // 5. Verify operator decision options are present
  const options = [
    "APPROVE_DRY_RUN_FOR_LOCAL_REPLACEMENT",
    "APPROVE_WITH_MORE_CHANGES",
    "REJECT_REPLACEMENT"
  ];
  options.forEach(opt => {
    assert(review.operator_decision_options.includes(opt), `Decision option present: '${opt}'`);
  });

  // 6. Verify blocked actions are present
  const blockedActions = [
    "full active cockpit replacement",
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(review.blocked_actions.includes(action), `Review blocks action: '${action}'`);
  });

  // 7. Verify report confirms replacement_performed=false
  assert(report.replacement_performed === false, "Dry-run report confirms replacement_performed is false");

  // 8. Safety check: No mutations or websocket interfaces in scripts
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL OPERATOR REVIEW CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL OPERATOR REVIEW CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runOperatorReviewTests();
