import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { getAuditIntegrityScore } from "../../lib/audit/auditIntegrity";

type Props = {
  events: AuditEvent[];
};

export const AuditIntegritySummary: React.FC<Props> = ({ events }) => {
  const score = React.useMemo(() => getAuditIntegrityScore(events), [events]);
  
  const getStatusColor = (val: number) => {
    if (val >= 95) return "#10b981"; // Healthy green
    if (val >= 80) return "#f59e0b"; // Warning amber
    return "#ef4444"; // Error red
  };

  return (
    <div
      style={{
        background: "rgba(0,0,0,0.25)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "8px",
        padding: "12px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        textAlign: "left"
      }}
    >
      <div>
        <span style={{ fontSize: "9px", color: "var(--text-secondary)", fontWeight: "bold", letterSpacing: "0.5px", display: "block" }}>
          AUDIT INTEGRITY SCORE
        </span>
        <span style={{ fontSize: "11px", color: "#cbd5e1", marginTop: "4px", display: "block" }}>
          {events.length} active transactions evaluated.
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px" }}>
        <span style={{ fontSize: "28px", fontWeight: "bold", color: getStatusColor(score), fontFamily: "monospace" }}>
          {score}%
        </span>
        <span
          style={{
            fontSize: "8px",
            fontWeight: "bold",
            padding: "1px 6px",
            borderRadius: "4px",
            background: `${getStatusColor(score)}22`,
            color: getStatusColor(score),
            border: `1px solid ${getStatusColor(score)}44`,
            textTransform: "uppercase"
          }}
        >
          {score >= 95 ? "VERIFIED" : score >= 80 ? "DEGRADED" : "COMPROMISED"}
        </span>
      </div>
    </div>
  );
};
