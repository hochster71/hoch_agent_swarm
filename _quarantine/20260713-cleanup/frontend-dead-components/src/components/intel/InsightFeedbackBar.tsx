import React from "react";
import type { InsightFeedback } from "../../lib/intel/insightTypes";

type Props = {
  onSubmit: (value: InsightFeedback) => void;
};

export const InsightFeedbackBar: React.FC<Props> = ({ onSubmit }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", textAlign: "left" }}>
      <span style={{ fontSize: "10px", color: "var(--text-secondary)" }}>
        Was this intelligence recommendation helpful?
      </span>
      <div style={{ display: "flex", gap: "6px" }}>
        <button
          onClick={() => onSubmit("helpful")}
          style={{
            flexGrow: 1,
            background: "rgba(16, 185, 129, 0.15)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "4px",
            color: "#10b981",
            padding: "6px",
            fontSize: "11px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Yes
        </button>
        <button
          onClick={() => onSubmit("partial")}
          style={{
            flexGrow: 1,
            background: "rgba(245, 158, 11, 0.15)",
            border: "1px solid rgba(245, 158, 11, 0.3)",
            borderRadius: "4px",
            color: "#f59e0b",
            padding: "6px",
            fontSize: "11px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          Partially
        </button>
        <button
          onClick={() => onSubmit("not_helpful")}
          style={{
            flexGrow: 1,
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "4px",
            color: "#f87171",
            padding: "6px",
            fontSize: "11px",
            fontWeight: "bold",
            cursor: "pointer"
          }}
        >
          No
        </button>
      </div>
    </div>
  );
};
