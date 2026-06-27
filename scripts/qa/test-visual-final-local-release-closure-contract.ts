import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runFinalLocalReleaseClosureTests() {
  console.log("==================================================");
  console.log("VISUAL FINAL LOCAL RELEASE CLOSURE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/37_final_local_release_closure.md');
  const closureFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/final_local_release_closure.json');

  const tarFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/visual-control-plane-local.tar.gz');
  const archiveManifestFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/archive_manifest.json');
  const archiveReviewFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/archive_review.json');
  const finalReviewFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/final_review.json');

  const installRoot = path.join(baseDir, 'artifacts/install-review/visual-control-plane-local');
  const installReviewFile = path.join(installRoot, 'install_review.json');
  const installAcceptanceFile = path.join(installRoot, 'install_acceptance.json');

  const releaseRoot = path.join(baseDir, 'artifacts/releases/visual-control-plane-local');
  const releaseManifestFile = path.join(releaseRoot, 'manifest.json');
  const releaseProvenanceFile = path.join(releaseRoot, 'provenance.json');
  const hashLedgerFile = path.join(releaseRoot, 'hash_ledger.json');
  const rollbackFile = path.join(releaseRoot, 'ROLLBACK.md');

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
  assert(fs.existsSync(docFile), "docs/visual-control-plane/37_final_local_release_closure.md exists");
  assert(fs.existsSync(closureFile), "final_local_release_closure.json exists");
  assert(fs.existsSync(tarFile), "archive tarball exists");
  assert(fs.existsSync(archiveManifestFile), "archive manifest exists");
  assert(fs.existsSync(archiveReviewFile), "archive review exists");
  assert(fs.existsSync(finalReviewFile), "final review exists");
  assert(fs.existsSync(installReviewFile), "install review exists");
  assert(fs.existsSync(installAcceptanceFile), "install acceptance exists");
  assert(fs.existsSync(releaseManifestFile), "release package manifest exists");
  assert(fs.existsSync(releaseProvenanceFile), "release package provenance exists");
  assert(fs.existsSync(hashLedgerFile), "hash ledger exists");
  assert(fs.existsSync(rollbackFile), "rollback file exists");

  if (!fs.existsSync(closureFile) || !fs.existsSync(archiveManifestFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let closure: any;
  let archiveManifest: any;

  try {
    closure = JSON.parse(fs.readFileSync(closureFile, 'utf-8'));
    assert(true, "final_local_release_closure.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse closure JSON: ${e.message}`);
    process.exit(1);
  }

  try {
    archiveManifest = JSON.parse(fs.readFileSync(archiveManifestFile, 'utf-8'));
    assert(true, "archive_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse archive manifest: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify closure details
  assert(closure.phase === "V28_FINAL_LOCAL_RELEASE_CLOSURE", "phase check passed");
  assert(closure.final_closure_status === "LOCAL_RELEASE_CLOSED", "final_closure_status is LOCAL_RELEASE_CLOSED");
  assert(closure.local_only === true, "local_only is true");
  assert(closure.accepted_local_install === true, "accepted_local_install is true");
  assert(closure.install_acceptance_decision === "ACCEPT_LOCAL_INSTALL", "install_acceptance_decision is ACCEPT_LOCAL_INSTALL");
  assert(closure.release_train_complete === true, "release_train_complete is true");
  assert(closure.next_allowed_phase === "NONE_LOCAL_RELEASE_COMPLETE", "next_allowed_phase is NONE_LOCAL_RELEASE_COMPLETE");

  assert(closure.archive_verified === true, "archive_verified is true");
  assert(closure.source_freeze_verified === true, "source_freeze_verified is true");
  assert(closure.manifest_verified === true, "manifest_verified is true");
  assert(closure.provenance_verified === true, "provenance_verified is true");
  assert(closure.rollback_verified === true, "rollback_verified is true");
  assert(closure.evidence_verified === true, "evidence_verified is true");
  assert(closure.qa_passed === true, "qa_passed is true");
  assert(closure.ci_validate_passed === true, "ci_validate_passed is true");

  assert(closure.deployment_performed === false, "deployment_performed is false");
  assert(closure.production_deployment_enabled === false, "production_deployment_enabled is false");
  assert(closure.external_publication_enabled === false, "external_publication_enabled is false");
  assert(closure.backend_mutation_enabled === false, "backend_mutation_enabled is false");
  assert(closure.prompt_execution_enabled === false, "prompt_execution_enabled is false");
  assert(closure.approval_decision_execution_enabled === false, "approval_decision_execution_enabled is false");
  assert(closure.security_posture_change_enabled === false, "security_posture_change_enabled is false");

  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(closure.blocked_actions.includes(action), `Blocked action registered in closure: '${action}'`);
  });

  assert(Array.isArray(closure.closure_artifacts) && closure.closure_artifacts.length > 0, "closure_artifacts list is not empty");
  closure.closure_artifacts.forEach((art: string) => {
    assert(fs.existsSync(path.join(baseDir, art)), `Closure artifact exists: ${art}`);
  });

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL FINAL LOCAL RELEASE CLOSURE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL FINAL LOCAL RELEASE CLOSURE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runFinalLocalReleaseClosureTests();
