import React from "react";
import type { ReplaySession } from "../../lib/replay/replayTypes";

type Props = {
  session: ReplaySession;
  onSelectIndex: (idx: number) => void;
};

export const ReplayEventLane: React.FC<Props> = ({ session, onSelectIndex }) => {
  const getActionAbbreviation = (type: string) => {
    switch (type) {
      case "TELEMETRY_UPDATED":
        return "TEL";
      case "AI_RECOMMENDATION_GENERATED":
        return "REC";
      case "COMMAND_PREVIEWED":
        return "PRV";
      case "COMMAND_EXECUTED":
        return "EXE";
      case "COMMAND_BLOCKED":
        return "BLK";
      case "POLICY_CHECKED":
        return "POL";
      default:
        return "EVT";
    }
  };

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case "critical":
      case "high":
        return "#f87171";
      case "medium":
        return "#f59e0b";
      default:
        return "#00e5ff";
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        overflowX: "auto",
        padding: "10px 4px",
        minHeight: "50px",
        boxSizing: "border-box"
      }}
    >
      {session.events.map((event, idx) => {
        const isCurrent = idx === session.current_index;
        const color = getSeverityColor(event.severity);
        
        return (
          <div
            key={idx}
            onClick={() => onSelectIndex(idx)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "4px",
              cursor: "pointer",
              flexShrink: 0
            }}
          >
            {/* Dot marker */}
            <div
              style={{
                width: isCurrent ? "12px" : "8px",
                height: isCurrent ? "12px" : "8px",
                borderRadius: "50%",
                background: isCurrent ? color : `${color}55`,
                border: isCurrent ? "2px solid #fff" : `1px solid ${color}`,
                boxShadow: isCurrent ? `0 0 10px ${color}` : "none",
                transition: "all 0.15s ease-out"
              }}
            />
            {/* Timestamp label */}
            <span
              style={{
                fontSize: "7px",
                fontFamily: "monospace",
                color: isCurrent ? "#fff" : "var(--text-secondary)",
                fontWeight: isCurrent ? "bold" : "normal"
              }}
            >
              {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
            </span>
            {/* Label box */}
            <span
              style={{
                fontSize: "8px",
                fontWeight: "bold",
                padding: "2px 4px",
                borderRadius: "3px",
                background: isCurrent ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.15)",
                color: isCurrent ? "#fff" : "var(--text-secondary)",
                border: isCurrent ? "1px solid rgba(255,255,255,0.15)" : "1px solid rgba(255,255,255,0.04)"
              }}
            >
              {getActionAbbreviation(event.action.type)}
            </span>
          </div>
        );
      })}
    </div>
  );
};
