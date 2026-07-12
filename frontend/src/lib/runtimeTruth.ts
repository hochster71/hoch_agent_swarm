/**
 * REQ-GOV-005 — runtime truth rendering contract (frontend).
 *
 * The backend now emits, for every telemetry field:
 *   { value, state, source, confidence, source_updated_at, age_seconds, timestamp_status }
 * where `value` is NULL and `state` is MISSING/UNKNOWN when the source is unavailable.
 *
 * The UI must render UNKNOWN. It must NEVER substitute a success fallback -- no
 * `?? 100`, no `|| "HEALTHY"`, no "0s ago" for an absent timestamp.
 */

export type TruthState = "OK" | "UNKNOWN" | "MISSING" | "STALE" | "ERROR" | "UNVERIFIED";

export interface Truth<T = unknown> {
  value: T | null;
  state: TruthState;
  source: string;
  confidence: "HIGH" | "LOW" | "NONE";
  source_updated_at: string | null;
  age_seconds: number | null;
  timestamp_status: "OK" | "MISSING" | "ERROR";
  reason?: string;
}

/** A value may be shown as good ONLY when it is OK. Everything else is not success. */
export function isSuccess(t?: Truth | null): boolean {
  return !!t && t.state === "OK" && t.value !== null && t.value !== undefined;
}

/** Render text. Absence renders as its truth state -- never as a number or a success word. */
export function renderTruth(t?: Truth | null, unit = ""): string {
  if (!t) return "UNKNOWN";
  if (t.value === null || t.value === undefined) return t.state; // MISSING / UNKNOWN / ERROR
  if (t.state === "STALE") return `${t.value}${unit} (STALE)`;
  if (t.state === "UNVERIFIED") return `${t.value}${unit} (UNVERIFIED)`;
  return `${t.value}${unit}`;
}

/** Freshness text. A missing timestamp is NEVER "0s ago". */
export function renderFreshness(t?: Truth | null): string {
  if (!t || t.age_seconds === null || t.age_seconds === undefined) return "AGE UNKNOWN";
  if (t.timestamp_status !== "OK") return "AGE UNKNOWN";
  const s = t.age_seconds;
  if (s < 60) return `${Math.round(s)}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}

/** no-fake-green: color is a function of the truth state, never hardcoded. */
export function truthColor(t?: Truth | null): string {
  if (!t) return "#8b9bb4";
  switch (t.state) {
    case "OK": return "#10b981";
    case "STALE":
    case "UNVERIFIED": return "#f59e0b";
    case "ERROR": return "#ef4444";
    case "MISSING":
    case "UNKNOWN":
    default: return "#8b9bb4"; // grey: we do not know. NOT green.
  }
}
