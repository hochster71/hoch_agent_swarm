import React, { useState, useEffect } from "react";
import type { Asset } from "../../lib/assets/assetTypes";

interface AssetRecentEventsProps {
  asset: Asset;
}

type MissionEvent = {
  ts: string;
  node_id: string;
  status: string;
  activity: string;
  icon: string;
};

export const AssetRecentEvents: React.FC<AssetRecentEventsProps> = ({ asset }) => {
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    
    // Fetch from backend mission feed
    const apiBase = typeof window !== "undefined" && (window as any).API_BASE ? (window as any).API_BASE : "";
    fetch(`${apiBase}/api/mission/feed?limit=80`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load mission logs");
        return res.json();
      })
      .then((data) => {
        const list = (data.events || []) as MissionEvent[];
        const filtered = list.filter((e) => e.node_id === asset.id).slice(0, 5);
        setEvents(filtered);
        setLoading(false);
      })
      .catch((err) => {
        console.warn("Error loading events for asset:", err);
        setError("Failed to sync mission feed.");
        setLoading(false);
      });
  }, [asset.id]);

  if (loading) {
    return <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", textAlign: "left" }}>Loading mission timeline...</div>;
  }

  if (error) {
    return <div style={{ fontSize: "11px", color: "#ef4444", textAlign: "left" }}>{error}</div>;
  }

  if (events.length === 0) {
    return <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", textAlign: "left" }}>No recent events recorded for this asset.</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px", textWrap: "wrap", textAlign: "left" }}>
      {events.map((ev, index) => {
        let borderLeftColor = "rgba(16, 185, 129, 0.5)"; // green (active)
        const stat = ev.status.toLowerCase();
        if (stat.includes("triage")) borderLeftColor = "rgba(245, 158, 11, 0.5)"; // yellow
        else if (stat.includes("heal")) borderLeftColor = "rgba(168, 85, 247, 0.5)"; // purple
        else if (stat.includes("reason")) borderLeftColor = "rgba(59, 130, 246, 0.5)"; // blue
        else if (stat.includes("deploy")) borderLeftColor = "rgba(6, 182, 212, 0.5)"; // cyan

        return (
          <div
            key={index}
            style={{
              display: "flex",
              gap: "8px",
              padding: "6px 8px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.04)",
              borderLeft: `3px solid ${borderLeftColor}`,
              borderRadius: "4px"
            }}
          >
            <span style={{ color: "var(--text-secondary)", fontFamily: "monospace", fontSize: "9px", flexShrink: 0, marginTop: "2px" }}>
              {ev.ts}
            </span>
            <div style={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
              <span style={{ fontWeight: "bold", color: "#fff", fontSize: "9.5px" }}>
                {ev.icon} {ev.status.toUpperCase()}
              </span>
              <span style={{ color: "var(--text-secondary)", fontSize: "9.5px", marginTop: "2px", lineHeight: "1.3" }}>
                {ev.activity}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
