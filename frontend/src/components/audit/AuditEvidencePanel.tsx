import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";

type Props = {
  event: AuditEvent;
};

export const AuditEvidencePanel: React.FC<Props> = ({ event }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", textAlign: "left", fontSize: "11px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "6px" }}>
        <span style={{ color: "#818cf8", fontWeight: "bold", fontSize: "10px" }}>PROVENANCE & DATA LINEAGE</span>
        <span
          style={{
            background: "rgba(255,255,255,0.08)",
            padding: "2px 6px",
            borderRadius: "4px",
            fontSize: "9px",
            color: "#fff",
            fontFamily: "monospace",
            textTransform: "uppercase"
          }}
        >
          {event.provenance.source}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span style={{ color: "var(--text-secondary)" }}>Evidence Confidence Status:</span>
        <span style={{ fontSize: "14px", fontWeight: "bold", color: "#fff" }}>
          {event.provenance.confidence !== undefined ? `${event.provenance.confidence}%` : "100% [OBSERVED]"}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span style={{ color: "var(--text-secondary)" }}>Backing Verification Evidence:</span>
        {event.provenance.evidence_refs && event.provenance.evidence_refs.length > 0 ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
            {event.provenance.evidence_refs.map((ref, idx) => (
              <span
                key={idx}
                style={{
                  background: "rgba(0, 229, 255, 0.12)",
                  border: "1px solid rgba(0, 229, 255, 0.25)",
                  color: "#00e5ff",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontFamily: "monospace",
                  fontSize: "9px"
                }}
              >
                📄 {ref}
              </span>
            ))}
          </div>
        ) : (
          <span style={{ fontStyle: "italic", color: "#f87171" }}>⚠️ No evidence files linked to this record.</span>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span style={{ color: "var(--text-secondary)" }}>Secure Enclave Context:</span>
        <span
          style={{
            color: "#10b981",
            fontFamily: "monospace",
            fontWeight: "bold",
            background: "rgba(16, 185, 129, 0.08)",
            padding: "4px 8px",
            borderRadius: "4px",
            border: "1px solid rgba(16, 185, 129, 0.2)",
            display: "inline-block",
            width: "fit-content"
          }}
        >
          🔒 SIPRNET (TACTICAL COMPUTING)
        </span>
      </div>
    </div>
  );
};
