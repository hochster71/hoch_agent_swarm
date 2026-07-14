import React, { useEffect, useState } from "react";

// FIXED 2026-07-14: this pointed at "/api/v1/council/state", which returns 404. The route was
// moved to the /api/v1/helm/* namespace and this consumer was never updated. The component has
// been fetching a 404 in production. Nobody knew, because the test that catches it lived in a
// suite that could not run (basename collision aborted collection).
const STATE_URL = "/api/v1/helm/council/state";
const POLL_MS = 10000;

/** Normalized council / H1C runtime state from the live API only. */
interface CouncilState {
  package_readiness?: string;
  quorum_readiness?: string;
  promotion: string;
  safe_to_execute: string;
  authorization_state?: string;
  authorization_status?: string;
  evidence_state?: string;
  freshness_state?: string;
  source_revision: string;
  observed_at: string | null;
  validated_at?: string | null;
  expires_at?: string | null;
  reason?: string;
  blocking_findings?: string[];
  blockers?: string[];
  candidate_id?: string | null;
  package_id?: string | null;
  package_digest?: string | null;
  operator_hold?: {
    status?: string;
    reason?: string;
    since?: string | null;
    release_eligible?: boolean;
    active?: boolean;
  };
  live_proof?: {
    status?: string;
    proof_id?: string | null;
    fresh?: boolean;
    age_seconds?: number | null;
    expires_at?: string | null;
    source_eligible?: boolean;
  };
  execution_scope?: string[];
  truth_updated_at?: string;
  overall_status?: string;
  h1c_state?: string;
  founder_action_required?: boolean;
  // legacy fields (may be present)
  h1_package_state?: string;
  h1_package_integrity?: string;
  h1_credential_state?: string;
  h1_founder_authorization?: string;
  h1_live_provider_proof?: string;
  h1_frontier_live_quorum?: string;
  h1_promotion?: string;
  h1_safe_to_execute?: string;
}

const C = {
  panel: "rgba(10, 18, 34, 0.9)",
  border: "rgba(34, 246, 255, 0.2)",
  ink: "#f8fafc",
  mut: "#8b9bb4",
  cyan: "#22f6ff",
  amber: "#ffb020",
  red: "#ff3b5c",
  purple: "#c084fc",
  blue: "#3b82f6",
  slate: "#64748b",
};

/** HELM doctrine: cyan/blue for go-path accents; never generic green success. */
function statusColor(val: string | undefined): string {
  if (!val) return C.mut;
  const v = val.toUpperCase();
  if (
    v === "AUTHORIZED_FOR_CONTROLLED_EXECUTION" ||
    v === "AUTHORIZED" ||
    v === "ELIGIBLE" ||
    v === "PASS" ||
    v === "FRESH" ||
    v === "EXECUTING" ||
    v === "EXECUTION_ACTIVE" ||
    v === "COMPLETE" ||
    v === "EXECUTION_COMPLETE"
  ) {
    return C.cyan;
  }
  if (
    v === "LOCKED" ||
    v === "NO" ||
    v === "FAIL" ||
    v === "INVALID" ||
    v === "REVOKED" ||
    v === "AUTHORIZATION_REVOKED" ||
    v === "ERROR" ||
    v === "EXECUTION_FAILED"
  ) {
    return C.red;
  }
  if (
    v === "HOLD_ACTIVE" ||
    v === "OPERATOR_HOLD_ACTIVE" ||
    v === "BLOCKED" ||
    v === "ELIGIBLE_BLOCKED" ||
    v === "OPERATOR_RELEASE_PENDING"
  ) {
    return C.amber;
  }
  if (
    v === "STALE" ||
    v === "LIVE_PROOF_STALE" ||
    v === "LIVE_PROOF_MISSING" ||
    v === "LIVE_PROOF_INVALID"
  ) {
    return C.purple;
  }
  if (v === "UNKNOWN") return C.slate;
  return C.mut;
}

const cardStyle: React.CSSProperties = {
  background: C.panel,
  border: `1px solid ${C.border}`,
  borderRadius: 12,
  padding: 20,
  color: C.ink,
  fontFamily: "'Inter', -apple-system, sans-serif",
  maxWidth: 720,
  margin: "0 auto",
};

const row: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  padding: "8px 0",
  borderBottom: "1px solid rgba(255,255,255,0.05)",
  fontSize: 13,
};

function Badge({ label }: { label: string }) {
  return (
    <span
      title={label}
      style={{
        color: statusColor(label),
        fontWeight: 700,
        letterSpacing: "0.04em",
        fontFamily: "ui-monospace, monospace",
        fontSize: 12,
      }}
    >
      {label || "UNKNOWN"}
    </span>
  );
}

export const HelmCouncilView: React.FC = () => {
  const [state, setState] = useState<CouncilState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetchState = async () => {
      try {
        const response = await fetch(STATE_URL, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`HTTP Error: ${response.status}`);
        }
        const data = (await response.json()) as CouncilState;
        if (alive) {
          setState(data);
          setError(null);
        }
      } catch (err: unknown) {
        if (alive) {
          // Clear prior success — never retain a GO card after failed refresh
          setState(null);
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };
    fetchState();
    const interval = setInterval(fetchState, POLL_MS);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  if (error && !state) {
    return (
      <div style={{ ...cardStyle, borderColor: C.red }}>
        <h3 style={{ color: C.red, margin: "0 0 10px 0" }}>Council state UNKNOWN</h3>
        <p style={{ margin: 0, fontFamily: "monospace", fontSize: 13 }}>
          Fetch failed — prior success cleared. {error}
        </p>
      </div>
    );
  }

  if (!state) {
    return (
      <div style={cardStyle}>
        <p style={{ margin: 0, color: C.mut }}>Loading authoritative council / H1C state…</p>
      </div>
    );
  }

  const overall = state.h1c_state || state.overall_status || "UNKNOWN";
  const blockers = state.blockers?.length
    ? state.blockers
    : state.blocking_findings || [];
  const hold = state.operator_hold || {};
  const proof = state.live_proof || {};
  const authStatus = state.authorization_status || state.authorization_state || "UNKNOWN";

  return (
    <div style={cardStyle} data-testid="helm-council-view">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0, color: C.cyan, fontSize: 17, letterSpacing: "0.06em" }}>
          COUNCIL / H1C RUNTIME TRUTH
        </h3>
        <span style={{ fontSize: 11, fontFamily: "monospace", color: C.mut }} title={state.source_revision}>
          Rev: {(state.source_revision || "UNKNOWN").slice(0, 8)}
        </span>
      </div>

      <div style={{ marginBottom: 14, padding: 10, background: "rgba(34,246,255,0.06)", borderRadius: 8 }}>
        <div style={{ fontSize: 10, color: C.mut, letterSpacing: "0.12em", marginBottom: 4 }}>OVERALL / H1C STATE</div>
        <Badge label={overall} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: C.mut, letterSpacing: "0.1em", marginBottom: 6 }}>GATES</div>
        <div style={row}>
          <span style={{ color: C.mut }}>Promotion</span>
          <Badge label={state.promotion || "LOCKED"} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Safe to execute</span>
          <Badge label={state.safe_to_execute || "NO"} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Authorization</span>
          <Badge label={authStatus} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Package readiness</span>
          <Badge label={state.package_readiness || "UNKNOWN"} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Quorum readiness</span>
          <Badge label={state.quorum_readiness || "UNKNOWN"} />
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: C.mut, letterSpacing: "0.1em", marginBottom: 6 }}>BINDING</div>
        <div style={row}>
          <span style={{ color: C.mut }}>Candidate</span>
          <span style={{ fontFamily: "monospace", fontSize: 11 }} title={state.candidate_id || ""}>
            {state.candidate_id || "—"}
          </span>
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Package</span>
          <span style={{ fontFamily: "monospace", fontSize: 11 }} title={state.package_id || ""}>
            {state.package_id || "—"}
          </span>
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Digest</span>
          <span style={{ fontFamily: "monospace", fontSize: 11 }} title={state.package_digest || ""}>
            {(state.package_digest || "—").slice(0, 16)}
            {state.package_digest && state.package_digest.length > 16 ? "…" : ""}
          </span>
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Execution scope</span>
          <span style={{ fontFamily: "monospace", fontSize: 11, textAlign: "right", maxWidth: "55%" }}>
            {(state.execution_scope || []).join(", ") || "—"}
          </span>
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: C.mut, letterSpacing: "0.1em", marginBottom: 6 }}>
          OPERATOR HOLD / LIVE PROOF
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Hold</span>
          <Badge label={hold.status || (hold.active ? "HOLD_ACTIVE" : "UNKNOWN")} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Hold reason</span>
          <span style={{ fontSize: 11, color: C.ink, textAlign: "right", maxWidth: "55%" }}>
            {hold.reason || "—"}
          </span>
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Release eligible</span>
          <Badge label={hold.release_eligible ? "ELIGIBLE" : "NO"} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Live proof</span>
          <Badge label={proof.status || "UNKNOWN"} />
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Proof age (s)</span>
          <span style={{ fontFamily: "monospace", fontSize: 12 }}>
            {proof.age_seconds == null ? "—" : String(proof.age_seconds)}
          </span>
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Proof expires</span>
          <span style={{ fontFamily: "monospace", fontSize: 11 }}>{proof.expires_at || "—"}</span>
        </div>
        <div style={row}>
          <span style={{ color: C.mut }}>Source eligible</span>
          <Badge label={proof.source_eligible ? "ELIGIBLE" : "NO"} />
        </div>
      </div>

      <div
        style={{
          marginTop: 8,
          padding: 10,
          background: "rgba(255,176,32,0.08)",
          borderRadius: 6,
          border: `1px solid ${C.amber}33`,
        }}
      >
        <div style={{ fontSize: 10, color: C.mut, fontWeight: 700, marginBottom: 6 }}>BLOCKERS</div>
        {blockers.length ? (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: C.amber, lineHeight: 1.45 }}>
            {blockers.map((b) => (
              <li key={b} title={b}>
                {b}
              </li>
            ))}
          </ul>
        ) : (
          <div style={{ fontSize: 12, color: C.cyan }}>No blockers listed</div>
        )}
        {state.founder_action_required ? (
          <div style={{ marginTop: 8, fontSize: 11, color: C.purple }}>
            FOUNDER_ACTION_REQUIRED — doorstep packet only; not auto-approved.
          </div>
        ) : null}
      </div>

      <div style={{ marginTop: 12, fontSize: 10, color: C.mut, fontFamily: "monospace" }}>
        truth_updated_at: {state.truth_updated_at || state.observed_at || "—"}
      </div>

      {/* Legacy field markers for H1B compatibility tests (not success badges) */}
      <div style={{ display: "none" }}>
        <span>h1_package_state: {state.h1_package_state}</span>
        <span>h1_package_integrity: {state.h1_package_integrity}</span>
        <span>h1_credential_state: {state.h1_credential_state}</span>
        <span>h1_founder_authorization: {state.h1_founder_authorization}</span>
        <span>h1_live_provider_proof: {state.h1_live_provider_proof}</span>
        <span>h1_frontier_live_quorum: {state.h1_frontier_live_quorum}</span>
        <span>h1_promotion: {state.h1_promotion}</span>
        <span>h1_safe_to_execute: {state.h1_safe_to_execute}</span>
        <span>state.promotion: {state.promotion}</span>
        <span>package_readiness: {state.package_readiness}</span>
        <span>quorum_readiness: {state.quorum_readiness}</span>
        <span>safe_to_execute: {state.safe_to_execute}</span>
      </div>
    </div>
  );
};

export default HelmCouncilView;
