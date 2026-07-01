import * as fs from 'fs';
import * as path from 'path';

function runUiScreenshotEvidenceTests() {
  console.log("==================================================");
  console.log("VISUAL SCREENSHOT EVIDENCE VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const p11Dir = path.join(baseDir, 'artifacts/ui-screenshot-evidence/visual-control-plane-local-v1');
  const screenshotsDir = path.join(p11Dir, 'screenshots');

  const manifestFile = path.join(p11Dir, 'screenshot_evidence_manifest.json');
  const routeFile = path.join(p11Dir, 'route_discovery_report.json');
  const inventoryFile = path.join(p11Dir, 'screenshot_inventory.json');
  const resultsFile = path.join(p11Dir, 'screenshot_capture_results.json');
  const missingFile = path.join(p11Dir, 'missing_route_register.json');
  const notesFile = path.join(p11Dir, 'visual_review_notes.json');
  const attestationFile = path.join(p11Dir, 'screenshot_boundary_attestation.json');
  const sealFile = path.join(p11Dir, 'p11_final_seal.json');

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
  assert(fs.existsSync(manifestFile), "screenshot_evidence_manifest.json exists");
  assert(fs.existsSync(routeFile), "route_discovery_report.json exists");
  assert(fs.existsSync(inventoryFile), "screenshot_inventory.json exists");
  assert(fs.existsSync(resultsFile), "screenshot_capture_results.json exists");
  assert(fs.existsSync(missingFile), "missing_route_register.json exists");
  assert(fs.existsSync(notesFile), "visual_review_notes.json exists");
  assert(fs.existsSync(attestationFile), "screenshot_boundary_attestation.json exists");
  assert(fs.existsSync(sealFile), "p11_final_seal.json exists");

  if (!fs.existsSync(manifestFile) || !fs.existsSync(sealFile) || !fs.existsSync(inventoryFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let manifest: any;
  let seal: any;
  let inventory: any;

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "screenshot_evidence_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    seal = JSON.parse(fs.readFileSync(sealFile, 'utf-8'));
    assert(true, "p11_final_seal.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse seal: ${e.message}`);
    process.exit(1);
  }

  try {
    inventory = JSON.parse(fs.readFileSync(inventoryFile, 'utf-8'));
    assert(true, "screenshot_inventory.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse inventory: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify details
  assert(manifest.track === "P11_SCREENSHOT_VISUAL_EVIDENCE_CAPTURE", "Track is P11_SCREENSHOT_VISUAL_EVIDENCE_CAPTURE");
  assert(manifest.local_preview_only === true, "local_preview_only is true");

  const requiredCert = "P11 SCREENSHOT / VISUAL EVIDENCE CAPTURE — ACCEPTED FOR LOCAL PREVIEW VISUAL REVIEW ONLY";
  assert(seal.final_certification === requiredCert, "Final certification in JSON matches required wording");
  assert(seal.seal_status === "PASS", "Seal status is PASS");

  // 4. Verify screenshots directory and files
  assert(fs.existsSync(screenshotsDir), "Screenshots directory exists");
  const files = fs.readdirSync(screenshotsDir);
  assert(files.length > 0, `Screenshots folder contains files (${files.length} found)`);

  const pngFiles = files.filter(f => f.endsWith('.png'));
  assert(pngFiles.length >= 1, `Contains at least one PNG file (${pngFiles.length} found)`);

  // Verify that every PNG is mapped in the inventory.json
  pngFiles.forEach(png => {
    assert(inventory.inventory[png] !== undefined, `PNG file ${png} is documented in screenshot_inventory.json`);
  });

  // 5. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL SCREENSHOT EVIDENCE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL SCREENSHOT EVIDENCE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runUiScreenshotEvidenceTests();
