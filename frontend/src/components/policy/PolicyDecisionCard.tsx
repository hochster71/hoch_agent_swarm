import React from "react";
import type { PolicyEvaluationResult } from "../../lib/policy/policyTypes";

type Props = {
  result: PolicyEvaluationResult;
};

export const PolicyDecisionCard: React.FC<Props> = ({ result }) => {
  const getDecisionStyles = (decision: string) => {
    switch (decision) {
      case "allow":
        return {
          color: "#10b981",
          background: "rgba(16, 185, 129, 0.1)",
          border: "1px solid rgba(16, 185, 129, 0.3)",
          text: "ALLOW (Execution Permitted)"
        };
      case "warn":
        return {
          color: "#f59e0b",
          background: "rgba(245, 158, 11, 0.1)",
          border: "1px solid rgba(245, 158, 11, 0.3)",
          text: "WARNING (Requires confirmation)"
        };
      case "block":
      default:
        return {
          color: "#ef4444",
          background: "rgba(239, 68, 68, 0.1)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
          text: "BLOCKED (Execution Terminated)"
        };
    }
  };

  const style = getDecisionStyles(result.decision);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", textAlign: "left" }}>
      {/* Banner */}
      <div
        style={{
          background: style.background,
          border: style.border,
          borderRadius: "8px",
          padding: "16px",
          textAlign: "center",
          color: style.color,
          fontWeight: "bold",
          fontSize: "14px",
          letterSpacing: "0.5px"
        }}
      >
        {style.text}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-secondary)" }}>
        <span>Policy Risk Score:</span>
        <span style={{ color: "#fff", fontWeight: "bold" }}>{result.score}/100</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", marginTop: "4px" }}>
        {/* Passed Checks */}
        <div>
          <span style={{ color: "#10b981", fontWeight: "bold", display: "block", marginBottom: "4px" }}>Passed Checks ({result.passed.length})</span>
          <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1" }}>
            {result.passed.map((item, idx) => (
              <li key={idx} style={{ marginBottom: "2px" }}>{item}</li>
            ))}
          </ul>
        </div>

        {/* Warnings */}
        {result.warnings.length > 0 && (
          <div>
            <span style={{ color: "#f59e0b", fontWeight: "bold", display: "block", marginBottom: "4px" }}>Security Warnings ({result.warnings.length})</span>
            <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1" }}>
              {result.warnings.map((item, idx) => (
                <li key={idx} style={{ marginBottom: "2px" }}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Blockers */}
        {result.blockers.length > 0 && (
          <div>
            <span style={{ color: "#ef4444", fontWeight: "bold", display: "block", marginBottom: "4px" }}>Execution Blockers ({result.blockers.length})</span>
            <ul style={{ margin: 0, paddingLeft: "16px", color: "#cbd5e1" }}>
              {result.blockers.map((item, idx) => (
                <li key={idx} style={{ marginBottom: "2px" }}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {result.approval_required && (
        <div
          style={{
            background: "rgba(129, 140, 248, 0.08)",
            border: "1px solid rgba(129, 140, 248, 0.2)",
            borderRadius: "6px",
            padding: "8px 12px",
            fontSize: "11px",
            color: "#818cf8",
            marginTop: "6px"
          }}
        >
          🔐 <strong>Signature Required:</strong> {result.approval_reason}
        </div>
      )}
    </div>
  );
};
