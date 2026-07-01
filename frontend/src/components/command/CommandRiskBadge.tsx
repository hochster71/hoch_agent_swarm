import React from "react";
import type { CommandRisk } from "../../lib/command/commandTypes";

interface RiskBadgeProps {
  risk: CommandRisk;
}

export const CommandRiskBadge: React.FC<RiskBadgeProps> = ({ risk }) => {
  let color = "#10b981"; // green
  let bg = "rgba(16, 185, 129, 0.15)";
  let border = "rgba(16, 185, 129, 0.3)";

  if (risk === "medium") {
    color = "#f59e0b"; // yellow
    bg = "rgba(245, 158, 11, 0.15)";
    border = "rgba(245, 158, 11, 0.3)";
  } else if (risk === "high") {
    color = "#ef4444"; // red
    bg = "rgba(239, 68, 68, 0.15)";
    border = "rgba(239, 68, 68, 0.3)";
  } else if (risk === "critical") {
    color = "#f43f5e"; // bright red rose
    bg = "rgba(244, 63, 94, 0.2)";
    border = "rgba(244, 63, 94, 0.4)";
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "3px 8px",
        borderRadius: "4px",
        fontSize: "10px",
        fontWeight: "bold",
        color,
        backgroundColor: bg,
        border: `1px solid ${border}`,
        textTransform: "uppercase",
        letterSpacing: "0.5px"
      }}
    >
      {risk === "critical" ? "⚠️ CRITICAL" : risk}
    </span>
  );
};
