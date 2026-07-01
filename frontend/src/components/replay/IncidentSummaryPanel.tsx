import React from "react";
import type { IncidentSummary } from "../../lib/replay/replayTypes";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { IncidentExportButton } from "./IncidentExportButton";

type Props = {
  summary: IncidentSummary;
  events: AuditEvent[];
};

export const IncidentSummaryPanel: React.FC<Props> = ({ summary, events }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", textAlign: "left", fontSize: "11px" }}>
      <h3 style={{ fontSize: "12px", color: "#f87171", margin: 0, fontWeight: "bold", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "6px" }}>
        🚨 INCIDENT RECONSTRUCTION
      </h3>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "var(--text-secondary)" }}>Incident ID:</span>
        <span style={{ fontFamily: "monospace", color: "#fff", fontWeight: "bold" }}>{summary.incident_id}</span>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "var(--text-secondary)" }}>Timeline Span:</span>
        <span style={{ color: "#38bdf8", fontWeight: "500" }}>
          {new Date(summary.time_range.start).toLocaleTimeString()} - {new Date(summary.time_range.end).toLocaleTimeString()}
        </span>
      </div>

      {/* Root Cause */}
      <div>
        <span style={{ color: "var(--text-secondary)", fontSize: "9px", display: "block", marginBottom: "4px" }}>ROOT CAUSE HYPOTHESIS</span>
        <p style={{ margin: 0, background: "rgba(239, 68, 68, 0.05)", border: "1px solid rgba(239, 68, 68, 0.15)", borderRadius: "6px", padding: "8px", color: "#cbd5e1", lineHeight: "1.4" }}>
          {summary.root_cause_hypothesis}
        </p>
      </div>

      {/* Policy Findings */}
      <div>
        <span style={{ color: "var(--text-secondary)", fontSize: "9px", display: "block", marginBottom: "4px" }}>ZTA POLICY AUDIT FINDINGS</span>
        {summary.policy_findings.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1", lineHeight: "1.4" }}>
            {summary.policy_findings.map((finding, idx) => (
              <li key={idx} style={{ marginBottom: "2px" }}>{finding}</li>
            ))}
          </ul>
        ) : (
          <span style={{ fontStyle: "italic", color: "var(--text-secondary)" }}>No explicit policy actions in timeline.</span>
        )}
      </div>

      {/* Remediation */}
      <div>
        <span style={{ color: "var(--text-secondary)", fontSize: "9px", display: "block", marginBottom: "4px" }}>REMEDIATION RECOMMENDATIONS</span>
        <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1", lineHeight: "1.4" }}>
          {summary.remediation_actions.map((act, idx) => (
            <li key={idx} style={{ marginBottom: "2px" }}>{act}</li>
          ))}
        </ul>
      </div>

      {/* Open Questions */}
      <div>
        <span style={{ color: "var(--text-secondary)", fontSize: "9px", display: "block", marginBottom: "4px" }}>OPEN AUDIT QUESTIONS</span>
        <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1", lineHeight: "1.4" }}>
          {summary.open_questions.map((q, idx) => (
            <li key={idx} style={{ marginBottom: "2px" }}>{q}</li>
          ))}
        </ul>
      </div>

      <div style={{ flexGrow: 1 }} />

      {/* Export Evidence packet button */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
        <IncidentExportButton summary={summary} events={events} />
      </div>
    </div>
  );
};
