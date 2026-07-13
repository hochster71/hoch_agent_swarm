import React from "react";
import type { OperationalInsight, InsightFeedback } from "../../lib/intel/insightTypes";
import { InsightFeedbackBar } from "./InsightFeedbackBar";

type Props = {
  insight: OperationalInsight;
  onClose: () => void;
  onSubmitFeedback: (value: InsightFeedback) => void;
};

export const InsightExplanationPanel: React.FC<Props> = ({ insight, onClose, onSubmitFeedback }) => {
  return (
    <aside
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        width: "420px",
        height: "100vh",
        background: "rgba(11, 15, 25, 0.95)",
        backdropFilter: "blur(12px)",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "-10px 0 30px rgba(0,0,0,0.5)",
        zIndex: 1050,
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        color: "#fff",
        textAlign: "left",
        boxSizing: "border-box"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "10px" }}>
        <div>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", fontWeight: "bold", textTransform: "uppercase" }}>
            EXPLAINABLE AI INTEL
          </span>
          <h2 style={{ margin: "4px 0 0 0", fontSize: "14px", fontWeight: "bold" }}>{insight.title}</h2>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "4px",
            color: "#fff",
            fontSize: "10px",
            padding: "2px 8px",
            cursor: "pointer"
          }}
        >
          Close
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px", overflowY: "auto", flexGrow: 1, paddingRight: "4px" }}>
        {/* Rationale */}
        <section
          style={{
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.04)",
            borderRadius: "6px",
            padding: "10px"
          }}
        >
          <span style={{ fontSize: "9px", color: "#818cf8", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            DECISION RATIONALE
          </span>
          <p style={{ margin: 0, fontSize: "11px", color: "#cbd5e1", lineHeight: "1.4" }}>
            {insight.explanation.rationale}
          </p>
        </section>

        {/* Contributing Factors */}
        <section
          style={{
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.04)",
            borderRadius: "6px",
            padding: "10px"
          }}
        >
          <span style={{ fontSize: "9px", color: "#818cf8", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            CONTRIBUTING FACTORS
          </span>
          <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#cbd5e1", lineHeight: "1.5" }}>
            {insight.explanation.contributing_factors.map((factor, idx) => (
              <li key={idx} style={{ marginBottom: "2px" }}>{factor}</li>
            ))}
          </ul>
        </section>

        {/* Evidence References */}
        <section
          style={{
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.04)",
            borderRadius: "6px",
            padding: "10px"
          }}
        >
          <span style={{ fontSize: "9px", color: "#818cf8", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            TELEMETRY EVIDENCE PATHS
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
            {insight.explanation.evidence_refs.map((ref, idx) => (
              <span
                key={idx}
                style={{
                  background: "rgba(0, 229, 255, 0.1)",
                  border: "1px solid rgba(0, 229, 255, 0.2)",
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
        </section>

        {/* Assumptions */}
        <section
          style={{
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.04)",
            borderRadius: "6px",
            padding: "10px"
          }}
        >
          <span style={{ fontSize: "9px", color: "#818cf8", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            UNDERLYING ASSUMPTIONS
          </span>
          <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#cbd5e1", lineHeight: "1.5" }}>
            {insight.explanation.assumptions.map((ass, idx) => (
              <li key={idx} style={{ marginBottom: "2px" }}>{ass}</li>
            ))}
          </ul>
        </section>
      </div>

      {/* Feedback Bar */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "12px" }}>
        {insight.feedback ? (
          <div style={{ background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "6px", padding: "8px 12px", fontSize: "11px", color: "#10b981" }}>
            ✓ Feedback submitted: <strong>{insight.feedback.value.toUpperCase()}</strong>
          </div>
        ) : (
          <InsightFeedbackBar onSubmit={onSubmitFeedback} />
        )}
      </div>
    </aside>
  );
};
