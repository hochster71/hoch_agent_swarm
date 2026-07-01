import React from "react";
import type { Asset } from "../../lib/assets/assetTypes";
import { generateRecommendationsForAsset } from "../../lib/assets/assetRecommendations";
import { useCommandStore } from "../../lib/command/commandStore";
import { useAssetStore } from "../../lib/assets/assetStore";

interface AssetRecommendationsProps {
  asset: Asset;
}

export const AssetRecommendations: React.FC<AssetRecommendationsProps> = ({ asset }) => {
  const { openPreview, setMode } = useCommandStore();
  const { closeDrilldown } = useAssetStore();

  const recommendations = React.useMemo(() => {
    return generateRecommendationsForAsset(asset);
  }, [asset]);

  const handleAction = (rec: typeof recommendations[number]) => {
    let commandText = "";
    let mode: "simulate" | "execute" = "simulate";

    if (rec.action_type === "simulate_rebalance") {
      commandText = `rebalance workload from iMac to Dell 9440`;
      mode = "simulate";
    } else if (rec.action_type === "run_diagnostic") {
      commandText = `run diagnostic on ${asset.id}`;
      mode = "simulate";
    } else if (rec.action_type === "restart_agent") {
      commandText = `restart agent on ${asset.id}`;
      mode = "execute";
    } else if (rec.action_type === "rollback") {
      commandText = `rollback deploy on ${asset.id}`;
      mode = "execute";
    }

    if (commandText) {
      // Sync prompt input text in DOM for visual feedback if user cancels
      const legacyInput = document.getElementById("prompt-input-react") as HTMLInputElement;
      if (legacyInput) legacyInput.value = commandText;

      // Close asset detail view and trigger preview modal
      closeDrilldown();
      setMode(mode);
      openPreview(commandText);
    }
  };

  if (recommendations.length === 0) {
    return (
      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", textAlign: "left" }}>
        No operational recommendations at this time. Asset state is optimal.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", textAlign: "left" }}>
      {recommendations.map((rec) => {
        let borderLeftColor = "rgba(34, 211, 238, 0.4)"; // cyan
        if (rec.severity === "high" || rec.severity === "critical") {
          borderLeftColor = "rgba(239, 68, 68, 0.5)"; // red
        } else if (rec.severity === "medium") {
          borderLeftColor = "rgba(245, 158, 11, 0.5)"; // amber
        }

        return (
          <div
            key={rec.id}
            style={{
              padding: "8px 10px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.04)",
              borderLeft: `3px solid ${borderLeftColor}`,
              borderRadius: "6px",
              display: "flex",
              flexDirection: "column",
              gap: "6px"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "9px", color: "var(--text-secondary)", fontWeight: "bold", textTransform: "uppercase" }}>
                Severity: {rec.severity} | Confidence: {rec.confidence}%
              </span>
            </div>
            
            <p style={{ color: "#fff", fontSize: "10.5px", margin: 0, lineHeight: "1.4" }}>
              {rec.summary}
            </p>

            {rec.action_type !== "observe" && (
              <div style={{ display: "flex", gap: "6px", marginTop: "2px" }}>
                <button
                  className="btn btn-primary btn-xs"
                  onClick={() => handleAction(rec)}
                  style={{
                    padding: "3px 10px",
                    fontSize: "9px",
                    height: "22px",
                    background: rec.action_type === "simulate_rebalance" ? "rgba(59, 130, 246, 0.15)" : "rgba(20, 184, 166, 0.15)",
                    border: rec.action_type === "simulate_rebalance" ? "1px solid rgba(59, 130, 246, 0.3)" : "1px solid rgba(20, 184, 166, 0.3)",
                    color: rec.action_type === "simulate_rebalance" ? "#3b82f6" : "var(--accent-teal)",
                    fontWeight: "bold",
                    cursor: "pointer"
                  }}
                >
                  {rec.action_type === "simulate_rebalance" ? "SIMULATE" : "TRIGGER ACTION"}
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
