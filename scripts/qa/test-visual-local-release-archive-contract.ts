import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runLocalReleaseArchiveTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL RELEASE ARCHIVE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_local_release_archive.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/33_local_release_archive.md');
  const scriptFile = path.join(baseDir, 'scripts/visual/archive-local-release-package.sh');
  const archiveRoot = path.join(baseDir, 'artifacts/releases/visual-control-plane-local-archive');
  const tarFile = path.join(archiveRoot, 'visual-control-plane-local.tar.gz');
  const manifestFile = path.join(archiveRoot, 'archive_manifest.json');
  const reviewFile = path.join(archiveRoot, 'archive_review.json');
  const checksumFile = path.join(archiveRoot, 'archive_checksums.sha256');

  const sourceFreezeFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local/freeze_record.json');
  const sourceLedgerFile = path.join(baseDir, 'artifacts/releases/visual-control-plane-local/hash_ledger.json');

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
  assert(fs.existsSync(docFile), "docs/visual-control-plane/33_local_release_archive.md exists");
  assert(fs.existsSync(configJsonFile), "config/visual_local_release_archive.json exists");
  assert(fs.existsSync(scriptFile), "archive script exists");
  assert(fs.existsSync(archiveRoot), "archive root exists");
  assert(fs.existsSync(tarFile), "visual-control-plane-local.tar.gz exists");
  assert(fs.existsSync(manifestFile), "archive_manifest.json exists");
  assert(fs.existsSync(reviewFile), "archive_review.json exists");
  assert(fs.existsSync(checksumFile), "archive_checksums.sha256 exists");
  assert(fs.existsSync(sourceFreezeFile), "source freeze_record.json exists");
  assert(fs.existsSync(sourceLedgerFile), "source hash_ledger.json exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(manifestFile) || !fs.existsSync(reviewFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let manifest: any;
  let review: any;
  let sourceFreeze: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_local_release_archive.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "archive_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse archive manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    review = JSON.parse(fs.readFileSync(reviewFile, 'utf-8'));
    assert(true, "archive_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse archive review: ${e.message}`);
    process.exit(1);
  }

  try {
    sourceFreeze = JSON.parse(fs.readFileSync(sourceFreezeFile, 'utf-8'));
    assert(true, "source freeze_record.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse source freeze record: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify freeze pre-requisites
  assert(sourceFreeze.freeze_declared === true, "source freeze_declared is true");

  // 4. Verify config flags
  assert(config.local_only === true, "config local_only is true");
  assert(config.archive_created === true, "config archive_created is true");
  assert(config.deployment_performed === false, "config deployment_performed is false");
  assert(config.external_publication_enabled === false, "config external_publication_enabled is false");
  assert(config.production_deployment_enabled === false, "config production_deployment_enabled is false");
  assert(config.backend_mutation_enabled === false, "config backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "config prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "config approval_decision_execution_enabled is false");
  assert(config.security_posture_change_enabled === false, "config security_posture_change_enabled is false");
  assert(config.next_allowed_phase === "V25_LOCAL_RELEASE_FINAL_REVIEW", "Config next_allowed_phase check");

  // 5. Verify review flags
  assert(review.local_only === true, "archive review local_only check");
  assert(review.archive_created === true, "archive review archive_created is true");
  assert(review.archive_checksum_verified === true, "archive review archive_checksum_verified is true");
  assert(review.source_freeze_verified === true, "archive review source_freeze_verified is true");
  assert(review.deployment_performed === false, "archive review deployment_performed is false");
  assert(review.external_publication_enabled === false, "archive review external_publication_enabled is false");
  assert(review.production_deployment_enabled === false, "archive review production_deployment_enabled is false");
  assert(review.backend_mutation_enabled === false, "archive review backend_mutation_enabled is false");
  assert(review.prompt_execution_enabled === false, "archive review prompt_execution_enabled is false");
  assert(review.approval_decision_execution_enabled === false, "archive review approval_decision_execution_enabled is false");
  assert(review.security_posture_change_enabled === false, "archive review security_posture_change_enabled is false");
  assert(review.checks_failed.length === 0, "checks_failed is empty");

  // 6. Verify tarball sha & size matches manifest & checksums
  const actualSha = getSha256(tarFile);
  const actualSize = fs.statSync(tarFile).size;

  assert(manifest.archive_sha256 === actualSha, `archive manifest archive_sha256 matches actual archive file: ${actualSha}`);
  assert(manifest.archive_size_bytes === actualSize, `archive manifest archive_size_bytes matches actual archive file: ${actualSize}`);

  const checksumContent = fs.readFileSync(checksumFile, 'utf-8');
  assert(checksumContent.includes(actualSha), "archive_checksums.sha256 contains the archive sha256");

  // 7. Verify blocked actions in review
  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(manifest.blocked_actions.includes(action), `Blocked action declared in manifest: '${action}'`);
  });

  // 8. Verify script structure
  const scriptContent = fs.readFileSync(scriptFile, 'utf-8');
  assert(scriptContent.includes("set -euo pipefail"), "script uses set -euo pipefail");
  assert(!scriptContent.includes("rm -rf"), "script does not contain rm -rf");
  assert(!scriptContent.includes("backend/"), "script does not reference backend/");

  // Verify no execution or mutation APIs
  assert(!scriptContent.includes("WebSocket"), "script does not introduce WebSocket");
  assert(!scriptContent.includes("EventSource"), "script does not introduce EventSource");
  assert(!scriptContent.includes("POST") && !scriptContent.includes("PUT") && !scriptContent.includes("DELETE"), "script does not call mutation APIs");

  // Verify prints
  assert(scriptContent.includes("echo \"LOCAL_RELEASE_ARCHIVE\""), "script prints LOCAL_RELEASE_ARCHIVE");
  assert(scriptContent.includes("echo \"ARCHIVE_CREATED\""), "script prints ARCHIVE_CREATED");
  assert(scriptContent.includes("echo \"CHECKSUM_WRITTEN\""), "script prints CHECKSUM_WRITTEN");
  assert(scriptContent.includes("echo \"NO_DEPLOYMENT\""), "script prints NO_DEPLOYMENT");
  assert(scriptContent.includes("echo \"NO_BACKEND_MUTATION\""), "script prints NO_BACKEND_MUTATION");

  // 9. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL RELEASE ARCHIVE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL RELEASE ARCHIVE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalReleaseArchiveTests();
