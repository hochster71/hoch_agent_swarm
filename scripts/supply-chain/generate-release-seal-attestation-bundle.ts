import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

function computeSha256(filePath: string): string {
  const fileBuffer = fs.readFileSync(filePath);
  const hashSum = crypto.createHash("sha256");
  hashSum.update(fileBuffer);
  return hashSum.digest("hex");
}

async function main() {
  const operator = "Michael Hoch";
  const reason = "Generate attestation bundle after Phase 12 seal dry run";
  
  // 1. Discover the latest seal dry-run
  let sealDryRunId = process.env.SEAL_DRY_RUN_ID || "";
  let dryRunData: any = null;
  
  const previewsDir = "dist/formal-previews";
  if (!fs.existsSync(previewsDir)) {
    console.error("No formal previews directory found.");
    process.exit(1);
  }
  
  const dryRunFiles: { filepath: string; mtime: number }[] = [];
  
  // Scan recursively
  const subdirs = fs.readdirSync(previewsDir);
  for (const sub of subdirs) {
    const p = path.join(previewsDir, sub, "formal_release_seal_dry_run_manifest.json");
    if (fs.existsSync(p)) {
      const stat = fs.statSync(p);
      dryRunFiles.push({ filepath: p, mtime: stat.mtimeMs });
    }
  }
  
  if (dryRunFiles.length === 0) {
    console.error("No seal dry run records found.");
    process.exit(1);
  }
  
  // Sort by modification time desc
  dryRunFiles.sort((a, b) => b.mtime - a.mtime);
  
  if (sealDryRunId) {
    const found = dryRunFiles.find(f => {
      try {
        const content = JSON.parse(fs.readFileSync(f.filepath, "utf8"));
        return content.seal_dry_run_id === sealDryRunId;
      } catch {
        return false;
      }
    });
    if (found) {
      dryRunData = JSON.parse(fs.readFileSync(found.filepath, "utf8"));
    } else {
      console.error(`Specified SEAL_DRY_RUN_ID ${sealDryRunId} not found.`);
      process.exit(1);
    }
  } else {
    try {
      dryRunData = JSON.parse(fs.readFileSync(dryRunFiles[0].filepath, "utf8"));
      sealDryRunId = dryRunData.seal_dry_run_id;
    } catch (err) {
      console.error("Failed to parse latest seal dry run manifest:", err);
      process.exit(1);
    }
  }
  
  console.log(`Using Seal Dry Run: ${sealDryRunId}`);
  
  // 2. Try POSTing to backend first to synchronize DB
  let backendSuccess = false;
  try {
    const res = await fetch(`http://localhost:8000/api/v1/release/seal-dry-run/${sealDryRunId}/attestation-bundle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator, reason })
    });
    if (res.ok) {
      const data = await res.json();
      console.log(`Successfully generated attestation bundle ${data.attestation_bundle_id} via backend API.`);
      backendSuccess = true;
    } else {
      console.warn(`Backend POST returned status ${res.status}. Falling back to local generation.`);
    }
  } catch (err) {
    console.warn("Backend API not reachable. Falling back to local generation.");
  }
  
  // 3. Fallback to direct disk generation if backend was not reachable or failed
  if (!backendSuccess) {
    const formalPreviewId = dryRunData.formal_preview_id;
    const candidatePacketId = dryRunData.candidate_packet_id;
    const version = dryRunData.candidate_version;
    const headSha = dryRunData.head_sha;
    const branch = dryRunData.branch;
    const releaseTag = dryRunData.release_tag;
    const sealStatus = dryRunData.seal_status;
    
    const bundleId = `attestation-bundle-${Math.floor(Date.now() / 1000)}-${crypto.randomBytes(4).toString("hex")}`;
    const createdAt = new Date().toISOString();
    
    let attestationStatus = "ATTESTATION_BLOCKED";
    if (sealStatus === "SEAL_READY") {
      attestationStatus = "ATTESTATION_READY";
    } else if (JSON.stringify(dryRunData.formal_release_blockers || []).toLowerCase().includes("dirty")) {
      attestationStatus = "ATTESTATION_WARN";
    }
    
    const potentialFiles = [
      `dist/releases/${version}/baseline_evidence_pack.json`,
      `dist/releases/${version}/release_manifest.json`,
      `dist/releases/${version}/provenance.intoto.jsonl`,
      `dist/releases/${version}/sbom.spdx.json`,
      `dist/releases/${version}/runtime_execution_audit.json`,
      `dist/releases/${version}/tool_call_trace_summary.json`,
      `dist/releases/${version}/redaction_report.json`,
      `dist/releases/${version}/approval_gate_report.json`,
      `dist/releases/${version}/verification_report.json`,
      `dist/releases/${version}/autonomy_budget_report.json`,
      `dist/candidates/${candidatePacketId}/candidate_packet_manifest.json`,
      `dist/candidates/${candidatePacketId}/candidate_packet_summary.md`,
      `dist/formal-previews/${formalPreviewId}/formal_release_preview_manifest.json`,
      `dist/formal-previews/${formalPreviewId}/formal_release_preview_summary.md`,
      `dist/formal-previews/${formalPreviewId}/formal_release_approval_report.json`,
      `dist/formal-previews/${formalPreviewId}/formal_release_approval_report.md`,
      `dist/formal-previews/${formalPreviewId}/formal_release_seal_dry_run_manifest.json`,
      `dist/formal-previews/${formalPreviewId}/formal_release_seal_dry_run_report.md`,
      "artifacts/qa/readiness-scorecard.json",
      "artifacts/qa/localhost-8000-audit.json",
      "artifacts/qa/autonomy-budget-audit.json",
      "artifacts/qa/north-star-readiness-report.md",
      "artifacts/qa/formal-release-approval.png",
      "artifacts/qa/formal-release-preview.png",
      "artifacts/qa/candidate-release-packet.png",
      "artifacts/qa/formal-release-seal-dry-run.png"
    ];
    
    const includedArtifacts: string[] = [];
    const missingArtifacts: string[] = [];
    const artifactChecksums: Record<string, string> = {};
    
    for (const f of potentialFiles) {
      if (fs.existsSync(f)) {
        try {
          const chk = computeSha256(f);
          includedArtifacts.push(f);
          artifactChecksums[f] = chk;
        } catch {
          missingArtifacts.push(f);
        }
      } else {
        missingArtifacts.push(f);
      }
    }
    
    const bundleDir = `dist/attestations/${bundleId}`;
    const bundleManifestPath = `${bundleDir}/release_seal_attestation_bundle_manifest.json`;
    const bundleSummaryPath = `${bundleDir}/release_seal_attestation_bundle_summary.md`;
    
    const manifest = {
      attestation_bundle_id: bundleId,
      seal_dry_run_id: sealDryRunId,
      formal_preview_id: formalPreviewId,
      candidate_packet_id: candidatePacketId,
      created_at: createdAt,
      operator,
      reason,
      head_sha: headSha,
      branch,
      release_tag: releaseTag,
      seal_status: sealStatus,
      formal_release_ready: sealStatus === "SEAL_READY",
      no_mutation_guarantee: true,
      included_artifacts: includedArtifacts,
      missing_artifacts: missingArtifacts,
      artifact_checksums: artifactChecksums,
      signing_policy: "BLOCK",
      release_channel_governance: "BLOCK",
      governance_summary: {
        operator_approval: "pending"
      },
      qa_summary: {
        qa_status: "WARN",
        readiness_status: "WARN"
      },
      evidence_paths: {
        manifest: bundleManifestPath,
        summary: bundleSummaryPath
      }
    };
    
    fs.mkdirSync(bundleDir, { recursive: true });
    fs.writeFileSync(bundleManifestPath, JSON.stringify(manifest, null, 2), "utf8");
    
    const statusBadge = attestationStatus === "ATTESTATION_READY" ? "✅ READY TO SEAL" : "❌ BLOCKED";
    const includedListStr = includedArtifacts.map(p => `- \`${path.basename(p)}\` (SHA256: \`${artifactChecksums[p]}\`)`).join("\n");
    const missingListStr = missingArtifacts.map(p => `- \`${path.basename(p)}\``).join("\n");
    
    const mdContent = `# Release Seal Attestation Bundle Summary — \`${bundleId}\`

## Attestation Status: ${statusBadge}
- **Dry Run Seal Status**: \`${sealStatus}\`
- **Ready for Formal Release**: \`${manifest.formal_release_ready ? "YES" : "NO"}\`

## Metadata
- **Attestation Bundle ID**: \`${bundleId}\`
- **Seal Dry Run ID**: \`${sealDryRunId}\`
- **Formal Preview ID**: \`${formalPreviewId}\`
- **Candidate Packet ID**: \`${candidatePacketId}\`
- **Git HEAD SHA**: \`${headSha}\`
- **Git Branch**: \`${branch}\`
- **Release Tag**: \`${releaseTag}\`
- **Operator**: \`${operator}\`
- **Justification Reason**: ${reason}
- **Generated At**: \`${createdAt}\`

---

## Safety & No-Mutation Guarantees
- 🔒 **no_mutation_guarantee = true**
- ⚠️ **Zero git-tags were created or modified.**
- 🔒 **Zero artifacts were signed.**
- 🚀 **Zero packages were published or finalized.**
- 🔍 **This attestation bundle is NOT a formal release.**

---

## Included Evidence Artifacts & Checksums
${includedListStr || "- None"}

---

## Missing Artifacts
${missingListStr || "- None"}
`;
    
    fs.writeFileSync(bundleSummaryPath, mdContent, "utf8");
    console.log(`Local generation completed. Wrote manifest and summary to ${bundleDir}.`);
  }
}

main().catch(err => {
  console.error("Attestation bundle generator failed:", err);
  process.exit(1);
});
