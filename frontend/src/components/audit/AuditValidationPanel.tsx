import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { validateAuditEvents } from "../../lib/audit/auditValidation";

type Props = {
  events: AuditEvent[];
  onImportFixture?: (type: "valid" | "invalid") => void;
};

export const AuditValidationPanel: React.FC<Props> = ({ events, onImportFixture }) => {
  const validation = React.useMemo(() => validateAuditEvents(events), [events]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", textAlign: "left" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "12px", color: "#818cf8", margin: 0, fontWeight: "bold" }}>
          QA COMPLIANCE AUDITING
        </h3>
        {onImportFixture && (
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => onImportFixture("valid")}
              style={{
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#10b981",
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "4px",
                cursor: "pointer"
              }}
            >
              + QA Valid Event
            </button>
            <button
              onClick={() => onImportFixture("invalid")}
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                color: "#f87171",
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "4px",
                cursor: "pointer"
              }}
            >
              + QA Incomplete Event
            </button>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "6px", padding: "8px" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block" }}>VALIDATED RECORDS</span>
          <span style={{ fontSize: "18px", fontWeight: "bold", color: "#10b981" }}>{validation.valid.length}</span>
        </div>
        <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "6px", padding: "8px" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block" }}>MALFORMED RECORDS</span>
          <span style={{ fontSize: "18px", fontWeight: "bold", color: validation.invalid.length > 0 ? "#ef4444" : "#10b981" }}>
            {validation.invalid.length}
          </span>
        </div>
      </div>

      {validation.invalid.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "10px", color: "#f87171", fontWeight: "bold" }}>⚠️ MALFORMED EVENTS DETECTED:</span>
          {validation.invalid.map((item, idx) => (
            <div
              key={idx}
              style={{
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                borderRadius: "6px",
                padding: "8px",
                fontSize: "11px"
              }}
            >
              <div style={{ fontWeight: "bold", color: "#f87171", marginBottom: "4px" }}>
                Index {idx} ({item.event.action?.type || "UNKNOWN_ACTION"})
              </div>
              <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1" }}>
                {item.reasons.map((reason, rIdx) => (
                  <li key={rIdx}>{reason}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {validation.missingPolicy.length > 0 && (
        <div style={{ background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)", borderRadius: "6px", padding: "8px", fontSize: "11px" }}>
          <span style={{ fontWeight: "bold", color: "#f59e0b", display: "block", marginBottom: "4px" }}>
            ⚠️ MISSING POLICY CONTEXTS ({validation.missingPolicy.length}):
          </span>
          <div style={{ color: "#cbd5e1" }}>
            Audit events should possess a valid `policy` evaluation statement. The following IDs are missing policy checks:{" "}
            {validation.missingPolicy.map((e) => `[${e.event_id || "No ID"}]`).join(", ")}
          </div>
        </div>
      )}

      {validation.missingEvidence.length > 0 && (
        <div style={{ background: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)", borderRadius: "6px", padding: "8px", fontSize: "11px" }}>
          <span style={{ fontWeight: "bold", color: "#f59e0b", display: "block", marginBottom: "4px" }}>
            ⚠️ MISSING EVIDENCE REFERENCES ({validation.missingEvidence.length}):
          </span>
          <div style={{ color: "#cbd5e1" }}>
            Audit events must contain reference logs in `evidence_refs`. The following events lack active links:{" "}
            {validation.missingEvidence.map((e) => `[${e.event_id || "No ID"}]`).join(", ")}
          </div>
        </div>
      )}

      {validation.missingConfidence.length > 0 && (
        <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "6px", padding: "8px", fontSize: "11px" }}>
          <span style={{ fontWeight: "bold", color: "#f87171", display: "block", marginBottom: "4px" }}>
            ⚠️ UNCALIBRATED AI DATA LINEAGE ({validation.missingConfidence.length}):
          </span>
          <div style={{ color: "#cbd5e1" }}>
            Inferred or predicted events must contain an active model `confidence` score. The following events lack a confidence score:{" "}
            {validation.missingConfidence.map((e) => `[${e.event_id || "No ID"}]`).join(", ")}
          </div>
        </div>
      )}
    </div>
  );
};
