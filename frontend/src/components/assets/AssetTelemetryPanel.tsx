import React from "react";
import type { Asset } from "../../lib/assets/assetTypes";

interface AssetTelemetryPanelProps {
  asset: Asset;
}

export const AssetTelemetryPanel: React.FC<AssetTelemetryPanelProps> = ({ asset }) => {
  const formatPercent = (val?: number) => (val !== undefined ? `${val}%` : "—");
  
  // Stale checks (60 seconds threshold)
  const isStale = React.useMemo(() => {
    try {
      const diffMs = Date.now() - new Date(asset.state.last_updated).getTime();
      return diffMs > 60000;
    } catch {
      return false;
    }
  }, [asset.state.last_updated]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", textAlign: "left" }}>
      {isStale && (
        <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", padding: "6px 10px", borderRadius: "6px", color: "#f87171", fontSize: "10px", fontWeight: "bold" }}>
          ⚠️ TELEMETRY STALE: Last update received over 60 seconds ago.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        {/* CPU */}
        <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "10px" }}>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            CPU UTILIZATION
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ flexGrow: 1, height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
              <div
                style={{
                  width: asset.telemetry.cpu_percent !== undefined ? `${asset.telemetry.cpu_percent}%` : "0%",
                  height: "100%",
                  background: (asset.telemetry.cpu_percent || 0) > 80 ? "#ef4444" : "var(--accent-teal)",
                  borderRadius: "3px"
                }}
              />
            </div>
            <span style={{ fontSize: "11px", fontWeight: "bold", color: "#fff", fontFamily: "monospace", minWidth: "35px", textAlign: "right" }}>
              {formatPercent(asset.telemetry.cpu_percent)}
            </span>
          </div>
        </div>

        {/* RAM */}
        <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "10px" }}>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            RAM ALLOCATION
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ flexGrow: 1, height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
              <div
                style={{
                  width: asset.telemetry.ram_used_gb !== undefined && asset.telemetry.ram_total_gb 
                    ? `${(asset.telemetry.ram_used_gb / asset.telemetry.ram_total_gb) * 100}%` 
                    : "0%",
                  height: "100%",
                  background: (asset.telemetry.ram_used_gb || 0) / (asset.telemetry.ram_total_gb || 1) > 0.8 ? "#ef4444" : "var(--accent-teal)",
                  borderRadius: "3px"
                }}
              />
            </div>
            <span style={{ fontSize: "10px", fontWeight: "bold", color: "#fff", fontFamily: "monospace", minWidth: "60px", textAlign: "right" }}>
              {asset.telemetry.ram_used_gb !== undefined ? `${asset.telemetry.ram_used_gb.toFixed(1)}/${asset.telemetry.ram_total_gb}G` : "—"}
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        {/* Disk */}
        <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "10px" }}>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            STORAGE PARTITION
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ flexGrow: 1, height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
              <div
                style={{
                  width: asset.telemetry.disk_used_gb !== undefined && asset.telemetry.disk_total_gb 
                    ? `${(asset.telemetry.disk_used_gb / asset.telemetry.disk_total_gb) * 100}%` 
                    : "0%",
                  height: "100%",
                  background: "var(--accent-teal)",
                  borderRadius: "3px"
                }}
              />
            </div>
            <span style={{ fontSize: "10px", fontWeight: "bold", color: "#fff", fontFamily: "monospace", minWidth: "60px", textAlign: "right" }}>
              {asset.telemetry.disk_used_gb !== undefined ? `${asset.telemetry.disk_used_gb}/${asset.telemetry.disk_total_gb}G` : "—"}
            </span>
          </div>
        </div>

        {/* Latency */}
        <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "8px", padding: "10px" }}>
          <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
            ICMP PING LATENCY
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div style={{ flexGrow: 1, height: "6px", background: "rgba(255,255,255,0.05)", borderRadius: "3px", overflow: "hidden" }}>
              <div
                style={{
                  width: asset.telemetry.network_latency_ms !== undefined ? `${Math.min(100, (asset.telemetry.network_latency_ms / 10.0) * 100)}%` : "0%",
                  height: "100%",
                  background: asset.status === "offline" ? "#6b7280" : (asset.telemetry.network_latency_ms || 0) > 3.0 ? "#ef4444" : "var(--accent-teal)",
                  borderRadius: "3px"
                }}
              />
            </div>
            <span style={{ fontSize: "11px", fontWeight: "bold", color: asset.status === "offline" ? "#ef4444" : "#fff", fontFamily: "monospace", minWidth: "35px", textAlign: "right" }}>
              {asset.status === "offline" ? "OFFLINE" : asset.telemetry.network_latency_ms !== undefined ? `${asset.telemetry.network_latency_ms.toFixed(1)}ms` : "—"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
