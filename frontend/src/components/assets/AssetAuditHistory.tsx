import React from "react";
import type { Asset } from "../../lib/assets/assetTypes";
import { useAuditStore } from "../../lib/audit/auditStore";

interface AssetAuditHistoryProps {
  asset: Asset;
}

export const AssetAuditHistory: React.FC<AssetAuditHistoryProps> = ({ asset }) => {
  const { events } = useAuditStore();

  const filteredEvents = React.useMemo(() => {
    // Filter events where target matches asset ID
    return events.filter((e) => e.target.id === asset.id);
  }, [events, asset.id]);

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return "--:--:--";
    }
  };

  if (filteredEvents.length === 0) {
    return (
      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", textAlign: "left" }}>
        No historical audit records found for this asset in the active session.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "180px", overflowY: "auto", textAlign: "left" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "9.5px", fontFamily: "monospace" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.08)", color: "var(--text-secondary)", textAlign: "left" }}>
            <th style={{ padding: "4px" }}>TIME</th>
            <th style={{ padding: "4px" }}>ACTION</th>
            <th style={{ padding: "4px" }}>ACTOR</th>
            <th style={{ padding: "4px", textAlign: "right" }}>RESULT</th>
          </tr>
        </thead>
        <tbody>
          {filteredEvents.map((evt) => {
            let resultColor = "#10b981"; // green
            if (evt.result === "failed") resultColor = "#ef4444";
            else if (evt.result === "blocked") resultColor = "#f59e0b";

            return (
              <tr key={evt.event_id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.03)", color: "#cbd5e1" }}>
                <td style={{ padding: "4px 2px", whiteSpace: "nowrap" }}>{formatTime(evt.timestamp)}</td>
                <td style={{ padding: "4px 2px", fontWeight: "bold" }}>{evt.action.type}</td>
                <td style={{ padding: "4px 2px" }}>{evt.actor.name}</td>
                <td style={{ padding: "4px 2px", textAlign: "right", color: resultColor, fontWeight: "bold" }}>
                  {evt.result.toUpperCase()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
