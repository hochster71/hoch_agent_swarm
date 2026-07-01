import React from "react";

export const ModelHealthPanel: React.FC = () => {
  const stats = [
    { label: "Evaluation Latency", val: "24ms" },
    { label: "Total Probes Evaluated", val: "1,248" },
    { label: "False Positive Rate", val: "1.4%" },
    { label: "Traceability Integrity", val: "VERIFIED" }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "11px", textAlign: "left" }}>
      {stats.map((s, idx) => (
        <div
          key={idx}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "4px 0",
            borderBottom: idx < stats.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none"
          }}
        >
          <span style={{ color: "var(--text-secondary)" }}>{s.label}</span>
          <span style={{ color: "#fff", fontWeight: "bold", fontFamily: "monospace" }}>{s.val}</span>
        </div>
      ))}
    </div>
  );
};
