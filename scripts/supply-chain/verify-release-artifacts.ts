import crypto from "node:crypto";
import fs from "node:fs";

const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));
const VERSION = packageJson.version;
const RELEASE_DIR = `dist/releases/${VERSION}`;
const MANIFEST = `${RELEASE_DIR}/release_manifest.json`;

function sha256(path: string): string {
  return crypto.createHash("sha256").update(fs.readFileSync(path)).digest("hex");
}

const blockers: string[] = [];
const warnings: string[] = [];

if (!fs.existsSync(MANIFEST)) {
  throw new Error(`Missing release manifest: ${MANIFEST}`);
}

const manifest = JSON.parse(fs.readFileSync(MANIFEST, "utf8"));

for (const artifact of manifest.artifacts ?? []) {
  if (!fs.existsSync(artifact.path)) {
    blockers.push(`Missing artifact: ${artifact.path}`);
    continue;
  }
  const actual = sha256(artifact.path);
  if (actual !== artifact.sha256) {
    blockers.push(`Hash mismatch: ${artifact.path}`);
  }
}

for (const required of [
  "baseline_evidence_pack.json",
  "baseline_evidence_pack.json.sha256",
  "release_manifest.json",
  "provenance.intoto.jsonl",
  "sbom.spdx.json",
  "runtime_execution_audit.json",
  "tool_call_trace_summary.json",
  "redaction_report.json",
  "approval_gate_report.json",
]) {
  if (!fs.existsSync(`${RELEASE_DIR}/${required}`)) {
    blockers.push(`Required release artifact missing: ${required}`);
  }
}

const runtimeAuditPath = `${RELEASE_DIR}/runtime_execution_audit.json`;
if (fs.existsSync(runtimeAuditPath)) {
  const runtimeAudit = JSON.parse(fs.readFileSync(runtimeAuditPath, "utf8"));
  if (runtimeAudit.status !== "PASS") {
    blockers.push(`Runtime execution audit did not PASS: ${JSON.stringify(runtimeAudit.blockers)}`);
  }
}

if (manifest.hochster?.cluster_jobs_blocked > 0) {
  blockers.push("HOCHSTER cluster has blocked jobs");
}
if (manifest.hochster?.missing_trace_ids?.length > 0) {
  blockers.push("HOCHSTER jobs missing trace IDs");
}
if (manifest.hochster?.missing_evidence_refs?.length > 0) {
  blockers.push("HOCHSTER jobs missing evidence refs");
}
if (!manifest.integrity?.signed) {
  warnings.push("Release artifacts are not cryptographically signed yet");
}

const report = {
  generated_at: new Date().toISOString(),
  release: VERSION,
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
  warnings,
};

fs.writeFileSync(
  `${RELEASE_DIR}/verification_report.json`,
  JSON.stringify(report, null, 2)
);

console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
