import React from "react";
import type { AuditEvent } from "../../lib/audit/auditTypes";
import { buildCausalGraph } from "../../lib/replay/causalGraph";

type Props = {
  events: AuditEvent[];
};

export const CorrelationRunGraph: React.FC<Props> = ({ events }) => {
  const graph = React.useMemo(() => buildCausalGraph(events), [events]);

  const getEventStyle = (label: string, result: string) => {
    const isError = result === "failed" || result === "blocked";
    switch (label) {
      case "TELEMETRY_UPDATED":
        return { icon: "📈", border: "1px solid rgba(245, 158, 11, 0.3)", color: "#f59e0b" };
      case "AI_RECOMMENDATION_GENERATED":
        return { icon: "🧠", border: "1px solid rgba(129, 140, 248, 0.3)", color: "#818cf8" };
      case "COMMAND_PREVIEWED":
        return { icon: "🔍", border: "1px solid rgba(0, 229, 255, 0.3)", color: "#00e5ff" };
      case "COMMAND_EXECUTED":
        return { icon: "🚀", border: isError ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(16, 185, 129, 0.3)", color: isError ? "#ef4444" : "#10b981" };
      default:
        return { icon: "🔹", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", textAlign: "left", fontSize: "11px" }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold" }}>
        CAUSAL DEPENDENCY LINK FLOW
      </span>
      {graph.nodes.length === 0 ? (
        <span style={{ fontStyle: "italic", color: "var(--text-secondary)" }}>Awaiting transaction events...</span>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {graph.nodes.map((node, idx) => {
            const style = getEventStyle(node.label, node.result);
            return (
              <div key={node.id} style={{ display: "flex", alignItems: "center" }}>
                {idx > 0 && (
                  <div
                    style={{
                      width: "12px",
                      height: "12px",
                      borderLeft: "1px dashed rgba(255,255,255,0.2)",
                      marginLeft: "8px",
                      marginRight: "8px"
                    }}
                  />
                )}
                <div
                  style={{
                    background: "rgba(0,0,0,0.25)",
                    border: style.border,
                    borderRadius: "6px",
                    padding: "6px 10px",
                    color: style.color,
                    fontFamily: "monospace",
                    fontSize: "9px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    width: "100%"
                  }}
                >
                  <span>{style.icon}</span>
                  <span style={{ fontWeight: "bold" }}>{node.label}</span>
                  <span style={{ flexGrow: 1 }} />
                  <span style={{ color: "var(--text-secondary)", fontSize: "8px" }}>
                    {new Date(node.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
