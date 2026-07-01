export type RealtimeUiDatum<T> = {
  value: T;
  source: "live" | "cache" | "simulation" | "manual" | "unknown";
  source_id: string;
  observed_at: string;
  received_at: string;
  ttl_ms: number;
  freshness: "live" | "stale" | "expired" | "error";
  correlation_id?: string;
  evidence_refs: string[];
};
