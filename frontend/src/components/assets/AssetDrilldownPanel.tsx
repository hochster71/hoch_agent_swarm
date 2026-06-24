import React, { useState } from "react";
import { useAssetStore } from "../../lib/assets/assetStore";
import { useAuditStore } from "../../lib/audit/auditStore";
import { getSelectedAsset } from "../../lib/assets/assetSelectors";
import { AssetSummaryHeader } from "./AssetSummaryHeader";
import { AssetTelemetryPanel } from "./AssetTelemetryPanel";
import { AssetRecentEvents } from "./AssetRecentEvents";
import { AssetRecommendations } from "./AssetRecommendations";
import { AssetEvidencePanel } from "./AssetEvidencePanel";
import { AssetAuditHistory } from "./AssetAuditHistory";
import { X } from "lucide-react";

export const AssetDrilldownPanel: React.FC = () => {
  const { assets, selectedAssetId, isDrilldownOpen, closeDrilldown } = useAssetStore();
  const { openDrawer } = useAuditStore();
  const [activeTab, setActiveTab] = useState<"overview" | "telemetry" | "events" | "swarms" | "recommendations" | "audit">("overview");

  const asset = React.useMemo(() => {
    return getSelectedAsset(assets, selectedAssetId);
  }, [assets, selectedAssetId]);

  if (!isDrilldownOpen || !asset) return null;

  const handleClose = () => {
    closeDrilldown();
  };

  const handleOpenAuditDrawer = () => {
    closeDrilldown();
    openDrawer();
  };

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "telemetry", label: "Telemetry" },
    { id: "events", label: "Events" },
    { id: "swarms", label: "Active Swarms" },
    { id: "recommendations", label: "Recommendations" },
    { id: "audit", label: "Audit & Evidence" }
  ] as const;

  return (
    <div className="modal-overlay" style={{ zIndex: 999, display: "flex" }}>
      <div
        className="modal-content card"
        style={{
          maxWidth: "600px",
          width: "90%",
          padding: "20px",
          background: "rgba(10, 15, 28, 0.96)",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--border-glass)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          color: "#fff",
          display: "flex",
          flexDirection: "column",
          maxHeight: "85vh"
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <span style={{ fontSize: "9px", color: "var(--accent-teal)", fontWeight: "bold", letterSpacing: "1px" }}>
            SWARM ASSET DRILLDOWN PANEL
          </span>
          <button
            className="icon-btn close-btn"
            onClick={handleClose}
            aria-label="Close panel"
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)" }}
          >
            <X style={{ width: "16px", height: "16px" }} />
          </button>
        </div>

        {/* Dynamic Summary */}
        <AssetSummaryHeader asset={asset} />

        {/* Navigation Tabs */}
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            marginBottom: "14px",
            gap: "8px",
            overflowX: "auto"
          }}
        >
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: "none",
                border: "none",
                borderBottom: activeTab === tab.id ? "2px solid var(--accent-teal)" : "2px solid transparent",
                color: activeTab === tab.id ? "var(--accent-teal)" : "var(--text-secondary)",
                padding: "6px 12px",
                fontSize: "11px",
                fontWeight: "bold",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.2s"
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Body */}
        <div style={{ flexGrow: 1, overflowY: "auto", paddingRight: "4px", minHeight: "220px" }}>
          {activeTab === "overview" && (
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px", textAlign: "left" }}>
              <div>
                <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold", display: "block", marginBottom: "6px" }}>
                  STATE SUMMARY
                </span>
                <p style={{ color: "#fff", fontSize: "11px", lineHeight: "1.4", margin: 0 }}>
                  {asset.state.summary}
                </p>

                {/* Mini memory sparkline trend mock graph */}
                <div style={{ marginTop: "12px" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "8.5px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
                    30-MINUTES RAM CONSUMPTION TREND
                  </span>
                  <div style={{ display: "flex", alignItems: "flex-end", height: "45px", gap: "4px", background: "rgba(0,0,0,0.25)", padding: "4px 8px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.03)" }}>
                    {[35, 42, 48, 54, 52, 60, 68, 72, 75, 84, 82, 85].map((val, idx) => (
                      <div
                        key={idx}
                        style={{
                          flex: 1,
                          height: `${val}%`,
                          background: val > 80 ? "rgba(239, 68, 68, 0.6)" : "rgba(34, 211, 238, 0.4)",
                          borderRadius: "1px"
                        }}
                        title={`${val}% Usage`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold", display: "block" }}>
                  OPERATIONAL OVERVIEW
                </span>
                
                <div style={{ background: "rgba(0,0,0,0.15)", border: "1px solid rgba(255,255,255,0.03)", padding: "8px 10px", borderRadius: "6px" }}>
                  <span style={{ fontSize: "8.5px", color: "var(--text-secondary)", display: "block", fontWeight: "bold" }}>
                    RECOMMENDED ACTION
                  </span>
                  <p style={{ fontSize: "10px", margin: "4px 0", color: "#fbbf24", fontWeight: "bold" }}>
                    {asset.status === "training" ? "Workload rebalance advised." : asset.status === "offline" ? "Diagnose ssh connectivity." : "Observe system vitals."}
                  </p>
                </div>

                {/* Provenance Legend */}
                <div style={{ background: "rgba(0,0,0,0.15)", border: "1px solid rgba(255,255,255,0.03)", padding: "8px 10px", borderRadius: "6px", fontSize: "8.5px" }}>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontWeight: "bold", marginBottom: "4px" }}>
                    PROVENANCE LEGEND
                  </span>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px", color: "var(--text-secondary)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} />
                      <span>Observed (Direct)</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#3b82f6" }} />
                      <span>Inferred (ML)</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#a855f7" }} />
                      <span>Predicted (Model)</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#fbbf24" }} />
                      <span>Manual (Operator)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "telemetry" && (
            <AssetTelemetryPanel asset={asset} />
          )}

          {activeTab === "events" && (
            <div>
              <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold", display: "block", marginBottom: "6px", textAlign: "left" }}>
                CHRONOLOGICAL MISSION LOGS
              </span>
              <AssetRecentEvents asset={asset} />
            </div>
          )}

          {activeTab === "swarms" && (
            <div style={{ textAlign: "left" }}>
              <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", fontWeight: "bold", display: "block", marginBottom: "8px" }}>
                DEPLOYED AGENT CONTAINERS ({asset.active_swarms.length})
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {asset.active_swarms.map((sw, idx) => {
                  const isGordy = sw.name.toUpperCase().includes("GORDY");
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: "8px 10px",
                        background: isGordy ? "rgba(59, 130, 246, 0.08)" : "rgba(255,255,255,0.02)",
                        border: `1px solid ${isGordy ? "rgba(59, 130, 246, 0.2)" : "rgba(255,255,255,0.05)"}`,
                        borderRadius: "6px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center"
                      }}
                    >
                      <div>
                        <span style={{ fontWeight: "bold", color: "#fff", fontSize: "10.5px" }}>{sw.name}</span>
                        <span style={{ color: "var(--text-secondary)", fontSize: "9px", marginLeft: "8px" }}>
                          ({sw.role || "Worker"})
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: "8.5px",
                          color: isGordy ? "var(--accent-blue)" : "var(--accent-teal)",
                          background: isGordy ? "rgba(59, 130, 246, 0.15)" : "rgba(20, 184, 166, 0.15)",
                          border: `1px solid ${isGordy ? "rgba(59, 130, 246, 0.3)" : "rgba(20, 184, 166, 0.3)"}`,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          fontWeight: "bold",
                          textTransform: "uppercase"
                        }}
                      >
                        {isGordy ? "Gordy Agent" : "Docker Swarm"}
                      </span>
                    </div>
                  );
                })}
                {asset.active_swarms.length === 0 && (
                  <p style={{ color: "var(--text-secondary)", fontSize: "11px", fontStyle: "italic" }}>
                    No active agent containers deployed on this node.
                  </p>
                )}
              </div>
            </div>
          )}

          {activeTab === "recommendations" && (
            <AssetRecommendations asset={asset} />
          )}

          {activeTab === "audit" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <AssetEvidencePanel asset={asset} />
              <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "10px" }}>
                <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "6px", textAlign: "left" }}>
                  ASSET AUDIT HISTORICAL LOGS
                </span>
                <AssetAuditHistory asset={asset} />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
            paddingTop: "12px",
            marginTop: "14px",
            display: "flex",
            justifyContent: "space-between",
            gap: "10px"
          }}
        >
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className="btn btn-outline"
              onClick={handleOpenAuditDrawer}
              style={{ padding: "6px 12px", fontSize: "10.5px", height: "30px", cursor: "pointer" }}
            >
              VIEW AUDIT
            </button>
            <button
              className="btn btn-outline"
              onClick={() => setActiveTab("audit")}
              style={{ padding: "6px 12px", fontSize: "10.5px", height: "30px", cursor: "pointer" }}
            >
              VIEW EVIDENCE
            </button>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleClose}
            style={{ padding: "6px 20px", fontSize: "10.5px", height: "30px", cursor: "pointer" }}
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
