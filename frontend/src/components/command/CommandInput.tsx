import React, { useState } from "react";
import { useCommandStore } from "../../lib/command/commandStore";

export const CommandInput: React.FC = () => {
  const [prompt, setPrompt] = useState("");
  const [taskType, setTaskType] = useState("code_generation");
  const { openPreview, setMode } = useCommandStore();

  const handlePreview = () => {
    if (!prompt.trim()) {
      alert("Please enter a task instruction.");
      return;
    }
    setMode("simulate");
    openPreview(prompt.trim());
  };

  const handleExecute = () => {
    if (!prompt.trim()) {
      alert("Please enter a task instruction.");
      return;
    }
    setMode("execute");
    openPreview(prompt.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handlePreview();
    }
  };

  // Sync state back to DOM select element so legacy window functions can read it if needed
  const handleTaskTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setTaskType(val);
    const legacySelect = document.getElementById("task-type-select") as HTMLSelectElement;
    if (legacySelect) legacySelect.value = val;
  };

  return (
    <div
      className="console-command-bar"
      style={{
        display: "flex",
        gap: "12px",
        alignItems: "center",
        background: "rgba(15, 23, 42, 0.85)",
        borderTop: "1px solid var(--border-glass)",
        padding: "12px",
        zIndex: 10,
        boxSizing: "border-box"
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontSize: "12px",
          color: "var(--accent-teal)",
          fontWeight: "bold",
          whiteSpace: "nowrap"
        }}
      >
        SWARM_CMD_INPUT &gt;
      </div>

      <select
        id="task-type-select-react"
        value={taskType}
        onChange={handleTaskTypeChange}
        style={{
          background: "rgba(0,0,0,0.4)",
          border: "1px solid var(--border-glass)",
          color: "#fff",
          padding: "6px",
          borderRadius: "6px",
          fontSize: "12px",
          cursor: "pointer"
        }}
      >
        <option value="code_generation">Code Generation Swarm</option>
        <option value="refactoring">Refactoring Swarm</option>
        <option value="unit_testing">Automated Unit Testing</option>
        <option value="general_query">General Query / Research</option>
      </select>

      <input
        type="text"
        id="prompt-input-react"
        placeholder="Enter tactical swarm instruction (e.g. rebalance workload)..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        style={{
          flexGrow: 1,
          background: "rgba(0,0,0,0.4)",
          border: "1px solid var(--border-glass)",
          color: "#fff",
          padding: "6px 12px",
          borderRadius: "6px",
          fontSize: "13px",
          fontFamily: "monospace"
        }}
      />

      <div style={{ display: "flex", gap: "6px" }}>
        <button
          className="btn btn-outline btn-sm"
          onClick={handlePreview}
          style={{
            padding: "6px 14px",
            borderColor: "var(--border-glass)",
            color: "#fff",
            fontSize: "11px",
            height: "30px",
            cursor: "pointer"
          }}
        >
          PREVIEW
        </button>
        
        <button
          className="btn btn-primary btn-sm"
          onClick={handleExecute}
          style={{
            padding: "6px 14px",
            fontSize: "11px",
            height: "30px",
            cursor: "pointer"
          }}
        >
          EXECUTE
        </button>
      </div>
    </div>
  );
};
