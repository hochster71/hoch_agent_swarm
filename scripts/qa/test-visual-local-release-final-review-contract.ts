import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runLocalReleaseFinalReviewTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL RELEASE FINAL REVIEW CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/34_local_release_final_review.md');
  const archiveRoot = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive');
  const tarFile = path.join(archiveRoot, 'visual-control-plane-local.tar.gz');
  const archiveManifestFile = path.join(archiveRoot, 'archive_manifest.json');
  const archiveReviewFile = path.join(archiveRoot, 'archive_review.json');
  const checksumFile = path.join(archiveRoot, 'archive_checksums.sha256');
  const finalReviewFile = path.join(archiveRoot, 'final_review.json');

  const sourceDir = path.join(baseDir, 'artifacts/releases/visual-control-plane-local');
  const sourceFreezeFile = path.join(sourceDir, 'freeze_record.json');
  const sourceLedgerFile = path.join(sourceDir, 'hash_ledger.json');
  const sourceManifestFile = path.join(sourceDir, 'manifest.json');
  const sourceProvenanceFile = path.join(sourceDir, 'provenance.json');
  const sourceRollbackFile = path.join(sourceDir, 'ROLLBACK.md');
  const sourceEvidenceDir = path.join(sourceDir, 'evidence');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  const getSha256 = (filePath: string): string => {
    const fileBuffer = fs.readFileSync(filePath);
    return crypto.createHash('sha256').update(fileBuffer).digest('hex');
  };

  // 1. Verify files exist
  assert(fs.existsSync(docFile), "docs/visual-control-plane/34_local_release_final_review.md exists");
  assert(fs.existsSync(finalReviewFile), "final_review.json exists");
  assert(fs.existsSync(tarFile), "archive file exists");
  assert(fs.existsSync(archiveManifestFile), "archive_manifest.json exists");
  assert(fs.existsSync(archiveReviewFile), "archive_review.json exists");
  assert(fs.existsSync(checksumFile), "archive_checksums.sha256 exists");
  assert(fs.existsSync(sourceFreezeFile), "source freeze_record.json exists");
  assert(fs.existsSync(sourceLedgerFile), "source hash_ledger.json exists");
  assert(fs.existsSync(sourceManifestFile), "source manifest.json exists");
  assert(fs.existsSync(sourceProvenanceFile), "source provenance.json exists");
  assert(fs.existsSync(sourceRollbackFile), "source ROLLBACK.md exists");
  assert(fs.existsSync(sourceEvidenceDir), "source evidence folder exists");

  if (fs.existsSync(sourceEvidenceDir)) {
    const evidenceFiles = fs.readdirSync(sourceEvidenceDir);
    assert(evidenceFiles.length > 0, "source evidence files exist inside folder");
  } else {
    assert(false, "source evidence folder does not exist");
  }

  if (!fs.existsSync(finalReviewFile) || !fs.existsSync(archiveManifestFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let finalReview: any;
  let archiveManifest: any;

  try {
    finalReview = JSON.parse(fs.readFileSync(finalReviewFile, 'utf-8'));
    assert(true, "final_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse final_review.json: ${e.message}`);
    process.exit(1);
  }

  try {
    archiveManifest = JSON.parse(fs.readFileSync(archiveManifestFile, 'utf-8'));
    assert(true, "archive_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse archive_manifest.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify final review metadata fields
  const actualSha = getSha256(tarFile);
  assert(finalReview.archive_sha256 === actualSha, `archive sha256 in final_review.json matches actual archive: ${actualSha}`);
  assert(archiveManifest.archive_sha256 === actualSha, "archive sha256 matches archive_manifest.json");

  const checksumContent = fs.readFileSync(checksumFile, 'utf-8');
  assert(checksumContent.includes(actualSha), "archive_checksums.sha256 contains actual archive sha256");

  assert(finalReview.phase === "V25_LOCAL_RELEASE_FINAL_REVIEW", "phase is V25_LOCAL_RELEASE_FINAL_REVIEW");
  assert(finalReview.local_only === true, "local_only is true");
  assert(finalReview.review_status === "FINAL_REVIEW_COMPLETE", "review_status is FINAL_REVIEW_COMPLETE");
  assert(finalReview.final_local_release_status === "READY_FOR_LOCAL_INSTALL_REVIEW", "final_local_release_status is READY_FOR_LOCAL_INSTALL_REVIEW");
  assert(finalReview.next_allowed_phase === "V26_LOCAL_INSTALL_REVIEW", "next_allowed_phase is V26_LOCAL_INSTALL_REVIEW");

  assert(finalReview.archive_verified === true, "archive_verified is true");
  assert(finalReview.source_freeze_verified === true, "source_freeze_verified is true");
  assert(finalReview.manifest_verified === true, "manifest_verified is true");
  assert(finalReview.provenance_verified === true, "provenance_verified is true");
  assert(finalReview.rollback_verified === true, "rollback_verified is true");
  assert(finalReview.evidence_verified === true, "evidence_verified is true");

  assert(Array.isArray(finalReview.checks_failed) && finalReview.checks_failed.length === 0, "checks_failed is empty");

  // 4. Verify safety gates
  assert(finalReview.deployment_performed === false, "deployment_performed is false");
  assert(finalReview.production_deployment_enabled === false, "production_deployment_enabled is false");
  assert(finalReview.external_publication_enabled === false, "external_publication_enabled is false");
  assert(finalReview.backend_mutation_enabled === false, "backend_mutation_enabled is false");
  assert(finalReview.prompt_execution_enabled === false, "prompt_execution_enabled is false");
  assert(finalReview.approval_decision_execution_enabled === false, "approval_decision_execution_enabled is false");
  assert(finalReview.security_posture_change_enabled === false, "security_posture_change_enabled is false");

  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(finalReview.blocked_actions.includes(action), `Blocked action present in review: '${action}'`);
  });

  // 5. Verify no execution or mutation APIs in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL RELEASE FINAL REVIEW CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL RELEASE FINAL REVIEW CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalReleaseFinalReviewTests();
