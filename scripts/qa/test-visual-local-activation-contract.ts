import * as fs from 'fs';
import * as path from 'path';

function runLocalActivationTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL ACTIVATION CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const flagsJsonFile = path.join(baseDir, 'config/visual_runtime_flags.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/17_feature_flagged_local_activation.md');

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
  assert(fs.existsSync(flagsJsonFile), "config/visual_runtime_flags.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/17_feature_flagged_local_activation.md exists");

  if (!fs.existsSync(flagsJsonFile) || !fs.existsSync(docFile)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse JSON Flags
  let flags: any;
  try {
    const rawJson = fs.readFileSync(flagsJsonFile, 'utf-8');
    flags = JSON.parse(rawJson);
    assert(true, "config/visual_runtime_flags.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config/visual_runtime_flags.json: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify safety & scope flags
  assert(flags.active_cockpit_replacement_enabled === false, "Safety check: active_cockpit_replacement_enabled is false");
  assert(flags.local_only === true, "Safety check: local_only is true");
  assert(flags.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(flags.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(flags.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(flags.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(flags.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(flags.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");
  assert(flags.rollback_required === true, "Safety check: rollback_required is true");

  // 4. Verify routes
  assert(flags.fallback_route === "mockups/visual-control-plane/control-plane.html", "Original cockpit route is referenced correctly");
  assert(flags.preview_route === "mockups/visual-control-plane/dashboard-preview.html", "Preview route is referenced correctly");
  assert(flags.side_by_side_route === "mockups/visual-control-plane/side-by-side-review.html", "Side-by-side route is referenced correctly");

  // 5. Verify documentation details
  const docContent = fs.readFileSync(docFile, 'utf-8');
  assert(docContent.includes("Rollback Procedure"), "Documentation contains Rollback Procedure");
  assert(docContent.includes("Michael Hoch"), "Documentation contains Michael Hoch approval sign-off");
  assert(docContent.includes("APPROVE_WITH_CHANGES"), "Documentation records APPROVE_WITH_CHANGES decision");

  // 6. Check that no disallowed network calls or side effects are introduced in files
  const previewHtmlFile = path.join(baseDir, 'mockups/visual-control-plane/dashboard-preview.html');
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  
  const htmlContent = fs.readFileSync(previewHtmlFile, 'utf-8');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket usage in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource usage in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");
  assert(!jsContent.includes('/decision'), "Safety check: No approval decision API endpoints referenced in preview JS");
  assert(!jsContent.includes('/execute') && !jsContent.includes('/kickoff'), "Safety check: No prompt execution API endpoints referenced in preview JS");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL ACTIVATION CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL ACTIVATION CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalActivationTests();
