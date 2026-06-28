import * as fs from 'fs';
import * as path from 'path';

function runProductionRiskTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL RISK REGISTER VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr8Dir = path.join(baseDir, 'artifacts/production-readiness-risk-register/visual-control-plane-local-v1');

  const manifestFile = path.join(pr8Dir, 'production_risk_manifest.json');
  const registerFile = path.join(pr8Dir, 'production_readiness_risk_register.json');
  const boundaryFile = path.join(pr8Dir, 'risk_boundary_attestation.json');
  const blockedFile = path.join(pr8Dir, 'risk_blocked_actions.json');
  const sealFile = path.join(pr8Dir, 'pr8_final_seal.json');

  const pr7Manifest = path.join(baseDir, 'artifacts/production-control-evidence-mapping/visual-control-plane-local-v1/production_evidence_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR8 files exist
  assert(fs.existsSync(manifestFile), "production_risk_manifest.json exists");
  assert(fs.existsSync(registerFile), "production_readiness_risk_register.json exists");
  assert(fs.existsSync(boundaryFile), "risk_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "risk_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr8_final_seal.json exists");

  assert(fs.existsSync(pr7Manifest), "PR7 evidence manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(registerFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_risk_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr8_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "PR8_PRODUCTION_READINESS_RISK_REGISTER_POAM", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR8 PRODUCTION READINESS RISK REGISTER & POA&M — ACCEPTED FOR RISK REGISTER & POA&M ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("PRODUCTION SECURITY CONTROL RISK REGISTER CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL RISK REGISTER CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionRiskTests();
