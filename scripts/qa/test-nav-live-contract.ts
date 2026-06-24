import fs from "node:fs";
import { navOperationalContracts } from "./nav-contract";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";

type Result = {
  id: string;
  label: string;
  endpoint: string;
  status: "PASS" | "WARN" | "BLOCK";
  http_status?: number;
  blockers: string[];
  warnings: string[];
};

function hasLiveEnvelope(payload: any): boolean {
  return Boolean(
    payload &&
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

async function checkContract(item: typeof navOperationalContracts[number]): Promise<Result> {
  if (item.expectedFreshness === "planned") {
    return {
      id: item.id,
      label: item.label,
      endpoint: item.endpoint,
      status: "WARN",
      blockers: [],
      warnings: ["Nav item is planned; live check skipped"],
    };
  }
  try {
    const response = await fetch(`${BASE_URL}${item.endpoint}`);
    const payload = await response.json();
    const blockers: string[] = [];
    const warnings: string[] = [];
    if (!response.ok) blockers.push(`HTTP ${response.status}`);
    if (!hasLiveEnvelope(payload)) blockers.push("Missing realtime envelope");
    if (payload.freshness !== item.expectedFreshness) {
      blockers.push(`Freshness mismatch: expected ${item.expectedFreshness}, got ${payload.freshness}`);
    }
    if (Array.isArray(payload.evidence_refs) && payload.evidence_refs.length === 0) {
      warnings.push("No evidence refs returned");
    }
    return {
      id: item.id,
      label: item.label,
      endpoint: item.endpoint,
      status: blockers.length ? "BLOCK" : warnings.length ? "WARN" : "PASS",
      http_status: response.status,
      blockers,
      warnings,
    };
  } catch (error: any) {
    return {
      id: item.id,
      label: item.label,
      endpoint: item.endpoint,
      status: "BLOCK",
      blockers: [error.message],
      warnings: [],
    };
  }
}

async function main() {
  const results = await Promise.all(navOperationalContracts.map(checkContract));
  const blockers = results.flatMap((item) =>
    item.blockers.map((blocker) => `${item.label}: ${blocker}`)
  );
  const warnings = results.flatMap((item) =>
    item.warnings.map((warning) => `${item.label}: ${warning}`)
  );
  const report = {
    generated_at: new Date().toISOString(),
    base_url: BASE_URL,
    status: blockers.length === 0 ? "PASS" : "BLOCK",
    results,
    blockers,
    warnings,
  };
  fs.mkdirSync("artifacts/qa", { recursive: true });
  fs.writeFileSync(
    "artifacts/qa/nav-live-contract-report.json",
    JSON.stringify(report, null, 2)
  );
  console.log(JSON.stringify(report, null, 2));
  if (blockers.length) process.exit(1);
}

main();
