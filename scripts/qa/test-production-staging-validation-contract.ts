import * as fs from 'fs';
import * as path from 'path';

function runStagingValidationTests() {
  console.log("==================================================");
  console.log("PRODUCTION STAGING VALIDATION CONTRACT CHECK");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr15Dir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');

  const manifestFile = path.join(pr15Dir, 'production_staging_validation_manifest.json');
  const resultsFile = path.join(pr15Dir, 'production_staging_validation_results.json');
  const boundaryFile = path.join(pr15Dir, 'staging_validation_boundary_attestation.json');
  const blockedFile = path.join(pr15Dir, 'staging_validation_blocked_actions.json');
  const sealFile = path.join(pr15Dir, 'pr15_final_seal.json');

  const pr14Manifest = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1/production_staging_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR15 files exist
  assert(fs.existsSync(manifestFile), "production_staging_validation_manifest.json exists");
  assert(fs.existsSync(resultsFile), "production_staging_validation_results.json exists");
  assert(fs.existsSync(boundaryFile), "staging_validation_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "staging_validation_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr15_final_seal.json exists");

  assert(fs.existsSync(pr14Manifest), "PR14 manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(resultsFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let results: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_staging_validation_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    results = JSON.parse(fs.readFileSync(resultsFile, 'utf-8'));
    assert(true, "production_staging_validation_results.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse results: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "staging_validation_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "staging_validation_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr15_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR15_PRODUCTION_READINESS_CONTROLLED_STAGING_VALIDATION", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR15 PRODUCTION READINESS CONTROLLED STAGING VALIDATION — ACCEPTED FOR CONTROLLED STAGING VALIDATION ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify results
  const resObj = results.production_staging_validation_results;
  assert(!!resObj, "production_staging_validation_results object exists");
  if (resObj) {
    assert(resObj.staging_release_tag === "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY-staging", "Staging tag matches");
    assert(resObj.overall_status === "PASS", "Overall validation is PASS");
  }

  // 5. Verify blocked actions
  const requiredActions = [
    "production deployment",
    "git push",
    "main merge",
    "production secrets",
    "live external binding",
    "prompt execution",
    "approval execution",
    "external publication",
    "actual ATO claim"
  ];

  const blockedList = blocked.staging_validation_blocked_actions;
  assert(Array.isArray(blockedList), "staging_validation_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 6. Verify no file claims execution performed
  const allJsonContents = [manifest, results, boundary, blocked, seal];
  allJsonContents.forEach(jsonObj => {
    const str = JSON.stringify(jsonObj);
    assert(!str.includes('"production_deployment": true') && 
           !str.includes('"performed": true') && 
           !str.includes('"git_push": true') && 
           !str.includes('"main_merge": true'), 
           "No file claims execution was performed");
  });

  // 7. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("PRODUCTION STAGING VALIDATION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION STAGING VALIDATION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runStagingValidationTests();
