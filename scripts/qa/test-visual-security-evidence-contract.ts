import * as fs from 'fs';
import * as path from 'path';

function runSecurityEvidenceTests() {
  console.log("==================================================");
  console.log("VISUAL SECURITY EVIDENCE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docFile = path.join(baseDir, 'docs/security-evidence/visual-control-plane-local-v1.md');
  const configJsonFile = path.join(baseDir, 'config/visual_control_plane_security_evidence.json');

  const evidenceDir = path.join(baseDir, 'artifacts/security-evidence/visual-control-plane-local-v1');
  const manifestFile = path.join(evidenceDir, 'security_evidence_manifest.json');
  const reportFile = path.join(evidenceDir, 'ato_readiness_report.json');

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
  assert(fs.existsSync(docFile), "docs/security-evidence/visual-control-plane-local-v1.md exists");
  assert(fs.existsSync(configJsonFile), "config/visual_control_plane_security_evidence.json exists");
  assert(fs.existsSync(manifestFile), "security_evidence_manifest.json exists");
  assert(fs.existsSync(reportFile), "ato_readiness_report.json exists");

  if (!fs.existsSync(configJsonFile) || !fs.existsSync(manifestFile) || !fs.existsSync(reportFile)) {
    console.error("Critical files missing, aborting test.");
    process.exit(1);
  }

  // 2. Parse JSONs
  let config: any;
  let manifest: any;
  let report: any;

  try {
    config = JSON.parse(fs.readFileSync(configJsonFile, 'utf-8'));
    assert(true, "config/visual_control_plane_security_evidence.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse config: ${e.message}`);
    process.exit(1);
  }

  try {
    manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf-8'));
    assert(true, "security_evidence_manifest.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse manifest: ${e.message}`);
    process.exit(1);
  }

  try {
    report = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
    assert(true, "ato_readiness_report.json parses cleanly");
  } catch (e: any) {
    assert(false, `Failed to parse report: ${e.message}`);
    process.exit(1);
  }

  // 3. Verify config details
  assert(config.track === "P4_SECURITY_ATO_EVIDENCE_PACKAGING", "Track is P4_SECURITY_ATO_EVIDENCE_PACKAGING");
  assert(config.release_tag === "visual-control-plane-local-v1.0.0", "Release tag check");
  assert(config.integration_branch === "integration/visual-control-plane-local-v1", "Integration branch check");
  assert(config.evidence_package_status === "ATO_READY", "Evidence package status check");

  // 4. Verify manifest details
  assert(manifest.phase === "P4_SECURITY_ATO_EVIDENCE_PACKAGING", "Manifest phase check");
  assert(manifest.evidence_manifest_status === "CERTIFIED", "Manifest status check");
  assert(manifest.security_evaluation.nist_ssdf_compliant === true, "SSDF compliant");
  assert(manifest.security_evaluation.slsa_provenance_verified === true, "SLSA verified");
  assert(manifest.security_evaluation.sbom_transparency_passed === true, "SBOM passed");

  // 5. Verify all referenced evidence files exist on disk
  manifest.evidence_files.forEach((fileRelPath: string) => {
    const fullPath = path.join(baseDir, fileRelPath);
    assert(fs.existsSync(fullPath), `Evidence file exists: ${fileRelPath}`);
  });

  // 6. Verify report details
  assert(report.phase === "P4_ATO_READINESS_REPORT", "Report phase check");
  assert(report.ato_readiness_score === 100, "ATO readiness score is 100");
  assert(report.ato_recommendation === "AUTHORIZE_LOCAL_PREVIEW", "ATO recommendation check");

  // 7. Safety check: No mutations or websocket interfaces in preview JS
  const previewJsFile = path.join(baseDir, 'frontend/visual_dashboard_preview.js');
  const jsContent = fs.readFileSync(previewJsFile, 'utf-8');

  assert(!jsContent.includes('WebSocket'), "Safety check: No WebSocket in visual_dashboard_preview.js");
  assert(!jsContent.includes('EventSource'), "Safety check: No EventSource in visual_dashboard_preview.js");
  assert(!jsContent.includes('POST') && !jsContent.includes('PUT') && !jsContent.includes('DELETE'), "Safety check: No POST/PUT/DELETE fetch calls in visual_dashboard_preview.js");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL SECURITY EVIDENCE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL SECURITY EVIDENCE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runSecurityEvidenceTests();
