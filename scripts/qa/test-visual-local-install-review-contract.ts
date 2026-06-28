import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runLocalInstallReviewTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL INSTALL REVIEW CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/35_local_install_review.md');
  const configJsonFile = path.join(baseDir, 'config/visual_local_install_review.json');
  const scriptFile = path.join(baseDir, 'scripts/visual/install-review-local-release.sh');
  const installRoot = path.join(baseDir, 'artifacts/install-review/visual-control-plane-local');
  const installReviewFile = path.join(installRoot, 'install_review.json');

  const tarFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/visual-control-plane-local.tar.gz');
  const archiveManifestFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/archive_manifest.json');
  const archiveReviewFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/archive_review.json');
  const checksumFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive/archive_checksums.sha256');

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
  assert(fs.existsSync(docFile), "docs/visual-control-plane/35_local_install_review.md exists");
  assert(fs.existsSync(configJsonFile), "config/visual_local_install_review.json exists");
  assert(fs.existsSync(scriptFile), "install review script exists");
  assert(fs.existsSync(installRoot), "install review root exists");
  assert(fs.existsSync(installReviewFile), "install_review.json exists");
  assert(fs.existsSync(tarFile), "archive exists");
  assert(fs.existsSync(archiveManifestFile), "archive manifest exists");
  assert(fs.existsSync(archiveReviewFile), "archive review exists");
  assert(fs.existsSync(checksumFile), "archive checksums file exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(installReviewFile) || !fs.existsSync(archiveManifestFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let installReview: any;
  let archiveManifest: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_local_install_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    installReview = JSON.parse(fs.readFileSync(installReviewFile, 'utf-8'));
    assert(true, "install_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse install_review.json: ${e.message}`);
    process.exit(1);
  }

  try {
    archiveManifest = JSON.parse(fs.readFileSync(archiveManifestFile, 'utf-8'));
    assert(true, "archive_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse archive manifest: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify archive sha256
  const actualSha = getSha256(tarFile);
  assert(config.archive_sha256 === actualSha, `archive sha256 matches config: ${actualSha}`);
  assert(archiveManifest.archive_sha256 === actualSha, "archive sha256 matches archive_manifest.json");

  // 4. Verify flags
  assert(config.install_review_performed === true, "install_review_performed is true");
  assert(installReview.install_review_performed === true, "installReview install_review_performed is true");
  assert(installReview.archive_verified === true, "archive_verified is true");
  assert(installReview.extract_verified === true, "extract_verified is true");
  assert(installReview.manifest_verified === true, "manifest_verified is true");
  assert(installReview.provenance_verified === true, "provenance_verified is true");
  assert(installReview.rollback_verified === true, "rollback_verified is true");
  assert(installReview.evidence_verified === true, "evidence_verified is true");

  assert(config.deployment_performed === false, "config deployment_performed is false");
  assert(config.production_deployment_enabled === false, "config production_deployment_enabled is false");
  assert(config.external_publication_enabled === false, "config external_publication_enabled is false");
  assert(config.backend_mutation_enabled === false, "config backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "config prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "config approval_decision_execution_enabled is false");
  assert(config.security_posture_change_enabled === false, "config security_posture_change_enabled is false");

  assert(installReview.deployment_performed === false, "installReview deployment_performed is false");
  assert(installReview.production_deployment_enabled === false, "installReview production_deployment_enabled is false");
  assert(installReview.external_publication_enabled === false, "installReview external_publication_enabled is false");
  assert(installReview.backend_mutation_enabled === false, "installReview backend_mutation_enabled is false");
  assert(installReview.prompt_execution_enabled === false, "installReview prompt_execution_enabled is false");
  assert(installReview.approval_decision_execution_enabled === false, "installReview approval_decision_execution_enabled is false");
  assert(installReview.security_posture_change_enabled === false, "installReview security_posture_change_enabled is false");

  assert(Array.isArray(installReview.checks_failed) && installReview.checks_failed.length === 0, "checks_failed is empty");
  assert(config.next_allowed_phase === "V27_LOCAL_INSTALL_ACCEPTANCE", "next_allowed_phase is V27_LOCAL_INSTALL_ACCEPTANCE");

  // 5. Verify extracted package contents
  assert(fs.existsSync(path.join(installRoot, 'control-plane.html')), "extracted package contains control-plane.html");
  assert(fs.existsSync(path.join(installRoot, 'styles.css')), "extracted package contains styles.css");
  assert(fs.existsSync(path.join(installRoot, 'manifest.json')), "extracted package contains manifest.json");
  assert(fs.existsSync(path.join(installRoot, 'provenance.json')), "extracted package contains provenance.json");
  assert(fs.existsSync(path.join(installRoot, 'ROLLBACK.md')), "extracted package contains ROLLBACK.md");
  assert(fs.existsSync(path.join(installRoot, 'evidence')), "extracted package contains evidence folder");

  // 6. Verify script structure
  const scriptContent = fs.readFileSync(scriptFile, 'utf-8');
  assert(scriptContent.includes("set -euo pipefail"), "script uses set -euo pipefail");
  assert(!scriptContent.includes("rm -rf"), "script does not contain rm -rf");
  assert(!scriptContent.includes("backend/"), "script does not reference backend/");

  // Verify no execution or mutation APIs
  assert(!scriptContent.includes("WebSocket"), "script does not introduce WebSocket");
  assert(!scriptContent.includes("EventSource"), "script does not introduce EventSource");
  assert(!scriptContent.includes("POST") && !scriptContent.includes("PUT") && !scriptContent.includes("DELETE"), "script does not call mutation APIs");

  // Verify prints
  assert(scriptContent.includes("echo \"LOCAL_INSTALL_REVIEW\""), "script prints LOCAL_INSTALL_REVIEW");
  assert(scriptContent.includes("echo \"ARCHIVE_VERIFIED\""), "script prints ARCHIVE_VERIFIED");
  assert(scriptContent.includes("echo \"INSTALL_REVIEW_EXTRACTED\""), "script prints INSTALL_REVIEW_EXTRACTED");
  assert(scriptContent.includes("echo \"NO_DEPLOYMENT\""), "script prints NO_DEPLOYMENT");
  assert(scriptContent.includes("echo \"NO_BACKEND_MUTATION\""), "script prints NO_BACKEND_MUTATION");

  // 7. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL INSTALL REVIEW CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL INSTALL REVIEW CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalInstallReviewTests();
