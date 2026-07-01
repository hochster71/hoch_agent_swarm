import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function runLocalInstallAcceptanceTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL INSTALL ACCEPTANCE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/36_local_install_acceptance.md');
  const installRoot = path.join(baseDir, 'artifacts/install-review/visual-control-plane-local');
  const installReviewFile = path.join(installRoot, 'install_review.json');
  const installAcceptanceFile = path.join(installRoot, 'install_acceptance.json');

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
  assert(fs.existsSync(docFile), "docs/visual-control-plane/36_local_install_acceptance.md exists");
  assert(fs.existsSync(installRoot), "install review root exists");
  assert(fs.existsSync(installReviewFile), "install_review.json exists");
  assert(fs.existsSync(installAcceptanceFile), "install_acceptance.json exists");

  if (!fs.existsSync(installAcceptanceFile) || !fs.existsSync(installReviewFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let acceptance: any;
  let review: any;

  try {
    acceptance = JSON.parse(fs.readFileSync(installAcceptanceFile, 'utf-8'));
    assert(true, "install_acceptance.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse install_acceptance.json: ${e.message}`);
    process.exit(1);
  }

  try {
    review = JSON.parse(fs.readFileSync(installReviewFile, 'utf-8'));
    assert(true, "install_review.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse install_review.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify extracted package files
  assert(fs.existsSync(path.join(installRoot, 'control-plane.html')), "control-plane.html exists");
  assert(fs.existsSync(path.join(installRoot, 'styles.css')), "styles.css exists");
  assert(fs.existsSync(path.join(installRoot, 'manifest.json')), "manifest.json exists");
  assert(fs.existsSync(path.join(installRoot, 'provenance.json')), "provenance.json exists");
  assert(fs.existsSync(path.join(installRoot, 'ROLLBACK.md')), "ROLLBACK.md exists");
  assert(fs.existsSync(path.join(installRoot, 'evidence')), "evidence folder exists");

  // 4. Verify acceptance metadata fields
  assert(acceptance.phase === "V27_LOCAL_INSTALL_ACCEPTANCE", "phase is V27_LOCAL_INSTALL_ACCEPTANCE");
  assert(acceptance.operator === "Michael Hoch", "operator is Michael Hoch");
  assert(acceptance.decision === "ACCEPT_LOCAL_INSTALL", "decision is ACCEPT_LOCAL_INSTALL");
  assert(acceptance.decision_scope === "local_only", "decision_scope is local_only");
  assert(acceptance.accepted_local_install === true, "accepted_local_install is true");
  assert(acceptance.install_review_performed === true, "install_review_performed is true");
  assert(acceptance.archive_verified === true, "archive_verified is true");
  assert(acceptance.extract_verified === true, "extract_verified is true");
  assert(acceptance.manifest_verified === true, "manifest_verified is true");
  assert(acceptance.provenance_verified === true, "provenance_verified is true");
  assert(acceptance.rollback_verified === true, "rollback_verified is true");
  assert(acceptance.evidence_verified === true, "evidence_verified is true");
  assert(Array.isArray(acceptance.checks_failed) && acceptance.checks_failed.length === 0, "checks_failed is empty");
  assert(acceptance.next_allowed_phase === "V28_FINAL_LOCAL_RELEASE_CLOSURE", "next_allowed_phase is V28_FINAL_LOCAL_RELEASE_CLOSURE");

  // 5. Verify safety gates
  assert(acceptance.deployment_performed === false, "deployment_performed is false");
  assert(acceptance.production_deployment_enabled === false, "production_deployment_enabled is false");
  assert(acceptance.external_publication_enabled === false, "external_publication_enabled is false");
  assert(acceptance.backend_mutation_enabled === false, "backend_mutation_enabled is false");
  assert(acceptance.prompt_execution_enabled === false, "prompt_execution_enabled is false");
  assert(acceptance.approval_decision_execution_enabled === false, "approval_decision_execution_enabled is false");
  assert(acceptance.security_posture_change_enabled === false, "security_posture_change_enabled is false");

  const blockedActions = [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ];
  blockedActions.forEach(action => {
    assert(acceptance.blocked_actions.includes(action), `Blocked action declared in acceptance: '${action}'`);
  });

  // 6. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL INSTALL ACCEPTANCE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL INSTALL ACCEPTANCE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalInstallAcceptanceTests();
