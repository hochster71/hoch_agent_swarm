import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

// Simple CLI arguments parser
function getArgs(): Record<string, string> {
  const args: Record<string, string> = {};
  const rawArgs = process.argv.slice(2);
  for (let i = 0; i < rawArgs.length; i++) {
    if (rawArgs[i].startsWith("--")) {
      const key = rawArgs[i].slice(2);
      const val = rawArgs[i + 1];
      if (val && !val.startsWith("--")) {
        args[key] = val;
        i++;
      } else {
        args[key] = "true";
      }
    }
  }
  return args;
}

function runGit(args: string[]): string {
  try {
    return execSync(`git ${args.join(" ")}`, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

function getGlobFiles(dir: string, ext: string): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;
  const list = fs.readdirSync(dir);
  for (const item of list) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      results.push(...getGlobFiles(fullPath, ext));
    } else if (item.endsWith(ext)) {
      results.push(fullPath);
    }
  }
  return results;
}

async function main() {
  const args = getArgs();
  
  // Resolve arguments or defaults
  const version = args["version"] || JSON.parse(fs.readFileSync("package.json", "utf8")).version;
  const operator = args["operator"] || "Michael Hoch";
  const reason = args["reason"] || "Create candidate packet";
  const channel = args["channel"] || "candidate";
  const packetId = args["packet-id"] || `packet-${Date.now()}`;
  
  console.log(`Generating Candidate Release Packet: ${packetId} for version ${version} (${channel})...`);
  
  const releaseDir = `dist/releases/${version}`;
  const candidatesDir = `dist/candidates/${packetId}`;
  fs.mkdirSync(candidatesDir, { recursive: true });
  
  // Read baseline files
  const releaseManifestPath = `${releaseDir}/release_manifest.json`;
  const verificationReportPath = `${releaseDir}/verification_report.json`;
  const baselineEvidencePath = `dist/baseline_evidence_pack.json`;
  
  const releaseManifest = fs.existsSync(releaseManifestPath) ? JSON.parse(fs.readFileSync(releaseManifestPath, "utf8")) : {};
  const verificationReport = fs.existsSync(verificationReportPath) ? JSON.parse(fs.readFileSync(verificationReportPath, "utf8")) : {};
  const baselineEvidence = fs.existsSync(baselineEvidencePath) ? JSON.parse(fs.readFileSync(baselineEvidencePath, "utf8")) : {};
  
  // Collect git metadata
  const headSha = runGit(["rev-parse", "HEAD"]);
  let branch = runGit(["rev-parse", "--abbrev-ref", "HEAD"]);
  if (!branch || branch.includes("fatal")) {
    branch = "detached";
  }
  const workingTreeClean = !runGit(["status", "--porcelain"]);
  
  // Fetch governance summary from running backend if active
  let govSummary: any = {};
  try {
    const res = await fetch("http://localhost:8000/api/v1/governance/summary");
    if (res.ok) {
      govSummary = await res.json();
    }
  } catch (err) {
    console.warn("FastAPI backend is offline, compiling local fallback status.");
  }
  
  // Determine blockers
  const formalBlockers: string[] = [];
  if (!workingTreeClean && !govSummary?.tag_alignment_requests?.some((g: any) => g.status === "approved" && g.action_type === "governance_waiver")) {
    formalBlockers.push("dirty_working_tree");
  }
  const qaPassed = verificationReport?.status === "PASS";
  if (!qaPassed) {
    formalBlockers.push("qa_not_passed");
  }
  const signingPolicyStatus = verificationReport?.signing_policy?.signing_policy_status || "BLOCK";
  if (signingPolicyStatus === "BLOCK") {
    formalBlockers.push("signing_policy_not_passed");
  }
  const tagStatus = govSummary?.tag_alignment_status || "NO_RELEASE_TAG";
  if (tagStatus === "NO_RELEASE_TAG") {
    formalBlockers.push("tag_missing");
  } else if (tagStatus === "STALE_TAG") {
    formalBlockers.push("tag_stale");
  }
  
  // If we fetched the actual blockers from the backend, use those
  const formal_release_blockers = govSummary?.formal_release_blockers || formalBlockers;
  const formal_release_ready = formal_release_blockers.length === 0;
  
  // Map packet status
  let packet_status = "candidate_blocked";
  if (formal_release_ready) {
    packet_status = "candidate_ready";
  } else if (channel === "local_dev") {
    packet_status = "candidate_warn";
  }
  
  // Resolve included and missing expected artifacts
  const expectedArtifacts = [
    `dist/baseline_evidence_pack.json`,
    `${releaseDir}/release_manifest.json`,
    `${releaseDir}/provenance.intoto.jsonl`,
    `${releaseDir}/sbom.spdx.json`,
    `${releaseDir}/runtime_execution_audit.json`,
    `${releaseDir}/tool_call_trace_summary.json`,
    `${releaseDir}/redaction_report.json`,
    `${releaseDir}/approval_gate_report.json`
  ];
  
  const included_artifacts: string[] = [];
  const missing_artifacts: string[] = [];
  
  for (const art of expectedArtifacts) {
    if (fs.existsSync(art)) {
      included_artifacts.push(art);
    } else {
      missing_artifacts.push(art);
    }
  }
  
  // Add QA reports and screenshots
  const qaJsons = getGlobFiles("artifacts/qa", ".json");
  const qaPngs = getGlobFiles("artifacts/qa", ".png");
  
  for (const qf of [...qaJsons, ...qaPngs]) {
    if (fs.existsSync(qf)) {
      included_artifacts.push(qf);
    }
  }
  
  // Construct Candidate Packet Manifest
  const manifest = {
    candidate_packet_id: packetId,
    candidate_version: version,
    candidate_channel: channel,
    created_at: new Date().toISOString(),
    head_sha: headSha,
    branch: branch,
    packet_status: packet_status,
    formal_release_ready: formal_release_ready,
    formal_release_blockers: formal_release_blockers,
    included_artifacts: included_artifacts,
    missing_artifacts: missing_artifacts,
    signing_policy: signingPolicyStatus,
    release_channel_governance: channel === "formal" ? "PASS" : "WARN",
    governance_summary: govSummary,
    qa_summary: {
      status: qaPassed ? "PASS" : "WARN",
      verification_report_exists: fs.existsSync(verificationReportPath)
    },
    evidence_paths: included_artifacts,
    operator: operator,
    reason: reason
  };
  
  const manifestPath = `${candidatesDir}/candidate_packet_manifest.json`;
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf8");
  console.log(`Wrote candidate packet manifest to ${manifestPath}`);
  
  // Construct Human-Readable Summary Markdown
  const summaryMd = `# Candidate Release Packet Summary — \`${packetId}\`

## Metadata
- **Version**: ${version}
- **Channel**: ${channel}
- **Operator**: ${operator}
- **Reason**: ${reason}
- **Generated At**: ${manifest.created_at}
- **Git HEAD SHA**: \`${headSha}\`
- **Git Branch**: \`${branch}\`
- **Working Tree Clean**: ${workingTreeClean}
- **Formal Release Ready**: **${formal_release_ready ? "YES" : "NO"}**
- **Packet Status**: **\`${packet_status.toUpperCase()}\`**

---

## Formal Release Blockers Checklist
${formal_release_blockers.length === 0 
  ? "* [x] No active release blockers. All gates satisfy policy requirements." 
  : formal_release_blockers.map((b: string) => `* [ ] **BLOCKER**: ${b}`).join("\n")}

---

## Included Evidence Artifacts
${included_artifacts.length === 0
  ? "*None.*"
  : included_artifacts.map((a: string) => `- [${path.basename(a)}](file:///${path.resolve(a)})`).join("\n")}

${missing_artifacts.length > 0 
  ? `\n## Missing Expected Artifacts\n${missing_artifacts.map((a: string) => `- \`${a}\``).join("\n")}`
  : ""}
  
---
*Note: Candidate packets are review artifacts. Generating a candidate packet does NOT create, move, delete, or push git tags.*
`;
  
  const summaryPath = `${candidatesDir}/candidate_packet_summary.md`;
  fs.writeFileSync(summaryPath, summaryMd, "utf8");
  console.log(`Wrote candidate packet summary markdown to ${summaryPath}`);
}

main().catch(err => {
  console.error("Failed to generate candidate packet:", err);
  process.exit(1);
});
