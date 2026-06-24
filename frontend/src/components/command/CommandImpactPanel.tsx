import React from "react";

interface CommandImpactPanelProps {
  impact: {
    summary: string;
    estimated_duration?: string;
    expected_latency_delta?: string;
    expected_cpu_delta?: Record<string, string>;
    expected_memory_delta?: Record<string, string>;
  };
}

export const CommandImpactPanel: React.FC<CommandImpactPanelProps> = ({ impact }) => {
  const hasCpuDeltas = impact.expected_cpu_delta && Object.keys(impact.expected_cpu_delta).length > 0;
  const hasMemDeltas = impact.expected_memory_delta && Object.keys(impact.expected_memory_delta).length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold" }}>
        PREDICTED IMPACT (SIMULATED)
      </span>
      <div
        style={{
          background: "rgba(0, 0, 0, 0.3)",
          border: "1px solid rgba(255, 255, 255, 0.05)",
          borderRadius: "6px",
          padding: "8px 12px",
          display: "flex",
          flexDirection: "column",
          gap: "6px"
        }}
      >
        <div style={{ color: "#fff", fontSize: "11px", lineHeight: "1.4" }}>
          {impact.summary}
        </div>
        
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "4px", fontSize: "10.5px" }}>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Est. Duration:</span>{" "}
            <span style={{ color: "#22d3ee", fontWeight: "bold" }}>{impact.estimated_duration || "N/A"}</span>
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Latency Delta:</span>{" "}
            <span style={{ color: "#22d3ee", fontWeight: "bold" }}>{impact.expected_latency_delta || "0.0ms"}</span>
          </div>
        </div>

        {hasCpuDeltas && (
          <div style={{ borderTop: "1px solid rgba(255, 255, 255, 0.04)", paddingTop: "6px", marginTop: "4px" }}>
            <span style={{ color: "var(--text-secondary)", fontSize: "9px", display: "block", marginBottom: "4px" }}>
              CPU UTILIZATION DELTAS:
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              {Object.entries(impact.expected_cpu_delta!).map(([node, delta]) => {
                const isNegative = delta.startsWith("-");
                return (
                  <div key={node} style={{ display: "flex", justifyContent: "space-between", fontSize: "10px" }}>
                    <span style={{ color: "#cbd5e1" }}>Node {node}:</span>
                    <span style={{ color: isNegative ? "#10b981" : "#ef4444", fontWeight: "bold" }}>
                      {delta}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {hasMemDeltas && (
          <div style={{ borderTop: "1px solid rgba(255, 255, 255, 0.04)", paddingTop: "6px", marginTop: "2px" }}>
            <span style={{ color: "var(--text-secondary)", fontSize: "9px", display: "block", marginBottom: "4px" }}>
              MEMORY CAPACITY DELTAS:
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              {Object.entries(impact.expected_memory_delta!).map(([node, delta]) => {
                const isNegative = delta.startsWith("-");
                return (
                  <div key={node} style={{ display: "flex", justifyContent: "space-between", fontSize: "10px" }}>
                    <span style={{ color: "#cbd5e1" }}>Node {node}:</span>
                    <span style={{ color: isNegative ? "#10b981" : "#f59e0b", fontWeight: "bold" }}>
                      {delta}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
