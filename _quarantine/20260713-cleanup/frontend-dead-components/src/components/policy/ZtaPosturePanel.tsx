import React from "react";
import type { ZtaStatus } from "../../lib/policy/policyTypes";

type Props = {
  posture: {
    identity: ZtaStatus;
    device_posture: ZtaStatus;
    network_trust: ZtaStatus;
    session_integrity: ZtaStatus;
  };
};

export const ZtaPosturePanel: React.FC<Props> = ({ posture }) => {
  const getStatusStyle = (status: ZtaStatus) => {
    switch (status) {
      case "verified":
        return { color: "#10b981", text: "● VERIFIED", bg: "rgba(16, 185, 129, 0.08)" };
      case "warning":
        return { color: "#f59e0b", text: "▲ WARNING", bg: "rgba(245, 158, 11, 0.08)" };
      case "failed":
        return { color: "#ef4444", text: "■ FAILED", bg: "rgba(239, 68, 68, 0.08)" };
      default:
        return { color: "#6b7280", text: "◆ UNKNOWN", bg: "rgba(255,255,255,0.04)" };
    }
  };

  const pillars = [
    { label: "Identity Verification", status: posture.identity },
    { label: "Device Posture Assessment", status: posture.device_posture },
    { label: "Network Security & Trust", status: posture.network_trust },
    { label: "Session Integrity Validation", status: posture.session_integrity },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11px", textAlign: "left" }}>
      {pillars.map((pillar, idx) => {
        const style = getStatusStyle(pillar.status);
        return (
          <div
            key={idx}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: style.bg,
              border: "1px solid rgba(255,255,255,0.04)",
              padding: "8px 12px",
              borderRadius: "6px"
            }}
          >
            <span style={{ color: "#cbd5e1" }}>{pillar.label}</span>
            <span style={{ color: style.color, fontWeight: "bold", fontFamily: "monospace" }}>
              {style.text}
            </span>
          </div>
        );
      })}
    </div>
  );
};
