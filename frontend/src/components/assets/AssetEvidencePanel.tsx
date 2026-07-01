import React from "react";
import type { Asset } from "../../lib/assets/assetTypes";

interface AssetEvidencePanelProps {
  asset: Asset;
}

export const AssetEvidencePanel: React.FC<AssetEvidencePanelProps> = ({ asset }) => {
  // Determine affected enclave
  let enclaveName = "SIPRNET (TACTICAL SECURE COMPUTE)";
  let enclaveDesc = "Classified computing segment for tactical agent operations and automated code engineering.";
  let enclaveColor = "var(--accent-orange)";
  
  if (asset.id === "L1") {
    enclaveName = "NIPRNET (CORE SERVICES)";
    enclaveDesc = "Unclassified operations hub for master coordination, external telemetry, and socket metrics routing.";
    enclaveColor = "var(--accent-teal)";
  } else if (asset.id === "IPAD" || asset.id === "IPHONE") {
    enclaveName = "JWICS (MOBILE EDGE)";
    enclaveDesc = "Top Secret mobile edge operators command network for remote telemetry and execution authorization.";
    enclaveColor = "#a855f7"; // purple
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", textAlign: "left" }}>
      {/* Evidence references */}
      <div>
        <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
          TELEMETRY EVIDENCE TRACKING
        </span>
        <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.04)", borderRadius: "6px", padding: "8px 10px" }}>
          {asset.state.evidence_refs.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: "16px", color: "#fff", fontSize: "10px", lineHeight: "1.4" }}>
              {asset.state.evidence_refs.map((ref, idx) => (
                <li key={idx} style={{ marginBottom: "2px" }}>
                  <code>{ref}</code>
                </li>
              ))}
            </ul>
          ) : (
            <span style={{ color: "var(--text-secondary)", fontSize: "10px", fontStyle: "italic" }}>
              No backing telemetry references required.
            </span>
          )}
        </div>
      </div>

      {/* ZTA Network Enclave */}
      <div>
        <span style={{ color: "var(--text-secondary)", fontSize: "9px", fontWeight: "bold", display: "block", marginBottom: "4px" }}>
          SECURE NETWORK SEGMENTATION (ZTA)
        </span>
        <div
          style={{
            background: "rgba(0,0,0,0.2)",
            border: `1px solid ${enclaveColor}`,
            borderLeft: `3px solid ${enclaveColor}`,
            borderRadius: "6px",
            padding: "8px 10px"
          }}
        >
          <span style={{ color: enclaveColor, fontWeight: "bold", fontSize: "10px", display: "block" }}>
            {enclaveName}
          </span>
          <p style={{ color: "var(--text-secondary)", fontSize: "9.5px", margin: "4px 0 0 0", lineHeight: "1.3" }}>
            {enclaveDesc}
          </p>
        </div>
      </div>
    </div>
  );
};
