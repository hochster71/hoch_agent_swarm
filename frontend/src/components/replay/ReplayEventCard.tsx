import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";

type Props = {
  event?: AuditEvent;
};

export const ReplayEventCard: React.FC<Props> = ({ event }) => {
  if (!event) {
    return (
      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", padding: "16px 0" }}>
        No event data. Scrub the timeline slider...
      </div>
    );
  }

  const getResultStyle = (res: string) => {
    switch (res) {
      case "success":
        return { color: "#10b981", bg: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)" };
      case "failed":
      case "blocked":
        return { color: "#ef4444", bg: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.2)" };
      default:
        return { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)" };
    }
  };

  const style = getResultStyle(event.result);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", textAlign: "left", fontSize: "11px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "monospace", color: "var(--text-secondary)" }}>
          EVENT ID: {event.event_id || "evt_unknown"}
        </span>
        <span
          style={{
            background: style.bg,
            border: style.border,
            color: style.color,
            padding: "2px 8px",
            borderRadius: "4px",
            fontSize: "8px",
            fontWeight: "bold",
            textTransform: "uppercase"
          }}
        >
          {event.result}
        </span>
      </div>

      <div style={{ background: "rgba(0,0,0,0.15)", border: "1px solid rgba(255,255,255,0.03)", borderRadius: "6px", padding: "10px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>ACTION TYPE</span>
          <span style={{ display: "block", color: "#fff", fontWeight: "bold", fontFamily: "monospace", marginTop: "2px" }}>
            {event.action.type}
          </span>
        </div>
        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>SUMMARY DETAIL</span>
          <p style={{ margin: "2px 0 0 0", color: "#cbd5e1", lineHeight: "1.4" }}>
            {event.action.summary}
          </p>
        </div>
        {event.action.command_text && (
          <div>
            <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>RAW TEXT COMMAND</span>
            <span style={{ display: "block", color: "#00e5ff", fontFamily: "monospace", marginTop: "2px" }}>
              &gt; {event.action.command_text}
            </span>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>ACTOR INITIATOR</span>
          <div style={{ marginTop: "2px", fontWeight: "bold", color: "#fff" }}>
            👤 {event.actor.name}
            <span style={{ display: "block", fontSize: "9px", color: "var(--text-secondary)", fontWeight: "normal" }}>
              role: {event.actor.role || "System Process"} ({event.actor.type})
            </span>
          </div>
        </div>

        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>TARGET RECIPIENT</span>
          <div style={{ marginTop: "2px", fontWeight: "bold", color: "#fff" }}>
            🎯 {event.target.name || event.target.id}
            <span style={{ display: "block", fontSize: "9px", color: "var(--text-secondary)", fontWeight: "normal" }}>
              type: {event.target.type}
            </span>
          </div>
        </div>
      </div>

      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "var(--text-secondary)" }}>Correlation ID:</span>
        <span style={{ fontFamily: "monospace", color: "#818cf8" }}>{event.correlation_id}</span>
      </div>
    </div>
  );
};
