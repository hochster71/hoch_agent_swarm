import React, { useEffect, useState } from "react";

/**
 * S3 — PERT / Critical-Path tab for the canonical control plane.
 *
 * Reads the shell-facing PERT feed (GET /api/v1/control-plane/pert on :8000, which
 * passes through the authoritative :8765 pert_cpm). Renders the task graph with
 * te / slack and highlights the critical path. Self-contained (React + inline styles);
 * fail-visible if the feed is unreachable. Ports the :8765 "/" PERT view into the shell.
 */

const PERT_URL = "/api/v1/control-plane/pert";
const POLL_MS = 15000;
type AnyObj = Record<string, any>;

const C = {
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

const td: React.CSSProperties = { padding: "6px 10px", fontSize: 12, borderBottom: "1px solid rgba(255,255,255,0.06)" };
const th: React.CSSProperties = { ...td, color: C.mut, textTransform: "uppercase", letterSpacing: ".1em", fontSize: 10, textAlign: "left" };

export const PertCriticalPathTab: React.FC = () => {
  const [data, setData] = useState<AnyObj | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [at, setAt] = useState<string>("");

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const r = await fetch(PERT_URL, { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        if (!alive) return;
        setData(j);
        setError(null);
        setAt(new Date().toLocaleTimeString());
      } catch (e: any) {
        if (!alive) return;
        setError(String(e?.message || e));
      }
    };
    load();
    const t = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(t); };
  }, []);

  if (error && !data) {
    return <div style={{ ...card, borderColor: C.red, color: C.red, fontFamily: "monospace" }}>PERT feed unreachable ({error}).</div>;
  }
  if (!data) {
    return <div style={{ ...card, color: C.mut, fontFamily: "monospace" }}>Loading PERT / critical path…</div>;
  }

  const cp: string[] = Array.isArray(data.critical_path) ? data.critical_path : [];
  const cpSet = new Set(cp);
  const tasks: AnyObj[] = Array.isArray(data.tasks) ? data.tasks : [];
  const statusColor = (s: string) =>
    /complete/i.test(s) ? C.green : /block/i.test(s) ? C.red : /progress|active/i.test(s) ? C.cyan : C.mut;

  return (
    <div style={{ color: C.ink, fontFamily: "'Inter',-apple-system,sans-serif", display: "grid", gap: 14 }}>
      <div style={{ ...card, display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: ".16em", color: C.mut, textTransform: "uppercase" }}>Critical path</div>
          <div style={{ fontFamily: "monospace", color: C.cyan, fontSize: 15, marginTop: 4 }}>{cp.length ? cp.join(" → ") : "—"}</div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, color: C.mut }}>
          <div>expected <b style={{ color: C.ink }}>{data.expected_duration_minutes ?? "—"}</b> min</div>
          <div>{tasks.length} tasks</div>
          <div style={{ color: data.pert_source_available ? C.mut : C.amber }}>
            {data.pert_source_available ? "live " + at : "PERT source (:8765) unreachable"}
          </div>
        </div>
      </div>

      <div style={{ ...card, padding: 0, overflow: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>ID</th><th style={th}>Task</th><th style={th}>Owner</th>
              <th style={th}>TE</th><th style={th}>Slack</th><th style={th}>Status</th><th style={th}>Crit</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t, i) => {
              const crit = t.is_critical || cpSet.has(t.id);
              return (
                <tr key={t.id || i} style={crit ? { background: "rgba(34,246,255,0.06)" } : undefined}>
                  <td style={{ ...td, color: crit ? C.cyan : C.mut, fontFamily: "monospace", fontWeight: crit ? 700 : 400 }}>{t.id}</td>
                  <td style={{ ...td, color: C.ink }}>{t.title}</td>
                  <td style={{ ...td, color: C.mut }}>{t.owner_agent || t.A || "—"}</td>
                  <td style={{ ...td, color: C.ink }}>{t.te ?? "—"}</td>
                  <td style={{ ...td, color: (t.slack ?? 1) === 0 ? C.amber : C.mut }}>{t.slack ?? "—"}</td>
                  <td style={{ ...td, color: statusColor(String(t.status || "")) }}>{t.status || "—"}</td>
                  <td style={{ ...td, color: crit ? C.cyan : C.mut }}>{crit ? "●" : ""}</td>
                </tr>
              );
            })}
            {tasks.length === 0 && (
              <tr><td style={{ ...td, color: C.mut }} colSpan={7}>no task data</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{ fontSize: 10, color: C.mut, fontFamily: "monospace" }}>source: {PERT_URL} (→ :8765 pert_cpm)</div>
    </div>
  );
};

export default PertCriticalPathTab;
