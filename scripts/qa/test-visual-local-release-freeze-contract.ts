import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runLocalReleaseFreezeTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL RELEASE FREEZE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_local_release_freeze.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/32_local_release_freeze.md');
  const releaseRoot = path.join(baseDir, 'artifacts/releases/visual-control-plane-local');
  const freezeRecordFile = path.join(releaseRoot, 'freeze_record.json');
  const hashLedgerFile = path.join(releaseRoot, 'hash_ledger.json');
  const freezeMdFile = path.join(releaseRoot, 'FREEZE.md');
  const manifestFile = path.join(releaseRoot, 'manifest.json');
  const provenanceFile = path.join(releaseRoot, 'provenance.json');
  const reviewFile = path.join(releaseRoot, 'release_review.json');

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
  assert(fs.existsSync(configJsonFile), "config/visual_local_release_freeze.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/32_local_release_freeze.md exists");
  assert(fs.existsSync(releaseRoot), "release root exists");
  assert(fs.existsSync(freezeRecordFile), "freeze_record.json exists");
  assert(fs.existsSync(hashLedgerFile), "hash_ledger.json exists");
  assert(fs.existsSync(freezeMdFile), "FREEZE.md exists");
  assert(fs.existsSync(manifestFile), "manifest.json exists");
  assert(fs.existsSync(provenanceFile), "provenance.json exists");
  assert(fs.existsSync(reviewFile), "release_review.json exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(freezeRecordFile) || !fs.existsSync(hashLedgerFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let record: any;
  let ledger: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_local_release_freeze.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    record = JSON.parse(fs.readFileSync(freezeRecordFile, 'utf-8'));
    assert(true, "freeze_record.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse freeze_record.json: ${e.message}`);
    process.exit(1);
  }

  try {
    ledger = JSON.parse(fs.readFileSync(hashLedgerFile, 'utf-8'));
    assert(true, "hash_ledger.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse hash_ledger.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety flags in config
  assert(config.phase === "V23_LOCAL_RELEASE_FREEZE", "Config phase check: V23_LOCAL_RELEASE_FREEZE");
  assert(config.local_only === true, "Config local_only is true");
  assert(config.freeze_declared === true, "Config freeze_declared is true");
  assert(config.deployment_performed === false, "Config deployment_performed is false");
  assert(config.external_publication_enabled === false, "Config external_publication_enabled is false");
  assert(config.production_deployment_enabled === false, "Config production_deployment_enabled is false");
  assert(config.backend_mutation_enabled === false, "Config backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "Config prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "Config approval_decision_execution_enabled is false");
  assert(config.security_posture_change_enabled === false, "Config security_posture_change_enabled is false");
  assert(config.next_allowed_phase === "V24_LOCAL_RELEASE_ARCHIVE", "Config next_allowed_phase is V24_LOCAL_RELEASE_ARCHIVE");

  // 4. Verify safety flags in record
  assert(record.phase === "V23_LOCAL_RELEASE_FREEZE", "Record phase check: V23_LOCAL_RELEASE_FREEZE");
  assert(record.local_only === true, "Record local_only is true");
  assert(record.freeze_declared === true, "Record freeze_declared is true");
  assert(record.deployment_performed === false, "Record deployment_performed is false");
  assert(record.source_review_status === "REVIEW_COMPLETE", "Record source_review_status is REVIEW_COMPLETE");
  assert(record.manifest_verified === true, "Record manifest_verified is true");
  assert(record.provenance_verified === true, "Record provenance_verified is true");
  assert(record.rollback_verified === true, "Record rollback_verified is true");
  assert(record.evidence_verified === true, "Record evidence_verified is true");
  assert(record.hashes_verified === true, "Record hashes_verified is true");
  assert(Array.isArray(record.checks_failed) && record.checks_failed.length === 0, "Record checks_failed is empty");
  assert(Array.isArray(record.frozen_files) && record.frozen_files.length > 0, "Record frozen_files is not empty");

  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(record.blocked_actions.includes(action), `Freeze record blocks action: '${action}'`);
  });

  // 5. Verify Hash Ledger alignment
  assert(ledger.phase === "V23_LOCAL_RELEASE_FREEZE", "Ledger phase check");
  assert(ledger.local_only === true, "Ledger local_only is true");
  assert(ledger.deployment_performed === false, "Ledger deployment_performed is false");
  assert(ledger.external_publication_enabled === false, "Ledger external_publication_enabled is false");

  ledger.files.forEach((fileEntry: any) => {
    assert(fileEntry.path !== "", "Ledger entry path is not empty");
    assert(fileEntry.sha256 && fileEntry.sha256.length === 64, "Ledger entry sha256 is valid");
    assert(typeof fileEntry.size_bytes === "number" && fileEntry.size_bytes > 0, "Ledger entry size_bytes is positive number");

    const fileAbsPath = path.join(baseDir, fileEntry.path);
    assert(fs.existsSync(fileAbsPath), `Ledger file exists: ${fileEntry.path}`);
    if (fs.existsSync(fileAbsPath)) {
      const actualHash = getSha256(fileAbsPath);
      assert(actualHash === fileEntry.sha256, `Ledger hash match verified for ${fileEntry.path}`);
    }
  });

  // 6. Verify FREEZE.md contents
  const freezeMdContent = fs.readFileSync(freezeMdFile, 'utf-8');
  assert(freezeMdContent.includes("LOCAL RELEASE FREEZE ONLY"), "FREEZE.md contains LOCAL RELEASE FREEZE ONLY");
  assert(freezeMdContent.includes("NOT PRODUCTION DEPLOYMENT"), "FREEZE.md contains NOT PRODUCTION DEPLOYMENT");
  assert(freezeMdContent.includes("DO NOT MODIFY RELEASE PACKAGE WITHOUT NEW PHASE"), "FREEZE.md contains modification warning");
  assert(freezeMdContent.includes("NO BACKEND MUTATION"), "FREEZE.md contains NO BACKEND MUTATION");
  assert(freezeMdContent.includes("NO PROMPT EXECUTION"), "FREEZE.md contains NO PROMPT EXECUTION");
  assert(freezeMdContent.includes("NO APPROVAL DECISION EXECUTION"), "FREEZE.md contains NO APPROVAL DECISION EXECUTION");

  // 7. Safety check: No mutations or websocket interfaces
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL RELEASE FREEZE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL RELEASE FREEZE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalReleaseFreezeTests();
