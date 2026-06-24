import React from "react";

type Violation = {
  timestamp: string;
  command: string;
  actor: string;
  reason: string;
  status: "BLOCKED" | "OVERRIDDEN";
};

export const PolicyViolationList: React.FC = () => {
  const violations: Violation[] = [
    {
      timestamp: "10:12:45 AM",
      command: "force delete all logs",
      actor: "guest.viewer",
      reason: "Viewer role cannot execute operational commands.",
      status: "BLOCKED"
    },
    {
      timestamp: "09:41:22 AM",
      command: "rollback server --force",
      actor: "operator.alex",
      reason: "High-risk command requires rollback capability.",
      status: "BLOCKED"
    },
    {
      timestamp: "08:15:30 AM",
      command: "rebalance workload",
      actor: "operator.michael",
      reason: "Session integrity failed or unknown.",
      status: "BLOCKED"
    }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", textAlign: "left", fontSize: "11px" }}>
      {violations.map((v, idx) => (
        <div
          key={idx}
          style={{
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.05)",
            borderRadius: "6px",
            padding: "8px 12px",
            display: "flex",
            flexDirection: "column",
            gap: "4px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontFamily: "monospace", color: "#f87171", fontWeight: "bold" }}>
              {v.timestamp} - {v.status}
            </span>
            <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>
              actor: {v.actor}
            </span>
          </div>
          <div style={{ color: "#fff", fontFamily: "monospace", wordBreak: "break-all" }}>
            &gt; {v.command}
          </div>
          <div style={{ color: "#ef4444", fontSize: "10px", marginTop: "2px" }}>
            Violation: {v.reason}
          </div>
        </div>
      ))}
    </div>
  );
};
