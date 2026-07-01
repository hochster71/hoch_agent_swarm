import { RealtimeUiDatum } from "./hochsterTypes";

export function wrapRealtime<T>(
  value: T,
  source: "live" | "cache" | "simulation" | "manual" | "unknown" = "unknown",
  sourceId: string = "unknown-service",
  ttlMs: number = 10000,
  correlationId?: string,
  evidenceRefs: string[] = []
): RealtimeUiDatum<T> {
  const nowStr = new Date().toISOString();
  return {
    value,
    source,
    source_id: sourceId,
    observed_at: nowStr,
    received_at: nowStr,
    ttl_ms: ttlMs,
    freshness: "live",
    correlation_id: correlationId,
    evidence_refs: evidenceRefs
  };
}

export function evaluateFreshness(params: {
  received_at: string;
  ttl_ms: number;
  source: "live" | "cache" | "simulation" | "manual" | "unknown";
  error?: boolean;
}): "live" | "stale" | "expired" | "error" {
  if (params.error) return "error";
  if (params.source === "simulation" || params.source === "manual") return "stale";
  const ageMs = Date.now() - new Date(params.received_at).getTime();
  if (ageMs <= params.ttl_ms) return "live";
  if (ageMs <= params.ttl_ms * 3) return "stale";
  return "expired";
}

