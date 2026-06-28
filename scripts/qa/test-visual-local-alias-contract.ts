import * as fs from 'fs';
import * as path from 'path';

function runLocalAliasTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL ALIAS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const flagsJsonFile = path.join(baseDir, 'config/visual_runtime_flags.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/19_local_cockpit_alias_activation.md');
  const aliasHtmlFile = path.join(baseDir, 'mockups/visual-control-plane/local-cockpit-alias.html');

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
  assert(fs.existsSync(docFile), "docs/visual-control-plane/19_local_cockpit_alias_activation.md exists");
  assert(fs.existsSync(aliasHtmlFile), "local-cockpit-alias.html exists");

  if (!fs.existsSync(flagsJsonFile) || !fs.existsSync(docFile) || !fs.existsSync(aliasHtmlFile)) {
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
  assert(flags.visual_cockpit_alias_enabled === true, "Safety check: visual_cockpit_alias_enabled is true");
  assert(flags.local_only === true, "Safety check: local_only is true");
  assert(flags.backend_mutation_enabled === false, "Safety check: backend_mutation_enabled is false");
  assert(flags.prompt_execution_enabled === false, "Safety check: prompt_execution_enabled is false");
  assert(flags.approval_decision_execution_enabled === false, "Safety check: approval_decision_execution_enabled is false");
  assert(flags.external_publication_enabled === false, "Safety check: external_publication_enabled is false");
  assert(flags.production_deployment_enabled === false, "Safety check: production_deployment_enabled is false");
  assert(flags.security_posture_change_enabled === false, "Safety check: security_posture_change_enabled is false");
  assert(flags.rollback_required === true, "Safety check: rollback_required is true");
  assert(flags.michael_hoch_final_approval_recorded === true, "Safety check: michael_hoch_final_approval_recorded is true");

  // 4. Verify routes
  assert(flags.fallback_route === "mockups/visual-control-plane/control-plane.html", "Original cockpit route is referenced correctly");
  assert(flags.preview_route === "mockups/visual-control-plane/dashboard-preview.html", "Preview route is referenced correctly");
  assert(flags.side_by_side_route === "mockups/visual-control-plane/side-by-side-review.html", "Side-by-side route is referenced correctly");
  assert(flags.alias_route === "mockups/visual-control-plane/local-cockpit-alias.html", "Alias route is referenced correctly");

  // 5. Verify alias html contents
  const aliasContent = fs.readFileSync(aliasHtmlFile, 'utf-8');
  assert(aliasContent.includes("local-cockpit-alias.html") || aliasContent.includes("control-plane.html"), "local-cockpit-alias.html links back to baseline cockpit");
  assert(aliasContent.includes("dashboard-preview.html"), "local-cockpit-alias.html links/frames dashboard-preview.html");

  // 6. Verify documentation details
  const docContent = fs.readFileSync(docFile, 'utf-8');
  assert(docContent.includes("Rollback Procedure"), "Documentation contains Rollback Procedure");
  assert(docContent.includes("Michael Hoch"), "Documentation contains Michael Hoch approval sign-off");
  assert(docContent.includes("FINAL_APPROVE_LOCAL_ACTIVATION"), "Documentation records FINAL_APPROVE_LOCAL_ACTIVATION decision");

  // 7. Check no disallowed mutations in script blocks of alias
  assert(!aliasContent.includes("WebSocket"), "Safety check: No WebSocket usage in alias html");
  assert(!aliasContent.includes("EventSource"), "Safety check: No EventSource usage in alias html");
  assert(!aliasContent.includes("POST") && !aliasContent.includes("PUT") && !aliasContent.includes("DELETE"), "Safety check: No POST/PUT/DELETE fetch calls in alias html");
  assert(!aliasContent.includes("/decision"), "Safety check: No decision API endpoints referenced in alias html");
  assert(!aliasContent.includes("/execute") && !aliasContent.includes("/kickoff"), "Safety check: No execution API endpoints referenced in alias html");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL ALIAS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL ALIAS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalAliasTests();
