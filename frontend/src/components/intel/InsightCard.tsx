import React from "react";
import type { OperationalInsight } from "../../lib/intel/insightTypes";

type Props = {
  insight: OperationalInsight;
  onExplain: (insight: OperationalInsight) => void;
  onAction: (insight: OperationalInsight) => void;
};

export const InsightCard: React.FC<Props> = ({ insight, onExplain, onAction }) => {
  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case "critical":
      case "high":
        return "#f87171"; // Red
      case "medium":
        return "#f59e0b"; // Orange
      default:
        return "#818cf8"; // Blue
    }
  };

  return (
    <article
      style={{
        background: "rgba(0,0,0,0.2)",
        border: "1px solid rgba(255,255,255,0.04)",
        borderRadius: "8px",
        padding: "12px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        textAlign: "left"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
        <div>
          <span
            style={{
              fontSize: "8px",
              fontWeight: "bold",
              color: getSeverityColor(insight.severity),
              border: `1px solid ${getSeverityColor(insight.severity)}33`,
              background: `${getSeverityColor(insight.severity)}11`,
              padding: "1px 6px",
              borderRadius: "4px",
              textTransform: "uppercase"
            }}
          >
            {insight.type} · {insight.severity}
          </span>
          <h3 style={{ margin: "6px 0 0 0", fontSize: "12px", fontWeight: "bold", color: "#fff" }}>
            {insight.title}
          </h3>
          <p style={{ margin: "4px 0 0 0", fontSize: "11px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
            {insight.summary}
          </p>
        </div>
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "6px",
            padding: "4px 8px",
            fontSize: "12px",
            fontWeight: "bold",
            color: "#38bdf8",
            fontFamily: "monospace",
            textAlign: "center"
          }}
        >
          {insight.confidence}%
          <span style={{ display: "block", fontSize: "7px", color: "var(--text-secondary)", fontWeight: "normal" }}>CONFIDENCE</span>
        </div>
      </div>

      <div style={{ display: "flex", gap: "8px" }}>
        <button
          onClick={() => onExplain(insight)}
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "#fff",
            borderRadius: "4px",
            padding: "4px 10px",
            fontSize: "11px",
            cursor: "pointer",
            fontWeight: "bold"
          }}
        >
          Explain Insight
        </button>
        {insight.recommendation && (
          <button
            onClick={() => onAction(insight)}
            style={{
              background: "rgba(0, 229, 255, 0.15)",
              border: "1px solid rgba(0, 229, 255, 0.3)",
              color: "#00e5ff",
              borderRadius: "4px",
              padding: "4px 10px",
              fontSize: "11px",
              cursor: "pointer",
              fontWeight: "bold"
            }}
          >
            {insight.recommendation.action_label}
          </button>
        )}
      </div>
    </article>
  );
};
