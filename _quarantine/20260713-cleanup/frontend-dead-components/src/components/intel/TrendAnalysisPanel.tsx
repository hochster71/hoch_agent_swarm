import React from "react";

export const TrendAnalysisPanel: React.FC = () => {
  const trends = [
    { label: "iMac CPU load (30m)", direction: "upward", pct: "+24%", avg: "82%", color: "#ef4444" },
    { label: "Dell XPS 9440 RAM (30m)", direction: "downward", pct: "-12%", avg: "52%", color: "#10b981" },
    { label: "MacBook Neo CPU (30m)", direction: "stable", pct: "0%", avg: "64%", color: "#cbd5e1" }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", textAlign: "left" }}>
      {trends.map((t, idx) => (
        <div
          key={idx}
          style={{
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.04)",
            borderRadius: "6px",
            padding: "8px 12px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <div>
            <span style={{ fontWeight: "bold", color: "#fff" }}>{t.label}</span>
            <span style={{ display: "block", color: "var(--text-secondary)", fontSize: "9px", marginTop: "2px" }}>
              average value: {t.avg}
            </span>
          </div>
          <span style={{ color: t.color, fontWeight: "bold", fontFamily: "monospace" }}>
            {t.direction === "upward" ? "📈" : t.direction === "downward" ? "📉" : "➡️"} {t.pct}
          </span>
        </div>
      ))}
    </div>
  );
};
