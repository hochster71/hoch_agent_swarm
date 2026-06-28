import * as fs from 'fs';
import * as path from 'path';

function runProductionFinalSealTests() {
  console.log("==================================================");
  console.log("PRODUCTION FINAL CANDIDATE SEAL VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr12Dir = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1');

  const manifestFile = path.join(pr12Dir, 'production_final_seal_manifest.json');
  const recordFile = path.join(pr12Dir, 'production_readiness_candidate_record.json');
  const boundaryFile = path.join(pr12Dir, 'candidate_boundary_attestation.json');
  const blockedFile = path.join(pr12Dir, 'candidate_blocked_actions.json');
  const sealFile = path.join(pr12Dir, 'pr12_final_seal.json');

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

  // 1. Verify PR12 files exist
  assert(fs.existsSync(manifestFile), "production_final_seal_manifest.json exists");
  assert(fs.existsSync(recordFile), "production_readiness_candidate_record.json exists");
  assert(fs.existsSync(boundaryFile), "candidate_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "candidate_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr12_final_seal.json exists");

  assert(fs.existsSync(pr11Manifest), "PR11 manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(recordFile) || !fs.existsSync(blockedFile) || !fs.existsSync(boundaryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let record: any;
  let boundary: any;
  let blocked: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_final_seal_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    record = JSON.parse(fs.readFileSync(recordFile, 'utf-8'));
    assert(true, "production_readiness_candidate_record.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse record: ${e.message}`);
    process.exit(1);
  }

  try {
    boundary = JSON.parse(fs.readFileSync(boundaryFile, 'utf-8'));
    assert(true, "candidate_boundary_attestation.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse boundary: ${e.message}`);
    process.exit(1);
  }

  try {
    blocked = JSON.parse(fs.readFileSync(blockedFile, 'utf-8'));
    assert(true, "candidate_blocked_actions.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse blocked: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr12_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR12_PRODUCTION_READINESS_FINAL_CANDIDATE_SEAL", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR12 PRODUCTION READINESS FINAL CANDIDATE SEAL — ACCEPTED FOR FINAL CANDIDATE SEAL ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify candidate record lists all tracks PR1 through PR11
  const rec = record.production_readiness_candidate_record;
  assert(!!rec, "production_readiness_candidate_record object exists");
  if (rec) {
    assert(rec.release === "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY", "Release version is correct");
    assert(rec.status === "SEALED_LOCAL_CANDIDATE", "Candidate status is SEALED_LOCAL_CANDIDATE");
    assert(Array.isArray(rec.consolidated_tracks), "consolidated_tracks is an array");
    
    const requiredTracks = ["PR1", "PR2", "PR3", "PR4", "PR5", "PR6", "PR7", "PR8", "PR9", "PR10", "PR11"];
    requiredTracks.forEach(t => {
      const entry = rec.consolidated_tracks.find((x: any) => x.track === t);
      assert(!!entry, `Candidate record contains entry for ${t}`);
      if (entry) {
        assert(entry.status === "ACCEPTED", `${t} status is ACCEPTED`);
        assert(typeof entry.head_commit === 'string' && entry.head_commit.length > 0, `${t} has head_commit`);
      }
    });

    const risks = rec.residual_risk_summary;
    assert(!!risks, "residual_risk_summary object exists");
    if (risks) {
      const riskKeys = ["RSK-TLS-001", "RSK-AUTH-002", "RSK-AUD-003", "RSK-MUT-004", "RSK-SPL-005", "RSK-OBS-006", "RSK-REC-007", "RSK-CMP-008"];
      riskKeys.forEach(k => {
        assert(risks[k] === "LOW", `Residual risk summary lists ${k} as LOW`);
      });
    }
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

  const blockedList = blocked.candidate_blocked_actions;
  assert(Array.isArray(blockedList), "candidate_blocked_actions is an array");
  requiredActions.forEach(actionName => {
    const act = blockedList.find((x: any) => x.action === actionName);
    assert(!!act, `Blocked actions contains entry for ${actionName}`);
    if (act) {
      assert(act.status === "BLOCKED", `${actionName} status is BLOCKED`);
      assert(act.performed === false, `${actionName} performed is false`);
    }
  });

  // 6. Verify no file claims execution performed
  const allJsonContents = [manifest, record, boundary, blocked, seal];
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
    console.error("PRODUCTION FINAL CANDIDATE SEAL CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION FINAL CANDIDATE SEAL CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionFinalSealTests();
