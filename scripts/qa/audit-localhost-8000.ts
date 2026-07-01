import fs from "node:fs";
import crypto from "node:crypto";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";
const OUT_DIR = "artifacts/qa";
const STARTED_AT = new Date().toISOString();

type EndpointCheck = {
  name: string;
  path: string;
  required: boolean;
  status: "PASS" | "WARN" | "BLOCK";
  http_status?: number;
  latency_ms?: number;
  blockers: string[];
  warnings: string[];
  payload_summary?: unknown;
};

const endpoints = [
  { name: "health", path: "/health", required: true },
  { name: "baseline_lock", path: "/api/v1/hochster/baseline/lock", required: true },
  { name: "hochster_cluster_jobs", path: "/api/v1/hochster/cluster/jobs", required: true },
  { name: "database_status", path: "/api/v1/system/database/status", required: true },
  { name: "runtime_docker_health", path: "/api/v1/runtime/docker-health", required: false },
  { name: "audit_events", path: "/api/v1/audit/events", required: true },
  { name: "policy_status", path: "/api/v1/policy/status", required: true },
];

function sha256(value: string) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function hasRealtimeEnvelope(payload: any): boolean {
  return Boolean(
    payload &&
      "data" in payload &&
      "source" in payload &&
      "source_id" in payload &&
      "observed_at" in payload &&
      "received_at" in payload &&
      "ttl_ms" in payload &&
      "freshness" in payload &&
      "correlation_id" in payload &&
      "evidence_refs" in payload
  );
}

function summarizePayload(payload: any) {
  if (!payload || typeof payload !== "object") return payload;
  return {
    keys: Object.keys(payload),
    source: payload.source,
    source_id: payload.source_id,
    freshness: payload.freshness,
    correlation_id: payload.correlation_id,
    evidence_ref_count: Array.isArray(payload.evidence_refs)
      ? payload.evidence_refs.length
      : undefined,
    decision: payload.data?.decision ?? payload.decision,
    summary: payload.data?.summary ?? payload.summary,
  };
}

function validateEndpoint(name: string, path: string, required: boolean, payload: any): {
  status: "PASS" | "WARN" | "BLOCK";
  blockers: string[];
  warnings: string[];
} {
  const blockers: string[] = [];
  const warnings: string[] = [];
  if (required && !hasRealtimeEnvelope(payload)) {
    blockers.push("Missing realtime envelope fields");
  }
  if (payload?.freshness && payload.freshness !== "live") {
    blockers.push(`Freshness is not live: ${payload.freshness}`);
  }
  if (Array.isArray(payload?.evidence_refs) && payload.evidence_refs.length === 0) {
    blockers.push("Missing evidence_refs");
  }
  if (name === "baseline_lock") {
    const decision = payload?.data?.decision?.status ?? payload?.decision?.status;
    if (decision !== "PASS") blockers.push(`Baseline lock decision is not PASS: ${decision}`);
  }
  if (name === "hochster_cluster_jobs") {
    const summary = payload?.data?.summary;
    if (!summary) {
      blockers.push("Missing HOCHSTER cluster job summary");
    } else {
      if (summary.jobs_completed < 9) blockers.push(`HOCHSTER jobs incomplete: ${summary.jobs_completed}/9`);
      if (summary.jobs_blocked > 0) blockers.push(`HOCHSTER jobs blocked: ${summary.jobs_blocked}`);
      if (summary.missing_trace_ids?.length > 0) blockers.push("HOCHSTER jobs missing trace IDs");
      if (summary.missing_evidence_refs?.length > 0) blockers.push("HOCHSTER jobs missing evidence refs");
    }
  }
  if (name === "database_status") {
    const data = payload?.data;
    if (data?.engine === "sqlite" && data?.sqlite_wal_enabled !== true) {
      blockers.push("SQLite WAL is not enabled");
    }
    if ((data?.busy_timeout_ms ?? 0) < 30000) {
      warnings.push("SQLite busy_timeout_ms below 30000");
    }
    if ((data?.database_locked_events ?? 0) > 0) {
      blockers.push(`Database locked events detected: ${data.database_locked_events}`);
    }
  }
  return {
    status: blockers.length > 0 ? "BLOCK" : warnings.length > 0 ? "WARN" : "PASS",
    blockers,
    warnings,
  };
}

async function checkEndpoint(endpoint: typeof endpoints[number]): Promise<EndpointCheck> {
  const url = `${BASE_URL}${endpoint.path}`;
  const started = Date.now();
  try {
    const response = await fetch(url);
    const latency = Date.now() - started;
    const text = await response.text();
    let payload: any = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = { raw: text.slice(0, 500) };
    }
    const validation = validateEndpoint(
      endpoint.name,
      endpoint.path,
      endpoint.required,
      payload
    );
    if (!response.ok) {
      validation.blockers.push(`HTTP status ${response.status}`);
      validation.status = "BLOCK";
    }
    return {
      name: endpoint.name,
      path: endpoint.path,
      required: endpoint.required,
      status: validation.status,
      http_status: response.status,
      latency_ms: latency,
      blockers: validation.blockers,
      warnings: validation.warnings,
      payload_summary: summarizePayload(payload),
    };
  } catch (error: any) {
    return {
      name: endpoint.name,
      path: endpoint.path,
      required: endpoint.required,
      status: endpoint.required ? "BLOCK" : "WARN",
      blockers: endpoint.required ? [`Request failed: ${error.message}`] : [],
      warnings: endpoint.required ? [] : [`Optional endpoint unavailable: ${error.message}`],
    };
  }
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const checks = await Promise.all(endpoints.map(checkEndpoint));
  const blockers = checks.flatMap((check) =>
    check.blockers.map((blocker) => `${check.name}: ${blocker}`)
  );
  const warnings = checks.flatMap((check) =>
    check.warnings.map((warning) => `${check.name}: ${warning}`)
  );
  const report = {
    report_id: `qa_localhost_8000_${Date.now()}`,
    base_url: BASE_URL,
    started_at: STARTED_AT,
    completed_at: new Date().toISOString(),
    status: blockers.length === 0 ? "PASS" : "BLOCK",
    checks,
    blockers,
    warnings,
  };
  const outputPath = `${OUT_DIR}/localhost-8000-audit.json`;
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  const hash = sha256(JSON.stringify(report));
  fs.writeFileSync(`${outputPath}.sha256`, `${hash}  ${outputPath}\n`);
  console.log(JSON.stringify(report, null, 2));
  if (report.status === "BLOCK") process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
