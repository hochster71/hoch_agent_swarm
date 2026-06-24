import crypto from "node:crypto";
import fs from "node:fs";
import { execSync } from "node:child_process";

const VERSION = "v0.1.2-SUPPLY-CHAIN-PROVENANCE";
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

fs.mkdirSync(RELEASE_DIR, { recursive: true });
copyIfExists(
  "dist/baseline_evidence_pack.json",
  `${RELEASE_DIR}/baseline_evidence_pack.json`
);
copyIfExists(
  "dist/baseline_evidence_pack.json.sha256",
  `${RELEASE_DIR}/baseline_evidence_pack.json.sha256`
);

const dockerDigests = readJson("artifacts/baseline/docker-image-digests.json", {
  records: [],
  warnings: ["docker digest report missing"],
});

const evidence = readJson(`${RELEASE_DIR}/baseline_evidence_pack.json`, {});

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

const candidateArtifacts = [
  "baseline_evidence_pack.json",
  "baseline_evidence_pack.json.sha256",
  "provenance.intoto.jsonl",
  "sbom.spdx.json",
  "decision_memo.md",
  "verification_report.json",
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
        : "verification_report",
    sha256: sha256(`${RELEASE_DIR}/${name}`),
  }));

const gitCommit = run("git rev-parse HEAD");
const gitBranch = run("git rev-parse --abbrev-ref HEAD");

const manifest = {
  release: {
    version: VERSION,
    codename: "Supply Chain Provenance",
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
    previous: "v0.1.0-RT-LOCK",
    hardening: "v0.1.1-HOCHSTER-CLUSTER-HARDENING",
    current: VERSION,
  },
  integrity: {
    signed: false,
    signature_refs: [],
    provenance_ref: `${RELEASE_DIR}/provenance.intoto.jsonl`,
    sbom_ref: `${RELEASE_DIR}/sbom.spdx.json`,
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
