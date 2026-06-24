import React from "react";
import type { OperationalInsight } from "../../lib/intel/insightTypes";

type Props = {
  insights: OperationalInsight[];
};

export const InsightHistory: React.FC<Props> = ({ insights }) => {
  const reviewed = insights.filter(x => x.status === "reviewed" || x.status === "dismissed");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", textAlign: "left" }}>
      {reviewed.length === 0 ? (
        <div style={{ fontStyle: "italic", color: "var(--text-secondary)", padding: "10px 0" }}>
          No actions reviewed in this session yet.
        </div>
      ) : (
        reviewed.map((item, idx) => (
          <div
            key={idx}
            style={{
              background: "rgba(0,0,0,0.15)",
              border: "1px solid rgba(255,255,255,0.04)",
              borderRadius: "6px",
              padding: "8px 12px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}
          >
            <div>
              <span style={{ fontWeight: "bold", color: "#cbd5e1" }}>{item.title}</span>
              <span style={{ display: "block", color: "var(--text-secondary)", fontSize: "9px", marginTop: "2px" }}>
                reviewed at {item.feedback?.submitted_at ? new Date(item.feedback.submitted_at).toLocaleTimeString() : "N/A"}
              </span>
            </div>
            <span
              style={{
                background: item.feedback?.value === "helpful" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                color: item.feedback?.value === "helpful" ? "#10b981" : "#f87171",
                padding: "2px 8px",
                borderRadius: "4px",
                fontWeight: "bold",
                fontSize: "9px",
                textTransform: "uppercase"
              }}
            >
              {item.feedback?.value || "DISMISSED"}
            </span>
          </div>
        ))
      )}
    </div>
  );
};
