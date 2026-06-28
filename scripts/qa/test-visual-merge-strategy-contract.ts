import * as fs from 'fs';
import * as path from 'path';

function runMergeStrategyTests() {
  console.log("==================================================");
  console.log("VISUAL MERGE STRATEGY CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/merge-strategy/visual-control-plane-local-v1.md');
  const configJsonFile = path.join(baseDir, 'config/visual_control_plane_merge_strategy.json');

  const mergeDir = path.join(baseDir, 'artifacts/merge/visual-control-plane-local-v1');
  const readinessFile = path.join(mergeDir, 'merge_readiness.json');
  const resultFile = path.join(mergeDir, 'merge_result.json');

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
  assert(fs.existsSync(docFile), "docs/merge-strategy/visual-control-plane-local-v1.md exists");
  assert(fs.existsSync(configJsonFile), "config/visual_control_plane_merge_strategy.json exists");
  assert(fs.existsSync(readinessFile), "merge_readiness.json exists");
  assert(fs.existsSync(resultFile), "merge_result.json exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(readinessFile) || !fs.existsSync(resultFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let readiness: any;
  let result: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_control_plane_merge_strategy.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    readiness = JSON.parse(fs.readFileSync(readinessFile, 'utf-8'));
    assert(true, "merge_readiness.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse merge_readiness.json: ${e.message}`);
    process.exit(1);
  }

  try {
    result = JSON.parse(fs.readFileSync(resultFile, 'utf-8'));
    assert(true, "merge_result.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse merge_result.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify config details
  assert(config.track === "P5_MERGE_STRATEGY", "Track is P5_MERGE_STRATEGY");
  assert(config.source_branch === "feature/visual-control-plane", "Source branch check");
  assert(config.target_branch === "integration/visual-control-plane-local-v1", "Target branch check");
  assert(config.release_tag === "visual-control-plane-local-v1.0.0", "Release tag check");
  assert(config.merge_to_main_allowed === false, "merge_to_main_allowed is false");
  assert(config.push_allowed === false, "push_allowed is false");

  assert(config.deployment_performed === false, "config deployment_performed is false");
  assert(config.external_publication_enabled === false, "config external_publication_enabled is false");
  assert(config.production_deployment_enabled === false, "config production_deployment_enabled is false");
  assert(config.backend_mutation_enabled === false, "config backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "config prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "config approval_decision_execution_enabled is false");
  assert(config.security_posture_change_enabled === false, "config security_posture_change_enabled is false");

  // 4. Verify readiness details
  assert(readiness.source_branch_exists === true, "readiness source_branch_exists check");
  assert(readiness.target_branch_name === "integration/visual-control-plane-local-v1", "readiness target_branch_name check");
  assert(readiness.release_tag_exists === true, "readiness release_tag_exists check");
  assert(readiness.merge_to_main_allowed === false, "readiness merge_to_main_allowed is false");
  assert(readiness.push_allowed === false, "readiness push_allowed is false");
  assert(readiness.deployment_performed === false, "readiness deployment_performed is false");

  // 5. Verify result details
  assert(result.source_branch === "feature/visual-control-plane", "result source_branch check");
  assert(result.target_branch === "integration/visual-control-plane-local-v1", "result target_branch check");
  assert(result.release_tag === "visual-control-plane-local-v1.0.0", "result release_tag check");
  assert(result.merge_to_main_performed === false, "result merge_to_main_performed is false");
  assert(result.push_performed === false, "result push_performed is false");
  assert(result.deployment_performed === false, "result deployment_performed is false");
  assert(result.conflicts_detected === false, "result conflicts_detected is false");
  assert(result.qa_passed === true, "result qa_passed is true");
  assert(result.ci_validate_passed === true, "result ci_validate_passed is true");

  // 6. Verify blocked actions
  const blockedActions = [
    "merge directly to main",
    "git push",
    "production deployment",
    "external publication",
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(result.blocked_actions.includes(action), `Blocked action registered in result: '${action}'`);
  });

  // 7. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL MERGE STRATEGY CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL MERGE STRATEGY CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runMergeStrategyTests();
