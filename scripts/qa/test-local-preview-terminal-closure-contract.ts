import * as fs from 'fs';
import * as path from 'path';

function runLocalPreviewTerminalClosureTests() {
  console.log("==================================================");
  console.log("LOCAL PREVIEW TERMINAL CLOSURE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p20Dir = path.join(baseDir, 'artifacts/terminal-local-preview-closure/visual-control-plane-local-v1');

  const manifestFile = path.join(p20Dir, 'terminal_closure_manifest.json');
  const logFile = path.join(p20Dir, 'full_workstream_acceptance_log.json');
  const boundaryFile = path.join(p20Dir, 'terminal_boundary_attestation.json');
  const blockedFile = path.join(p20Dir, 'terminal_blocked_actions_register.json');
  const decisionFile = path.join(p20Dir, 'terminal_operator_decision_record.json');
  const sealFile = path.join(p20Dir, 'p20_final_seal.json');

  const p19Manifest = path.join(baseDir, 'artifacts/immutable-local-preview-lock/visual-control-plane-local-v1/immutable_lock_manifest.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify P20 files exist
  assert(fs.existsSync(manifestFile), "terminal_closure_manifest.json exists");
  assert(fs.existsSync(logFile), "full_workstream_acceptance_log.json exists");
  assert(fs.existsSync(boundaryFile), "terminal_boundary_attestation.json exists");
  assert(fs.existsSync(blockedFile), "terminal_blocked_actions_register.json exists");
  assert(fs.existsSync(decisionFile), "terminal_operator_decision_record.json exists");
  assert(fs.existsSync(sealFile), "p20_final_seal.json exists");

  assert(fs.existsSync(p19Manifest), "P19 immutable lock manifest exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(logFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "terminal_closure_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p20_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P20_LOCAL_PREVIEW_TERMINAL_CLOSURE", "Track is correct");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P20 LOCAL PREVIEW WORKSTREAM TERMINAL CLOSURE — ACCEPTED FOR LOCAL PREVIEW TERMINAL CLOSURE ONLY";
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
    console.error("LOCAL PREVIEW TERMINAL CLOSURE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("LOCAL PREVIEW TERMINAL CLOSURE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalPreviewTerminalClosureTests();
