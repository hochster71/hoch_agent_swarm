import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runLocalReleaseReviewTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL RELEASE REVIEW CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/31_local_release_review.md');
  const releaseRoot = path.join(baseDir, 'artifacts/releases/visual-control-plane-local');
  const reviewJsonFile = path.join(releaseRoot, 'release_review.json');
  const manifestJsonFile = path.join(releaseRoot, 'manifest.json');
  const provenanceJsonFile = path.join(releaseRoot, 'provenance.json');
  const readmeFile = path.join(releaseRoot, 'README.md');
  const rollbackFile = path.join(releaseRoot, 'ROLLBACK.md');
  const cockpitFile = path.join(releaseRoot, 'control-plane.html');
  const stylesFile = path.join(releaseRoot, 'styles.css');

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
  assert(fs.existsSync(docFile), "docs/visual-control-plane/31_local_release_review.md exists");
  assert(fs.existsSync(reviewJsonFile), "release_review.json exists");
  assert(fs.existsSync(releaseRoot), "release root exists");
  assert(fs.existsSync(manifestJsonFile), "manifest.json exists");
  assert(fs.existsSync(provenanceJsonFile), "provenance.json exists");
  assert(fs.existsSync(readmeFile), "README.md exists");
  assert(fs.existsSync(rollbackFile), "ROLLBACK.md exists");
  assert(fs.existsSync(cockpitFile), "control-plane.html exists");
  assert(fs.existsSync(stylesFile), "styles.css exists");

  if (!fs.existsSync(reviewJsonFile) || !fs.existsSync(manifestJsonFile) || !fs.existsSync(provenanceJsonFile)) {
    console.error("Critical JSON files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let review: any;
  let manifest: any;
  let provenance: any;

  try {
    review = JSON.parse(fs.readFileSync(reviewJsonFile, 'utf-8'));
    assert(true, "release_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse release_review.json: ${e.message}`);
    process.exit(1);
  }

  try {
    manifest = JSON.parse(fs.readFileSync(manifestJsonFile, 'utf-8'));
    assert(true, "manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest.json: ${e.message}`);
    process.exit(1);
  }

  try {
    provenance = JSON.parse(fs.readFileSync(provenanceJsonFile, 'utf-8'));
    assert(true, "provenance.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse provenance.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in review record
  assert(review.phase === "V22_LOCAL_RELEASE_REVIEW", "Phase check: V22_LOCAL_RELEASE_REVIEW");
  assert(review.local_only === true, "Safety check: local_only is true");
  assert(review.review_status === "REVIEW_COMPLETE", "Review status check: REVIEW_COMPLETE");
  assert(review.deployment_performed === false, "Safety check: deployment_performed is false");
  assert(review.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(review.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(review.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(review.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(review.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(review.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");

  assert(review.manifest_verified === true, "Verification check: manifest_verified is true");
  assert(review.provenance_verified === true, "Verification check: provenance_verified is true");
  assert(review.rollback_verified === true, "Verification check: rollback_verified is true");
  assert(review.evidence_verified === true, "Verification check: evidence_verified is true");
  assert(review.hashes_verified === true, "Verification check: hashes_verified is true");
  assert(Array.isArray(review.checks_failed) && review.checks_failed.length === 0, "Safety check: checks_failed is empty");

  // 4. Verify blocked actions list in review
  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(review.blocked_actions.includes(action), `Decision record blocks action: '${action}'`);
  });

  assert(review.next_allowed_phase === "V23_LOCAL_RELEASE_FREEZE", "Next allowed phase is V23_LOCAL_RELEASE_FREEZE");

  // 5. Verify actual file hashes against manifest declarations
  manifest.files.forEach((fileEntry: any) => {
    const fileAbsPath = path.join(baseDir, fileEntry.path);
    assert(fs.existsSync(fileAbsPath), `Manifest file entry exists: ${fileEntry.path}`);
    if (fs.existsSync(fileAbsPath)) {
      const actualHash = getSha256(fileAbsPath);
      assert(actualHash === fileEntry.sha256, `Hash verified for ${fileEntry.path}`);
    }
  });

  manifest.evidence.forEach((evidenceEntry: any) => {
    const fileAbsPath = path.join(baseDir, evidenceEntry.path);
    assert(fs.existsSync(fileAbsPath), `Manifest evidence entry exists: ${evidenceEntry.path}`);
    if (fs.existsSync(fileAbsPath)) {
      const actualHash = getSha256(fileAbsPath);
      assert(actualHash === evidenceEntry.sha256, `Hash verified for evidence ${evidenceEntry.path}`);
    }
  });

  // 6. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL RELEASE REVIEW CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL RELEASE REVIEW CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalReleaseReviewTests();
