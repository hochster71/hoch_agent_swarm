import React, { useEffect, useState } from "react";

/**
 * S2 — Factory-aware Overview tab for the canonical control plane.
 *
 * Reads the SINGLE reconciled status feed (GET /api/v1/control-plane/status, added in S1),
 * so this panel reports identical numbers to the :8765 command center. No local computation,
 * no mock fallback that could read as green — if the feed is unreachable it says so.
 *
 * Self-contained on purpose (only React + inline styles) so it cannot break the existing
 * build until it is explicitly mounted from main.tsx.
 */

const STATUS_URL = "/api/v1/control-plane/status";
const POLL_MS = 15000;

type AnyObj = Record<string, any>;

const C = {
  bg: "#05070d",
  panel: "rgba(10,18,34,0.86)",
  border: "rgba(34,246,255,0.26)",
  ink: "#f8fafc",
  mut: "#8b9bb4",
  cyan: "#22f6ff",
  green: "#39ff88",
  amber: "#ffb020",
  red: "#ff3b5c",
};

const card: React.CSSProperties = {
  background: C.panel,
  border: `1px solid ${C.border}`,
  borderRadius: 12,
  padding: 16,
};

function factoryColor(f: AnyObj): string {
  const s = (f?.state || "").toUpperCase();
  if (s === "CONVERGED" || s === "IMPROVING") return C.green;
  if (s === "UNKNOWN" || !s) return C.mut;
  return C.cyan;
}

export const OverviewControlPlane: React.FC = () => {
  const [data, setData] = useState<AnyObj | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<string>("");

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(STATUS_URL, { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        if (!alive) return;
        setData(j);
        setError(null);
        setFetchedAt(new Date().toLocaleTimeString());
      } catch (e: any) {
        if (!alive) return;
        setError(String(e?.message || e));
      }
    };
    load();
    const t = setInterval(load, POLL_MS);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  if (error && !data) {
    return (
      <div style={{ ...card, borderColor: C.red, color: C.red, fontFamily: "monospace" }}>
        Control-plane status feed unreachable ({error}). Is :8765 up with /api/v1/control-plane/status?
      </div>
    );
  }
  if (!data) {
    return <div style={{ ...card, color: C.mut, fontFamily: "monospace" }}>Loading control-plane status…</div>;
  }

  const factories: [string, AnyObj][] = Object.entries(data.per_factory || {});
  const rec = data.reconciliation || {};
  const tests = data.tests || {};
  const blockers = data.blockers || {};
  const approvals: AnyObj[] = Array.isArray(data.approvals) ? data.approvals : [];
  const cp: string[] = Array.isArray(data.critical_path) ? data.critical_path : [];

  return (
    <div style={{ color: C.ink, fontFamily: "'Inter',-apple-system,sans-serif", display: "grid", gap: 14 }}>
      {/* headline */}
      <div style={{ ...card, display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: ".16em", color: C.mut, textTransform: "uppercase" }}>
            Goal progress · single source of truth
          </div>
          <div style={{ fontSize: 40, fontWeight: 800, color: C.cyan, lineHeight: 1.1 }}>
            {data.goal_percent ?? "—"}%
          </div>
          <div style={{ fontSize: 11, color: C.mut }}>
            authoritative: {String(rec.authoritative ?? "—")}% · legacy contract:{" "}
            {rec.legacy_static_contract_percent == null ? "n/a" : rec.legacy_static_contract_percent + "%"}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: C.mut }}>
          <div>evidence {data.evidence_coverage_percent ?? "—"}%</div>
          <div>tests <b style={{ color: (tests.failing ?? 0) > 0 ? C.red : C.green }}>{tests.passing ?? "—"}/{tests.failing ?? "—"}</b></div>
          <div>crit-path {data.critical_path_remaining_minutes ?? "—"} min</div>
          <div style={{ color: error ? C.amber : C.mut }}>{error ? "STALE — retrying" : "live " + fetchedAt}</div>
        </div>
      </div>

      {/* factories */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
        {factories.map(([name, f]) => (
          <div key={name} style={{ ...card }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 800, letterSpacing: ".05em" }}>{name}</span>
              <span style={{ fontSize: 10, color: factoryColor(f), fontWeight: 700 }}>
                {(f.state || (f.monetization_readiness_percent != null ? "REVENUE" : "—")).toString().toUpperCase()}
              </span>
            </div>
            <div style={{ fontSize: 12, color: C.mut, marginTop: 8 }}>
              {f.mean_score != null && <div>mean <b style={{ color: C.ink }}>{f.mean_score}</b> · gen {f.generation ?? "—"}</div>}
              {f.monetization_readiness_percent != null && (
                <div>monetization <b style={{ color: C.ink }}>{f.monetization_readiness_percent}%</b></div>
              )}
              {f.stripe_sandbox_readiness != null && <div>stripe: {String(f.stripe_sandbox_readiness)}</div>}
            </div>
          </div>
        ))}
      </div>

      {/* critical path + blockers + approvals */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={card}>
          <div style={{ fontSize: 11, letterSpacing: ".16em", color: C.mut, textTransform: "uppercase", marginBottom: 8 }}>
            Critical path · {blockers.blocked_task_count ?? 0} blocked
          </div>
          <div style={{ fontFamily: "monospace", color: C.cyan }}>{cp.length ? cp.join(" → ") : "—"}</div>
        </div>
        <div style={card}>
          <div style={{ fontSize: 11, letterSpacing: ".16em", color: C.mut, textTransform: "uppercase", marginBottom: 8 }}>
            Approvals awaiting operator ({approvals.length})
          </div>
          {approvals.length === 0 ? (
            <div style={{ color: C.mut }}>none</div>
          ) : (
            approvals.slice(0, 6).map((a, i) => (
              <div key={a.id || i} style={{ fontSize: 12, color: C.amber, padding: "2px 0" }}>
                <b>{a.id || "—"}</b> · {a.severity || ""} — {a.action || ""}
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ fontSize: 10, color: C.mut, fontFamily: "monospace" }}>
        source: {STATUS_URL} · {data.provenance || ""}
      </div>
    </div>
  );
};

export default OverviewControlPlane;
