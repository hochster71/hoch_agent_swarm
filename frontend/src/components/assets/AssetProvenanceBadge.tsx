import React from "react";
import type { Asset } from "../../lib/assets/assetTypes";

interface ProvenanceBadgeProps {
  source: Asset["state"]["provenance"];
  confidence?: number;
}

export const AssetProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({ source, confidence }) => {
  let color = "#10b981"; // green (observed)
  let bg = "rgba(16, 185, 129, 0.1)";
  let border = "rgba(16, 185, 129, 0.25)";

  if (source === "inferred") {
    color = "#3b82f6"; // blue
    bg = "rgba(59, 130, 246, 0.1)";
    border = "rgba(59, 130, 246, 0.25)";
  } else if (source === "predicted") {
    color = "#a855f7"; // purple
    bg = "rgba(168, 85, 247, 0.1)";
    border = "rgba(168, 85, 247, 0.25)";
  } else if (source === "manual") {
    color = "#fbbf24"; // yellow/amber
    bg = "rgba(251, 191, 36, 0.1)";
    border = "rgba(251, 191, 36, 0.25)";
  } else if (source === "synthetic") {
    color = "#06b6d4"; // cyan
    bg = "rgba(6, 182, 212, 0.1)";
    border = "rgba(6, 182, 212, 0.25)";
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "10px",
        fontWeight: "bold",
        color,
        background: bg,
        border: `1px solid ${border}`,
        textTransform: "uppercase",
        letterSpacing: "0.5px"
      }}
    >
      {source} {confidence !== undefined && `(${confidence}%)`}
    </span>
  );
};
