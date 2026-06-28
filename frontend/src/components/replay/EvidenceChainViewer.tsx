import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";

type Props = {
  event: AuditEvent;
};

export const EvidenceChainViewer: React.FC<Props> = ({ event }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", textAlign: "left", fontSize: "11px" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold" }}>
        TIMELINE EVIDENCE DATA LINEAGE
      </span>
      <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "6px", padding: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "var(--text-secondary)" }}>Provenance Source:</span>
          <span style={{ fontWeight: "bold", textTransform: "uppercase", color: "#38bdf8" }}>{event.provenance.source}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "var(--text-secondary)" }}>Evidence Confidence:</span>
          <span style={{ fontWeight: "bold", color: "#fff" }}>
            {event.provenance.confidence !== undefined ? `${event.provenance.confidence}%` : "100% [OBSERVED]"}
          </span>
        </div>
        <div>
          <span style={{ color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>Verifiable Telemetry Keys:</span>
          {event.provenance.evidence_refs && event.provenance.evidence_refs.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
              {event.provenance.evidence_refs.map((ref, idx) => (
                <span
                  key={idx}
                  style={{
                    background: "rgba(0, 229, 255, 0.12)",
                    border: "1px solid rgba(0, 229, 255, 0.25)",
                    color: "#00e5ff",
                    padding: "1px 6px",
                    borderRadius: "4px",
                    fontFamily: "monospace",
                    fontSize: "8px"
                  }}
                >
                  📄 {ref}
                </span>
              ))}
            </div>
          ) : (
            <span style={{ fontStyle: "italic", color: "#f87171" }}>⚠️ No evidence references linked.</span>
          )}
        </div>
      </div>
    </div>
  );
};
