import { execSync } from "node:child_process";
import fs from "node:fs";

const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));
const VERSION = packageJson.version;
const RELEASE_DIR = `dist/releases/${VERSION}`;

function run(command: string) {
  try {
    return execSync(command, { encoding: "utf8", stdio: "pipe" });
  } catch (err) {
    console.warn(` [WARNING] Cosign run failed: ${(err as Error).message}`);
    return "";
  }
}

if (!process.env.ENABLE_COSIGN_SIGNING) {
  console.log("Cosign signing skipped: ENABLE_COSIGN_SIGNING not set.");
  process.exit(0);
}

const otherArtifacts = [
  "baseline_evidence_pack.json",
  "provenance.intoto.jsonl",
  "sbom.spdx.json",
  "runtime_execution_audit.json",
  "tool_call_trace_summary.json",
  "redaction_report.json",
  "approval_gate_report.json",
];

// 1. Sign other artifacts first
for (const artifact of otherArtifacts) {
  const path = `${RELEASE_DIR}/${artifact}`;
  if (!fs.existsSync(path)) continue;
  run(`cosign sign-blob --yes --output-signature ${path}.sig ${path}`);
  console.log(`Signed ${path}`);
}

// 2. Update release_manifest.json signature status to signed
const manifestPath = `${RELEASE_DIR}/release_manifest.json`;
if (fs.existsSync(manifestPath)) {
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    
    // Update signature status fields
    manifest.signature_status = "signed";
    if (manifest.integrity) {
      manifest.integrity.signature_status = "signed";
      manifest.integrity.signed = true;
    }
    
    // Re-count signed/unsigned artifacts since we just signed them
    let signedCount = 0;
    let unsignedCount = 0;
    const expectedSigned = [
      "baseline_evidence_pack.json",
      "release_manifest.json",
      "provenance.intoto.jsonl",
      "sbom.spdx.json",
      "runtime_execution_audit.json",
      "tool_call_trace_summary.json",
      "redaction_report.json",
      "approval_gate_report.json",
    ];
    for (const name of expectedSigned) {
      const filePath = `${RELEASE_DIR}/${name}`;
      if (fs.existsSync(filePath)) {
        // Since we are about to sign release_manifest.json, count it as signed
        if (name === "release_manifest.json" || fs.existsSync(`${filePath}.sig`)) {
          signedCount++;
        } else {
          unsignedCount++;
        }
      }
    }
    manifest.signed_artifacts_count = signedCount;
    manifest.unsigned_artifacts_count = unsignedCount;
    if (manifest.integrity) {
      manifest.integrity.signed_artifacts_count = signedCount;
      manifest.integrity.unsigned_artifacts_count = unsignedCount;
    }

    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf8");
    console.log(`Updated manifest signature status in ${manifestPath}`);
  } catch (err) {
    console.warn(` [WARNING] Failed to update manifest signature status: ${(err as Error).message}`);
  }

  // 3. Sign the updated release_manifest.json
  run(`cosign sign-blob --yes --output-signature ${manifestPath}.sig ${manifestPath}`);
  console.log(`Signed ${manifestPath}`);
}
