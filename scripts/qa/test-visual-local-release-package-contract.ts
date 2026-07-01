import * as fs from 'fs';
import * as path from 'path';

function runLocalReleasePackageTests() {
  console.log("==================================================");
  console.log("VISUAL LOCAL RELEASE PACKAGE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const configJsonFile = path.join(baseDir, 'config/visual_local_release_package.json');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/30_local_release_package.md');
  const releaseRoot = path.join(baseDir, 'artifacts/releases/visual-control-plane-local');

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
  assert(fs.existsSync(configJsonFile), "config/visual_local_release_package.json exists");
  assert(fs.existsSync(docFile), "docs/visual-control-plane/30_local_release_package.md exists");
  assert(fs.existsSync(releaseRoot), "release root exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(releaseRoot)) {
    console.error("Critical files missing, aborting test run.");
    process.exit(1);
  }

  // 2. Parse config
  let config: any;
  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_local_release_package.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify config flags
  assert(config.local_only === true, "Config local_only is true");
  assert(config.package_created === true, "Config package_created is true");
  assert(config.deployment_performed === false, "Config deployment_performed is false");
  assert(config.production_deployment_enabled === false, "Config production_deployment_enabled is false");
  assert(config.external_publication_enabled === false, "Config external_publication_enabled is false");
  assert(config.backend_mutation_enabled === false, "Config backend_mutation_enabled is false");
  assert(config.prompt_execution_enabled === false, "Config prompt_execution_enabled is false");
  assert(config.approval_decision_execution_enabled === false, "Config approval_decision_execution_enabled is false");
  assert(config.security_posture_change_enabled === false, "Config security_posture_change_enabled is false");
  assert(config.next_allowed_phase === "V22_LOCAL_RELEASE_REVIEW", "Config next_allowed_phase is V22_LOCAL_RELEASE_REVIEW");

  // 4. Verify release files
  const readmeFile = path.join(releaseRoot, 'README.md');
  const manifestFile = path.join(releaseRoot, 'manifest.json');
  const provenanceFile = path.join(releaseRoot, 'provenance.json');
  const cockpitFile = path.join(releaseRoot, 'control-plane.html');
  const stylesFile = path.join(releaseRoot, 'styles.css');
  const rollbackFile = path.join(releaseRoot, 'ROLLBACK.md');

  assert(fs.existsSync(readmeFile), "README exists");
  assert(fs.existsSync(manifestFile), "manifest.json exists");
  assert(fs.existsSync(provenanceFile), "provenance.json exists");
  assert(fs.existsSync(cockpitFile), "release control-plane.html exists");
  assert(fs.existsSync(stylesFile), "release styles.css exists");
  assert(fs.existsSync(rollbackFile), "release ROLLBACK.md exists");

  // 5. Parse manifest
  let manifest: any;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  assert(manifest.local_only === true, "Manifest local_only is true");
  assert(manifest.deployment_performed === false, "Manifest deployment_performed is false");
  assert(manifest.package_name === "visual-control-plane-local", "Manifest package_name is correct");
  assert(manifest.package_type === "local_release_package", "Manifest package_type is correct");
  assert(manifest.accepted_commit_head !== "", "Manifest contains accepted_commit_head");

  // Verify sha256 entries in manifest files
  manifest.files.forEach((f: any) => {
    assert(f.sha256 && f.sha256.length === 64, `Manifest file entry for ${f.path} contains valid sha256`);
  });

  // Verify evidence files in manifest
  manifest.evidence.forEach((e: any) => {
    assert(e.sha256 && e.sha256.length === 64, `Manifest evidence entry for ${e.path} contains valid sha256`);
    const absPath = path.join(baseDir, e.path);
    assert(fs.existsSync(absPath), `Evidence file exists at ${absPath}`);
  });

  // 6. Parse provenance
  let provenance: any;
  try {
    provenance = JSON.parse(fs.readFileSync(provenanceFile, 'utf-8'));
    assert(true, "provenance.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse provenance: ${e.message}`);
    process.exit(1);
  }

  assert(provenance.source_branch !== "", "Provenance contains source_branch");
  assert(provenance.source_head !== "", "Provenance contains source_head");
  assert(provenance.builder === "HOCH Agent Swarm Antigravity local workflow", "Provenance contains builder");
  assert(provenance.deployment_performed === false, "Provenance deployment_performed is false");
  assert(provenance.external_publication_enabled === false, "Provenance external_publication_enabled is false");

  // 7. Verify README content
  const readmeContent = fs.readFileSync(readmeFile, 'utf-8');
  assert(readmeContent.includes("LOCAL RELEASE PACKAGE ONLY"), "README contains LOCAL RELEASE PACKAGE ONLY");
  assert(readmeContent.includes("NOT PRODUCTION DEPLOYMENT"), "README contains NOT PRODUCTION DEPLOYMENT");
  assert(readmeContent.includes("NO BACKEND MUTATION"), "README contains NO BACKEND MUTATION");
  assert(readmeContent.includes("NO PROMPT EXECUTION"), "README contains NO PROMPT EXECUTION");
  assert(readmeContent.includes("NO APPROVAL DECISION EXECUTION"), "README contains NO APPROVAL DECISION EXECUTION");

  // 8. Safety check: No mutations or websocket interfaces in cockpit js files
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL LOCAL RELEASE PACKAGE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL LOCAL RELEASE PACKAGE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runLocalReleasePackageTests();
