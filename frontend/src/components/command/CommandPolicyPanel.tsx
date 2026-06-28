import React from "react";

interface CommandPolicyPanelProps {
  policy: {
    required: boolean;
    result: "passed" | "failed" | "warning" | "not_required";
    policy_ids: string[];
    explanation: string;
  };
}

export const CommandPolicyPanel: React.FC<CommandPolicyPanelProps> = ({ policy }) => {
  let statusText = "● PASSED";
  let color = "#10b981"; // green
  let bg = "rgba(16, 185, 129, 0.05)";
  let border = "rgba(16, 185, 129, 0.15)";

  if (policy.result === "failed") {
    statusText = "● BLOCKED / FAILED";
    color = "#ef4444"; // red
    bg = "rgba(239, 68, 68, 0.05)";
    border = "rgba(239, 68, 68, 0.15)";
  } else if (policy.result === "warning") {
    statusText = "▲ WARNING";
    color = "#f59e0b"; // yellow/amber
    bg = "rgba(245, 158, 11, 0.05)";
    border = "rgba(245, 158, 11, 0.15)";
  } else if (policy.result === "not_required") {
    statusText = "NOT REQUIRED";
    color = "#cbd5e1"; // gray
    bg = "rgba(255, 255, 255, 0.02)";
    border = "rgba(255, 255, 255, 0.05)";
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold" }}>
        POLICY COMPLIANCE CHECK
      </span>
      <div
        style={{
          background: bg,
          border: `1px solid ${border}`,
          borderRadius: "6px",
          padding: "8px 12px",
          display: "flex",
          flexDirection: "column",
          gap: "4px"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color, fontWeight: "bold", fontSize: "10px" }}>{statusText}</span>
          <span style={{ color: "var(--text-secondary)", fontSize: "8.5px", fontFamily: "monospace" }}>
            {policy.policy_ids.join(", ") || "N/A"}
          </span>
        </div>
        <div style={{ color: "#fff", fontSize: "10px", lineHeight: "1.4" }}>
          {policy.explanation}
        </div>
      </div>
    </div>
  );
};
