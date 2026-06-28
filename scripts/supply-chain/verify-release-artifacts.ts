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
const isFormalRelease = process.env.GITHUB_ACTIONS === "true" || process.env.FORMAL_RELEASE === "true";
const signatureStatus = manifest.signature_status || "unsigned";
const signingPolicyStatus = manifest.signing_policy_status || "WARN";
const releaseFinalizationStatus = manifest.release_finalization_status || "local_dev_pass";

if (signatureStatus === "signed" || signatureStatus === "waived") {
  // PASS
} else {
  if (isFormalRelease) {
    blockers.push("Release artifacts are unsigned or partially signed, blocking formal release finalization");
  } else {
    warnings.push("Release artifacts are unsigned (Allowed in local dev mode)");
  }
}

// Compute formal release blockers
const formal_release_blockers: string[] = [];
if (!manifest.working_tree_clean) formal_release_blockers.push("dirty_working_tree");
if (manifest.decision?.status !== "PASS") formal_release_blockers.push("qa_not_passed");
if (signingPolicyStatus === "BLOCK") formal_release_blockers.push("signing_policy_not_passed");
if (manifest.release_tag_status === "NO_RELEASE_TAG") formal_release_blockers.push("tag_missing");
if (manifest.release_tag_status === "STALE_TAG") formal_release_blockers.push("tag_stale");

const isFormalChannel = (manifest.release_channel === "formal");
const operatorApprovalMissing = isFormalChannel && !manifest.release_channel_decision_id;
if (operatorApprovalMissing) {
  formal_release_blockers.push("operator_approval_missing");
}

// Block if formal release is blocked
if (isFormalRelease && manifest.formal_release_finalization_status === "formal_release_blocked") {
  blockers.push(`Formal release finalization is blocked: ${formal_release_blockers.join(", ")}`);
}

const release_channel_policy_decision = 
  manifest.formal_release_finalization_status === "formal_release_blocked" 
    ? "BLOCK" 
    : (manifest.release_channel === "local_dev" && formal_release_blockers.length > 0 ? "WARN" : "PASS");

const report = {
  generated_at: new Date().toISOString(),
  release: VERSION,
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
  warnings,
  signing_policy: {
    decision: blockers.length === 0 ? (signatureStatus === "signed" ? "PASS" : (signatureStatus === "waived" ? "PASS" : "WARN")) : "BLOCK",
    cosign_enabled: !!process.env.ENABLE_COSIGN_SIGNING,
    enable_cosign_signing_set: process.env.ENABLE_COSIGN_SIGNING !== undefined,
    is_formal_release: isFormalRelease,
    signing_policy_status: signingPolicyStatus,
    signature_status: signatureStatus,
    release_finalization_status: releaseFinalizationStatus
  },
  release_channel_policy_decision,
  release_channel: manifest.release_channel || "local_dev",
  tag_points_at_head: !!manifest.release_tag_points_at_head,
  tag_status: manifest.release_tag_status || "NO_RELEASE_TAG",
  formal_release_blockers,
  allowed_release_actions: [
    "continue_local_dev",
    "create_candidate_release",
    "request_formal_release_approval",
    "request_tag_alignment_approval"
  ],
  operator_approval_required: isFormalChannel || isFormalRelease
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
