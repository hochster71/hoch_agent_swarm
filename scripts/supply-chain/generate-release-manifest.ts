import crypto from "node:crypto";
import fs from "node:fs";
import { execSync } from "node:child_process";

const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));
const VERSION = packageJson.version;
const RELEASE_DIR = `dist/releases/${VERSION}`;

function run(command: string): string {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "unknown";
  }
}

function sha256(path: string): string {
  const buffer = fs.readFileSync(path);
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

function readJson(path: string, fallback: any) {
  if (!fs.existsSync(path)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function copyIfExists(source: string, target: string) {
  if (fs.existsSync(source)) {
    fs.copyFileSync(source, target);
  }
}

async function fetchAndSave(url: string, dest: string) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();
    fs.writeFileSync(dest, JSON.stringify(data, null, 2), "utf8");
    console.log(`Fetched and saved ${dest}`);
  } catch (err) {
    console.error(`Failed to fetch ${url}: ${(err as Error).message}`);
  }
}

async function main() {
  fs.mkdirSync(RELEASE_DIR, { recursive: true });
  copyIfExists(
    "dist/baseline_evidence_pack.json",
    `${RELEASE_DIR}/baseline_evidence_pack.json`
  );
  copyIfExists(
    "dist/baseline_evidence_pack.json.sha256",
    `${RELEASE_DIR}/baseline_evidence_pack.json.sha256`
  );

  // Fetch the new v0.1.3 runtime execution audit reports from local server
  const BASE_URL = "http://localhost:8000";
  await fetchAndSave(`${BASE_URL}/api/v1/audit/runtime/execution`, `${RELEASE_DIR}/runtime_execution_audit.json`);
  await fetchAndSave(`${BASE_URL}/api/v1/audit/runtime/tool-calls`, `${RELEASE_DIR}/tool_call_trace_summary.json`);
  await fetchAndSave(`${BASE_URL}/api/v1/audit/runtime/redactions`, `${RELEASE_DIR}/redaction_report.json`);
  await fetchAndSave(`${BASE_URL}/api/v1/audit/runtime/approvals`, `${RELEASE_DIR}/approval_gate_report.json`);
  await fetchAndSave(`${BASE_URL}/api/v1/readiness/budget-report`, `${RELEASE_DIR}/autonomy_budget_report.json`);

  // Fetch signing policy
  let signingPolicyData: any = {
    current_release: {
      signature_status: "unsigned",
      signing_policy_status: "WARN",
      release_finalization_status: "local_dev_pass",
      signing_waiver_status: "none",
      signing_waiver_decision_id: null
    }
  };
  try {
    const res = await fetch(`${BASE_URL}/api/v1/release/signing-policy`);
    if (res.ok) {
      signingPolicyData = await res.json();
    }
  } catch (err) {
    console.warn("Could not fetch signing policy from backend:", (err as Error).message);
  }

  const dockerDigests = readJson("artifacts/baseline/docker-image-digests.json", {
    records: [],
    warnings: ["docker digest report missing"],
  });

  const evidence = readJson(`${RELEASE_DIR}/baseline_evidence_pack.json`, {});
  const runtimeAudit = readJson(`${RELEASE_DIR}/runtime_execution_audit.json`, {});

  const blockers: string[] = [];
  const warnings: string[] = [];

  if (!fs.existsSync(`${RELEASE_DIR}/baseline_evidence_pack.json`)) {
    blockers.push("baseline evidence pack missing");
  }
  if (!fs.existsSync(`${RELEASE_DIR}/baseline_evidence_pack.json.sha256`)) {
    blockers.push("baseline evidence checksum missing");
  }
  if (!fs.existsSync(`${RELEASE_DIR}/provenance.intoto.jsonl`)) {
    warnings.push("provenance attestation not generated yet");
  }
  if (!fs.existsSync(`${RELEASE_DIR}/sbom.spdx.json`)) {
    warnings.push("SBOM not generated yet");
  }

  // Runtime Audit validation
  if (runtimeAudit.status !== "PASS") {
    blockers.push(`Runtime execution audit blocked: ${JSON.stringify(runtimeAudit.blockers)}`);
  }

  const candidateArtifacts = [
    "baseline_evidence_pack.json",
    "baseline_evidence_pack.json.sha256",
    "provenance.intoto.jsonl",
    "sbom.spdx.json",
    "decision_memo.md",
    "verification_report.json",
    "runtime_execution_audit.json",
    "tool_call_trace_summary.json",
    "redaction_report.json",
    "approval_gate_report.json",
    "autonomy_budget_report.json",
  ];

  const artifacts = candidateArtifacts
    .filter((name) => fs.existsSync(`${RELEASE_DIR}/${name}`))
    .map((name) => ({
      path: `${RELEASE_DIR}/${name}`,
      type:
        name.includes("evidence_pack.json") && !name.includes("sha256")
          ? "evidence_pack"
          : name.includes("sha256")
          ? "checksum"
          : name.includes("provenance")
          ? "provenance"
          : name.includes("sbom")
          ? "sbom"
          : name.includes("decision")
          ? "decision_memo"
          : name.includes("verification")
          ? "verification_report"
          : name.includes("runtime_execution")
          ? "runtime_execution_audit"
          : name.includes("tool_call")
          ? "tool_call_trace_summary"
          : name.includes("redaction")
          ? "redaction_report"
          : name.includes("autonomy_budget")
          ? "autonomy_budget_report"
          : "approval_gate_report",
      sha256: sha256(`${RELEASE_DIR}/${name}`),
    }));

  const gitCommit = run("git rev-parse HEAD");
  const gitBranch = run("git rev-parse --abbrev-ref HEAD");

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
  let signedCount = 0;
  let unsignedCount = 0;
  for (const name of expectedSigned) {
    const filePath = `${RELEASE_DIR}/${name}`;
    if (fs.existsSync(filePath)) {
      if (fs.existsSync(`${filePath}.sig`)) {
        signedCount++;
      } else {
        unsignedCount++;
      }
    }
  }

  const manifest: any = {
    signing_policy_status: signingPolicyData.current_release.signing_policy_status || "WARN",
    signing_required_for_formal_release: true,
    signing_provider: "cosign",
    signature_status: signingPolicyData.current_release.signature_status || "unsigned",
    signed_artifacts_count: signedCount,
    unsigned_artifacts_count: unsignedCount,
    signing_waiver_status: signingPolicyData.current_release.signing_waiver_status || "none",
    signing_waiver_decision_id: signingPolicyData.current_release.signing_waiver_decision_id,
    release_finalization_status: signingPolicyData.current_release.release_finalization_status || "local_dev_pass",
    release: {
      version: VERSION,
      codename: "Hochster Runtime Execution Audit",
      generated_at: new Date().toISOString(),
      generated_by: "generate-release-manifest.ts",
      git_commit_sha: gitCommit,
      git_branch: gitBranch,
      ci_provider: process.env.GITHUB_ACTIONS ? "github_actions" : "local",
      ci_run_id: process.env.GITHUB_RUN_ID,
      ci_run_url:
        process.env.GITHUB_SERVER_URL &&
        process.env.GITHUB_REPOSITORY &&
        process.env.GITHUB_RUN_ID
          ? `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`
          : undefined,
    },
    artifacts,
    docker: dockerDigests.records.map((record: any) => ({
      service: record.repository,
      image: `${record.repository}:${record.tag}`,
      digest: record.digest,
      warning:
        !record.digest || record.digest === "<none>"
          ? "missing digest"
          : undefined,
    })),
    baseline_chain: {
      previous: "v0.1.1-HOCHSTER-CLUSTER-HARDENING",
      hardening: "v0.1.2-SUPPLY-CHAIN-PROVENANCE",
      current: VERSION,
    },
    integrity: {
      signed: (signingPolicyData.current_release.signature_status === "signed"),
      signature_refs: [],
      provenance_ref: `${RELEASE_DIR}/provenance.intoto.jsonl`,
      sbom_ref: `${RELEASE_DIR}/sbom.spdx.json`,
      signing_policy_status: signingPolicyData.current_release.signing_policy_status || "WARN",
      signing_required_for_formal_release: true,
      signing_provider: "cosign",
      signature_status: signingPolicyData.current_release.signature_status || "unsigned",
      signed_artifacts_count: signedCount,
      unsigned_artifacts_count: unsignedCount,
      signing_waiver_status: signingPolicyData.current_release.signing_waiver_status || "none",
      signing_waiver_decision_id: signingPolicyData.current_release.signing_waiver_decision_id,
      release_finalization_status: signingPolicyData.current_release.release_finalization_status || "local_dev_pass"
    },
    hochster: {
      cluster_jobs_completed:
        evidence?.hochster_cluster?.jobs_completed ??
        evidence?.hochster?.solve_requests?.length ??
        0,
      cluster_jobs_blocked:
        evidence?.hochster_cluster?.jobs_blocked ?? 0,
      missing_trace_ids:
        evidence?.hochster_cluster?.missing_trace_ids ?? [],
      missing_evidence_refs:
        evidence?.hochster_cluster?.missing_evidence_refs ?? [],
    },
    decision: {
      status: blockers.length === 0 ? "PASS" : "BLOCK",
      blockers,
      warnings,
    },
  };

  fs.writeFileSync(
    `${RELEASE_DIR}/release_manifest.json`,
    JSON.stringify(manifest, null, 2)
  );

  console.log(JSON.stringify(manifest, null, 2));

  if (manifest.decision.status === "BLOCK") {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
