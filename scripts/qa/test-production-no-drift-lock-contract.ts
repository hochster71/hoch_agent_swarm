import * as fs from 'fs';
import * as path from 'path';

function runNoDriftLockTests() {
  console.log("==================================================");
  console.log("PRODUCTION NO-DRIFT LOCK VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr12Dir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');

  const manifestFile = path.join(pr12Dir, 'production_final_candidate_manifest.json');
  const lockFile = path.join(pr12Dir, 'production_readiness_track_lock.json');
  const registerFile = path.join(pr12Dir, 'production_no_drift_checksum_register.json');
  const policyFile = path.join(pr12Dir, 'production_no_drift_policy.json');
  const boundaryFile = path.join(pr12Dir, 'production_final_candidate_boundary_attestation.json');
  const blockedFile = path.join(pr12Dir, 'production_final_candidate_blocked_actions.json');
  const sealFile = path.join(pr12Dir, 'pr12a_final_seal.json');

  const pr11Manifest = path.join(baseDir, 'artifacts/production-readiness-remediation-validation/visual-control-plane-local-v1/production_validation_manifest.json');

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
  assert(fs.existsSync(manifestFile), "production_final_candidate_manifest.json exists");
  assert(fs.existsSync(lockFile), "production_readiness_track_lock.json exists");
  assert(fs.existsSync(registerFile), "production_no_drift_checksum_register.json exists");
  assert(fs.existsSync(policyFile), "production_no_drift_policy.json exists");
  assert(fs.existsSync(boundaryFile), "production_final_candidate_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "production_final_candidate_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr12a_final_seal.json exists");

  assert(fs.existsSync(pr11Manifest), "PR11 manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(lockFile) || !fs.existsSync(registerFile) || !fs.existsSync(policyFile) || !fs.existsSync(boundaryFile) || !fs.existsSync(blockedFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let trackLock: any;
  let register: any;
  let policy: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_final_candidate_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    trackLock = JSON.parse(fs.readFileSync(lockFile, 'utf-8'));
    assert(true, "production_readiness_track_lock.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse lock: ${e.message}`);
    process.exit(1);
  }

  try {
    register = JSON.parse(fs.readFileSync(registerFile, 'utf-8'));
    assert(true, "production_no_drift_checksum_register.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse register: ${e.message}`);
    process.exit(1);
  }

  try {
    policy = JSON.parse(fs.readFileSync(policyFile, 'utf-8'));
    assert(true, "production_no_drift_policy.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse policy: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "production_final_candidate_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "production_final_candidate_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr12a_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track_id === "PR12A", "Track ID is PR12A");
  assert(manifest.track_name === "Production Readiness No-Drift Lock", "Track name is correct");

  const requiredCert = "PR12A PRODUCTION READINESS NO-DRIFT LOCK — ACCEPTED FOR NO-DRIFT ENFORCEMENT ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify track lock contains PR1 through PR11
  const tracks = trackLock.accepted_tracks;
  assert(!!tracks, "accepted_tracks object exists");
  if (tracks) {
    const requiredTracks = ["PR1", "PR2", "PR3", "PR4", "PR5", "PR6", "PR7", "PR8", "PR9", "PR10", "PR11"];
    requiredTracks.forEach(t => {
      assert(!!tracks[t], `Track lock contains entry for ${t}`);
      assert(tracks[t].status === "ACCEPTED", `${t} status is ACCEPTED`);
    });
  }
  assert(trackLock.no_drift_status === "LOCKED", "no_drift_status is LOCKED");

  // 5. Verify checksum register contains non-empty SHA256 values and paths exist
  const reg = register.checksum_register;
  assert(!!reg, "checksum_register object exists");
  if (reg) {
    Object.keys(reg).forEach(relativeFile => {
      const entry = reg[relativeFile];
      assert(typeof entry.sha256 === 'string' && entry.sha256.length === 64, `File ${relativeFile} has valid SHA256 length`);
      assert(entry.locked === true, `File ${relativeFile} is locked`);
      
      const fullPath = path.join(baseDir, relativeFile);
      assert(fs.existsSync(fullPath), `Locked checksum path exists: ${relativeFile}`);
    });
  }

  // 6. Verify blocked actions
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

  const blockedList = blocked.production_final_candidate_blocked_actions;
  assert(Array.isArray(blockedList), "production_final_candidate_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 7. Verify no file claims execution performed
  const allJsonContents = [manifest, trackLock, register, policy, boundary, blocked, seal];
  allJsonContents.forEach(jsonObj => {
    const str = JSON.stringify(jsonObj);
    assert(!str.includes('"production_deployment": true') && 
           !str.includes('"performed": true') && 
           !str.includes('"git_push": true') && 
           !str.includes('"main_merge": true'), 
           "No file claims execution was performed");
  });

  // 8. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("PRODUCTION NO-DRIFT LOCK CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION NO-DRIFT LOCK CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runNoDriftLockTests();
