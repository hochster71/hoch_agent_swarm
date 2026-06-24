import React from "react";

interface CommandRollbackPanelProps {
  rollback: {
    available: boolean;
    rollback_id?: string;
    explanation: string;
  };
}

export const CommandRollbackPanel: React.FC<CommandRollbackPanelProps> = ({ rollback }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold" }}>
        ROLLBACK RECOVERY STATE
      </span>
      <div
        style={{
          background: "rgba(0, 0, 0, 0.3)",
          border: "1px solid rgba(255, 255, 255, 0.05)",
          borderRadius: "6px",
          padding: "8px 12px",
          display: "flex",
          flexDirection: "column",
          gap: "4px"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: rollback.available ? "#10b981" : "#cbd5e1", fontWeight: "bold", fontSize: "10px" }}>
            {rollback.available ? "● AVAILABLE" : "N/A"}
          </span>
          {rollback.rollback_id && (
            <span style={{ color: "#22d3ee", fontSize: "9px", fontFamily: "monospace", fontWeight: "bold" }}>
              ID: {rollback.rollback_id}
            </span>
          )}
        </div>
        <div style={{ color: "#fff", fontSize: "10px", lineHeight: "1.4" }}>
          {rollback.explanation}
        </div>
      </div>
    </div>
  );
};
