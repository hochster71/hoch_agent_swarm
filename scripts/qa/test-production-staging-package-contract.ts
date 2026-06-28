import * as fs from 'fs';
import * as path from 'path';

function runStagingPackageTests() {
  console.log("==================================================");
  console.log("PRODUCTION STAGING PACKAGE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr14Dir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');

  const manifestFile = path.join(pr14Dir, 'production_staging_manifest.json');
  const packageFile = path.join(pr14Dir, 'production_staging_deployment_package.json');
  const boundaryFile = path.join(pr14Dir, 'staging_boundary_attestation.json');
  const blockedFile = path.join(pr14Dir, 'staging_blocked_actions.json');
  const sealFile = path.join(pr14Dir, 'pr14_final_seal.json');

  const pr13Manifest = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1/production_decision_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR14 files exist
  assert(fs.existsSync(manifestFile), "production_staging_manifest.json exists");
  assert(fs.existsSync(packageFile), "production_staging_deployment_package.json exists");
  assert(fs.existsSync(boundaryFile), "staging_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "staging_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr14_final_seal.json exists");

  assert(fs.existsSync(pr13Manifest), "PR13 manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(packageFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let pkg: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_staging_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    pkg = JSON.parse(fs.readFileSync(packageFile, 'utf-8'));
    assert(true, "production_staging_deployment_package.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse staging package: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "staging_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "staging_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr14_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR14_PRODUCTION_READINESS_CONTROLLED_STAGING_DEPLOYMENT_PACKAGE", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR14 PRODUCTION READINESS CONTROLLED STAGING DEPLOYMENT PACKAGE — ACCEPTED FOR STAGING DEPLOYMENT PACKAGE ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify package info
  const stgPkg = pkg.staging_deployment_package;
  assert(!!stgPkg, "staging_deployment_package object exists");
  if (stgPkg) {
    assert(stgPkg.release_tag === "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY-staging", "Release tag is correct");
    assert(stgPkg.package_metadata.operator === "Michael Hoch", "Operator is Michael Hoch");
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

  const blockedList = blocked.staging_blocked_actions;
  assert(Array.isArray(blockedList), "staging_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 6. Verify no file claims execution performed
  const allJsonContents = [manifest, pkg, boundary, blocked, seal];
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
    console.error("PRODUCTION STAGING PACKAGE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION STAGING PACKAGE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runStagingPackageTests();
