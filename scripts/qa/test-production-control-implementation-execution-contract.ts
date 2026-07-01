import * as fs from 'fs';
import * as path from 'path';

function runProductionExecutionTests() {
  console.log("==================================================");
  console.log("PRODUCTION SECURITY CONTROL EXECUTION VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const pr5Dir = path.join(baseDir, 'artifacts/production-control-implementation-execution/visual-control-plane-local-v1');
  const hardeningDir = path.join(baseDir, 'backend/production_hardening');

  const manifestFile = path.join(pr5Dir, 'production_execution_manifest.json');
  const boundaryFile = path.join(pr5Dir, 'production_execution_boundary_attestation.json');
  const blockedFile = path.join(pr5Dir, 'production_execution_blocked_actions.json');
  const sealFile = path.join(pr5Dir, 'pr5_final_seal.json');

  const pr4Manifest = path.join(baseDir, 'artifacts/production-control-implementation-plan/visual-control-plane-local-v1/production_implementation_plan_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify PR5 files exist
  assert(fs.existsSync(manifestFile), "production_execution_manifest.json exists");
  assert(fs.existsSync(boundaryFile), "production_execution_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "production_execution_blocked_actions.json exists");
  assert(fs.existsSync(sealFile), "pr5_final_seal.json exists");

  assert(fs.existsSync(pr4Manifest), "PR4 implementation plan manifest exists");

  // 2. Verify Scaffolding files exist
  assert(fs.existsSync(path.join(hardeningDir, 'tls_scaffolding.py')), "tls_scaffolding.py exists");
  assert(fs.existsSync(path.join(hardeningDir, 'auth_adapter.py')), "auth_adapter.py exists");
  assert(fs.existsSync(path.join(hardeningDir, 'audit_ledger_helper.py')), "audit_ledger_helper.py exists");
  assert(fs.existsSync(path.join(hardeningDir, 'mutation_gate.py')), "mutation_gate.py exists");
  assert(fs.existsSync(path.join(hardeningDir, 'observability_scaffolding.py')), "observability_scaffolding.py exists");
  assert(fs.existsSync(path.join(hardeningDir, 'backup_recovery_scripts.py')), "backup_recovery_scripts.py exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 3. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "production_execution_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "pr5_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 4. Verify details
  assert(manifest.track === "PR5_PRODUCTION_SECURITY_CONTROL_IMPLEMENTATION_EXECUTION", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "PR5 PRODUCTION SECURITY CONTROL IMPLEMENTATION EXECUTION — ACCEPTED FOR CONTROL IMPLEMENTATION REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 5. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("PRODUCTION SECURITY CONTROL EXECUTION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PRODUCTION SECURITY CONTROL EXECUTION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runProductionExecutionTests();
