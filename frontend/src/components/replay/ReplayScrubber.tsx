import React from "react";
import type { ReplaySession, ReplayMode } from "../../lib/replay/replayTypes";

type Props = {
  session: ReplaySession;
  onStep: (direction: "forward" | "backward") => void;
  onScrub: (index: number) => void;
  onModeChange: (mode: ReplayMode) => void;
};

export const ReplayScrubber: React.FC<Props> = ({ session, onStep, onScrub, onModeChange }) => {
  const isPlaying = session.mode === "playing";
  const eventsCount = session.events.length;
  
  const handlePlayToggle = () => {
    onModeChange(isPlaying ? "paused" : "playing");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%", boxSizing: "border-box" }}>
      {/* Buttons Row */}
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "12px" }}>
        <button
          onClick={() => onStep("backward")}
          disabled={session.current_index === 0}
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: session.current_index === 0 ? "rgba(255,255,255,0.2)" : "#fff",
            borderRadius: "4px",
            padding: "4px 8px",
            fontSize: "11px",
            cursor: session.current_index === 0 ? "not-allowed" : "pointer"
          }}
          title="Step Backward"
        >
          ⏮️ Step
        </button>

        <button
          onClick={handlePlayToggle}
          style={{
            background: isPlaying ? "rgba(239, 68, 68, 0.2)" : "rgba(0, 229, 255, 0.15)",
            border: isPlaying ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(0, 229, 255, 0.3)",
            color: isPlaying ? "#f87171" : "#00e5ff",
            borderRadius: "50%",
            width: "36px",
            height: "36px",
            fontSize: "14px",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            justifyContent: "center",
            alignItems: "center"
          }}
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? "⏸️" : "▶️"}
        </button>

        <button
          onClick={() => onStep("forward")}
          disabled={eventsCount === 0 || session.current_index === eventsCount - 1}
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: (eventsCount === 0 || session.current_index === eventsCount - 1) ? "rgba(255,255,255,0.2)" : "#fff",
            borderRadius: "4px",
            padding: "4px 8px",
            fontSize: "11px",
            cursor: (eventsCount === 0 || session.current_index === eventsCount - 1) ? "not-allowed" : "pointer"
          }}
          title="Step Forward"
        >
          Step ⏭️
        </button>
      </div>

      {/* Slider Scrubber */}
      {eventsCount > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <input
            type="range"
            min={0}
            max={eventsCount - 1}
            value={session.current_index}
            onChange={(e) => onScrub(parseInt(e.target.value))}
            style={{
              width: "100%",
              cursor: "pointer",
              accentColor: "#00e5ff",
              background: "rgba(255,255,255,0.1)",
              height: "4px",
              borderRadius: "2px"
            }}
          />
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "9px", color: "var(--text-secondary)" }}>
            <span>Start</span>
            <span>Index: {session.current_index + 1} / {eventsCount}</span>
            <span>End</span>
          </div>
        </div>
      )}
    </div>
  );
};
