import { RealtimeUiDatum } from "./realtimeTypes";

export function evaluateFreshness(params: {
  received_at: string;
  ttl_ms: number;
  source: "live" | "cache" | "simulation" | "manual" | "unknown";
  error?: boolean;
}): "live" | "stale" | "expired" | "error" {
  if (params.error) return "error";
  if (params.source === "simulation") return "stale";
  if (params.source === "manual") return "stale";
  if (params.source === "unknown") return "error";
  const ageMs = Date.now() - new Date(params.received_at).getTime();
  if (ageMs <= params.ttl_ms) return "live";
  if (ageMs <= params.ttl_ms * 3) return "stale";
  return "expired";
}

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
    freshness: evaluateFreshness({ received_at: nowStr, ttl_ms: ttlMs, source }),
    correlation_id: correlationId,
    evidence_refs: evidenceRefs
  };
}

export function assertLiveDataAllowed(params: {
  source: "live" | "cache" | "simulation" | "manual" | "unknown";
  component: string;
}) {
  const allowSimulated =
    typeof import.meta !== "undefined" && import.meta.env
      ? import.meta.env.VITE_ALLOW_SIMULATED_DATA === "true"
      : false;
  if (!allowSimulated && params.source === "simulation") {
    throw new Error(
      `Simulated data blocked in RT baseline mode: ${params.component}`
    );
  }
}

