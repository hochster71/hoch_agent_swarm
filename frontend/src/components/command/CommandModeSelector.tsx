import React from "react";
import type { CommandMode } from "../../lib/command/commandTypes";

interface CommandModeSelectorProps {
  selectedMode: CommandMode | "override";
  onChange: (mode: CommandMode | "override") => void;
}

export const CommandModeSelector: React.FC<CommandModeSelectorProps> = ({
  selectedMode,
  onChange,
}) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold" }}>
        SELECT DISPATCH MODE
      </span>
      <div style={{ display: "flex", gap: "8px" }}>
        <label
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "8px",
            border: `1px solid ${selectedMode === "simulate" ? "var(--accent-blue)" : "rgba(255,255,255,0.08)"}`,
            borderRadius: "6px",
            background: selectedMode === "simulate" ? "rgba(59, 130, 246, 0.1)" : "rgba(255,255,255,0.02)",
            cursor: "pointer",
            textAlign: "center",
            transition: "all 0.2s"
          }}
          onClick={() => onChange("simulate")}
        >
          <input
            type="radio"
            name="dispatch-mode-react"
            value="simulate"
            checked={selectedMode === "simulate"}
            onChange={() => {}}
            style={{ marginBottom: "4px", pointerEvents: "none" }}
          />
          <span style={{ fontSize: "10px", fontWeight: "bold", color: "#fff" }}>SIMULATE</span>
          <span style={{ fontSize: "8px", color: "var(--text-secondary)" }}>Dry-run only</span>
        </label>

        <label
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "8px",
            border: `1px solid ${selectedMode === "execute" ? "var(--accent-teal)" : "rgba(255,255,255,0.08)"}`,
            borderRadius: "6px",
            background: selectedMode === "execute" ? "rgba(20, 184, 166, 0.1)" : "rgba(255,255,255,0.02)",
            cursor: "pointer",
            textAlign: "center",
            transition: "all 0.2s"
          }}
          onClick={() => onChange("execute")}
        >
          <input
            type="radio"
            name="dispatch-mode-react"
            value="execute"
            checked={selectedMode === "execute"}
            onChange={() => {}}
            style={{ marginBottom: "4px", pointerEvents: "none" }}
          />
          <span style={{ fontSize: "10px", fontWeight: "bold", color: "var(--accent-teal)" }}>EXECUTE</span>
          <span style={{ fontSize: "8px", color: "var(--text-secondary)" }}>Run on node</span>
        </label>

        <label
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "8px",
            border: `1px solid ${selectedMode === "override" ? "#ef4444" : "rgba(255,255,255,0.08)"}`,
            borderRadius: "6px",
            background: selectedMode === "override" ? "rgba(239, 68, 68, 0.1)" : "rgba(255,255,255,0.02)",
            cursor: "pointer",
            textAlign: "center",
            transition: "all 0.2s"
          }}
          onClick={() => onChange("override")}
        >
          <input
            type="radio"
            name="dispatch-mode-react"
            value="override"
            checked={selectedMode === "override"}
            onChange={() => {}}
            style={{ marginBottom: "4px", pointerEvents: "none" }}
          />
          <span style={{ fontSize: "10px", fontWeight: "bold", color: "#ef4444" }}>OVERRIDE</span>
          <span style={{ fontSize: "8px", color: "var(--text-secondary)" }}>Force bypass</span>
        </label>
      </div>
    </div>
  );
};
