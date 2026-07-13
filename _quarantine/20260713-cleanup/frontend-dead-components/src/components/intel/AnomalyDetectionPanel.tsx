import React from "react";
import type { TelemetryAnomaly } from "../../lib/intel/anomalyDetection";

export const AnomalyDetectionPanel: React.FC = () => {
  const anomalies: TelemetryAnomaly[] = [
    {
      timestamp: new Date().toISOString(),
      metric: "RAM",
      nodeName: "Michael's iMac [L2]",
      value: 91,
      threshold: 80,
      details: "Linear memory buffer growth detected. Risk of out-of-memory crash."
    },
    {
      timestamp: new Date().toISOString(),
      metric: "LATENCY",
      nodeName: "Tactical Edge iPhone",
      value: 6.4,
      threshold: 5.0,
      details: "Network connection jitter exceeds military-grade tactical guidelines."
    }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", textAlign: "left" }}>
      {anomalies.map((a, idx) => (
        <div
          key={idx}
          style={{
            background: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            borderRadius: "6px",
            padding: "8px 12px",
            display: "flex",
            flexDirection: "column",
            gap: "4px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: "bold", color: "#f87171" }}>
              ⚠️ {a.metric} ANOMALY DETECTED
            </span>
            <span style={{ color: "var(--text-secondary)", fontSize: "9px" }}>
              node: {a.nodeName}
            </span>
          </div>
          <p style={{ margin: 0, color: "#cbd5e1", lineHeight: "1.3" }}>
            {a.details} (Value: <strong>{a.value}</strong> / Limit: {a.threshold})
          </p>
        </div>
      ))}
    </div>
  );
};
