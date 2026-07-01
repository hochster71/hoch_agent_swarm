import React from "react";
import type { Asset } from "../../lib/assets/assetTypes";
import { AssetProvenanceBadge } from "./AssetProvenanceBadge";

interface AssetSummaryHeaderProps {
  asset: Asset;
}

export const AssetSummaryHeader: React.FC<AssetSummaryHeaderProps> = ({ asset }) => {
  let statusColor = "#10b981"; // green (active)
  let statusBg = "rgba(16, 185, 129, 0.15)";
  let statusBorder = "rgba(16, 185, 129, 0.3)";

  if (asset.status === "training") {
    statusColor = "#fbbf24"; // yellow
    statusBg = "rgba(251, 191, 36, 0.15)";
    statusBorder = "rgba(251, 191, 36, 0.3)";
  } else if (asset.status === "reasoning") {
    statusColor = "#3b82f6"; // blue
    statusBg = "rgba(59, 130, 246, 0.15)";
    statusBorder = "rgba(59, 130, 246, 0.3)";
  } else if (asset.status === "self_healing") {
    statusColor = "#a855f7"; // purple
    statusBg = "rgba(168, 85, 247, 0.15)";
    statusBorder = "rgba(168, 85, 247, 0.3)";
  } else if (asset.status === "degraded") {
    statusColor = "#f97316"; // orange
    statusBg = "rgba(249, 115, 22, 0.15)";
    statusBorder = "rgba(249, 115, 22, 0.3)";
  } else if (asset.status === "offline") {
    statusColor = "#ef4444"; // red
    statusBg = "rgba(239, 68, 68, 0.15)";
    statusBorder = "rgba(239, 68, 68, 0.3)";
  }

  let riskColor = "#10b981";
  if (asset.risk === "medium") riskColor = "#fbbf24";
  else if (asset.risk === "high") riskColor = "#f97316";
  else if (asset.risk === "critical") riskColor = "#ef4444";

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toTimeString().split(" ")[0];
    } catch {
      return "--:--:--";
    }
  };

  return (
    <div
      style={{
        borderBottom: "1px solid var(--border-glass)",
        paddingBottom: "12px",
        marginBottom: "14px",
        display: "flex",
        flexDirection: "column",
        gap: "8px"
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h2 className="modal-title" style={{ fontSize: "16px", fontWeight: "bold", color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
            {asset.name}
            <span
              style={{
                fontSize: "9px",
                padding: "2px 6px",
                borderRadius: "4px",
                color: statusColor,
                background: statusBg,
                border: `1px solid ${statusBorder}`,
                fontWeight: "bold",
                textTransform: "uppercase"
              }}
            >
              {asset.status.replace("_", " ")}
            </span>
          </h2>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontFamily: "monospace", display: "block", marginTop: "2px" }}>
            IP: {asset.ip_address} | {asset.device_type}
          </span>
        </div>

        <div style={{ textAlign: "right" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block", fontWeight: "bold" }}>
            RISK EXPOSURE
          </span>
          <span style={{ fontSize: "11px", fontWeight: "bold", color: riskColor, textTransform: "uppercase", display: "block", marginTop: "2px" }}>
            ● {asset.risk}
          </span>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1.5fr",
          gap: "12px",
          marginTop: "4px",
          background: "rgba(0,0,0,0.2)",
          padding: "6px 10px",
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.03)"
        }}
      >
        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "8.5px", display: "block", fontWeight: "bold" }}>
            LAST COMPLIANCE SYNC
          </span>
          <span style={{ color: "#fff", fontSize: "10px", fontFamily: "monospace", fontWeight: "bold" }}>
            {formatTime(asset.state.last_updated)}
          </span>
        </div>
        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "8.5px", display: "block", fontWeight: "bold" }}>
            CONFIDENCE METRIC
          </span>
          <span style={{ color: "#22d3ee", fontSize: "10px", fontWeight: "bold" }}>
            {asset.state.confidence !== undefined ? `${asset.state.confidence}%` : "—"}
          </span>
        </div>
        <div>
          <span style={{ color: "var(--text-secondary)", fontSize: "8.5px", display: "block", fontWeight: "bold", marginBottom: "2px" }}>
            DATA ORIGIN / LINEAGE
          </span>
          <AssetProvenanceBadge source={asset.state.provenance} />
        </div>
      </div>
    </div>
  );
};
