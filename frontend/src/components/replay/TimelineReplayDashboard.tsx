import React from "react";
import { useAuditStore } from "../../lib/audit/auditStore";
import { createReplaySession, stepReplay } from "../../lib/replay/replayEngine";
import { selectActiveEventsBeforeCurrent } from "../../lib/replay/replaySelectors";
import { buildIncidentSummary } from "../../lib/replay/incidentBuilder";
import { sampleIncidentTimeline } from "../../lib/replay/replayFixtures";
import { ReplayScrubber } from "./ReplayScrubber";
import { ReplayEventLane } from "./ReplayEventLane";
import { ReplayEventCard } from "./ReplayEventCard";
import { CorrelationRunGraph } from "./CorrelationRunGraph";
import { IncidentSummaryPanel } from "./IncidentSummaryPanel";
import { EvidenceChainViewer } from "./EvidenceChainViewer";
import type { ReplaySession, ReplayMode } from "../../lib/replay/replayTypes";

export const TimelineReplayDashboard: React.FC = () => {
  const auditState = useAuditStore();

  // Combine store audit events and fixture incident events
  const allEvents = React.useMemo(() => {
    const combined = [...auditState.events];
    // Add fixtures if not already present
    sampleIncidentTimeline.forEach(fixture => {
      if (!combined.some(e => e.event_id === fixture.event_id)) {
        combined.push(fixture);
      }
    });
    return combined;
  }, [auditState.events]);

  const [session, setSession] = React.useState<ReplaySession>(() => {
    return createReplaySession({
      events: allEvents,
      correlationId: "corr_incident_rebalance",
    });
  });

  // Keep session synchronized with events updates
  React.useEffect(() => {
    setSession(prev => {
      const newSession = createReplaySession({
        events: allEvents,
        correlationId: prev.filters.correlation_id,
        targetId: prev.filters.target_id,
        timeStart: prev.filters.time_start,
        time_end: prev.filters.time_end
      } as any);
      // Retain current index safely
      newSession.current_index = Math.min(newSession.events.length - 1, Math.max(0, prev.current_index));
      newSession.current_event = newSession.events[newSession.current_index];
      return newSession;
    });
  }, [allEvents]);

  // Scrubber timer loop
  React.useEffect(() => {
    let timer: any = null;
    if (session.mode === "playing") {
      timer = setInterval(() => {
        setSession(prev => {
          if (prev.current_index >= prev.events.length - 1) {
            return { ...prev, mode: "paused" };
          }
          return stepReplay(prev, "forward");
        });
      }, 2000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [session.mode]);

  const handleStep = (direction: "forward" | "backward") => {
    setSession(prev => stepReplay(prev, direction));
  };

  const handleScrub = (index: number) => {
    setSession(prev => {
      const idx = Math.min(prev.events.length - 1, Math.max(0, index));
      return {
        ...prev,
        current_index: idx,
        current_event: prev.events[idx],
        mode: "paused"
      };
    });
  };

  const handleModeChange = (mode: ReplayMode) => {
    setSession(prev => ({ ...prev, mode }));
  };

  const handleFilterCorrelation = (corrId: string) => {
    setSession(() => createReplaySession({
      events: allEvents,
      correlationId: corrId || undefined
    }));
  };

  const activeTimelineEvents = React.useMemo(() => {
    return selectActiveEventsBeforeCurrent(session);
  }, [session]);

  const incidentSummary = React.useMemo(() => {
    return buildIncidentSummary(session.events);
  }, [session.events]);

  return (
    <div style={{ padding: "20px", display: "flex", gap: "16px", height: "100%", boxSizing: "border-box" }}>
      
      {/* Left Column: Filters and Scrubber timeline info */}
      <div style={{ width: "240px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "16px", textAlign: "left" }}>
        
        {/* Playback Control Card */}
        <div className="card" style={{ padding: "16px" }}>
          <h3 className="card-title" style={{ fontSize: "11px", margin: 0, color: "#818cf8" }}>REPLAY SCRUBBER</h3>
          <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
            
            {/* Scrubber component */}
            <ReplayScrubber
              session={session}
              onStep={handleStep}
              onScrub={handleScrub}
              onModeChange={handleModeChange}
            />

            <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
              Selected Run: <strong style={{ color: "#fff" }}>{session.events.length} events</strong>
            </div>
          </div>
        </div>

        {/* Replay Filters */}
        <div className="card" style={{ padding: "16px", flexGrow: 1 }}>
          <h3 className="card-title" style={{ fontSize: "11px", margin: 0 }}>TIMELINE FILTERS</h3>
          <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "12px", fontSize: "11px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ color: "var(--text-secondary)" }}>Correlation ID</label>
              <select
                value={session.filters.correlation_id || ""}
                onChange={(e) => handleFilterCorrelation(e.target.value)}
                style={{
                  background: "rgba(0,0,0,0.3)",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "4px",
                  padding: "4px 8px",
                  color: "#fff",
                  outline: "none"
                }}
              >
                <option value="corr_incident_rebalance">corr_incident_rebalance</option>
                <option value="corr_qa_test_123">corr_qa_test_123</option>
                <option value="">All Logs</option>
              </select>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ color: "var(--text-secondary)" }}>Incident Level</label>
              <span style={{ fontSize: "12px", fontWeight: "bold", color: "#f87171" }}>
                ⚠️ HIGH SEVERITY
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ color: "var(--text-secondary)" }}>Time Slice</label>
              <span style={{ fontFamily: "monospace", color: "#38bdf8", fontSize: "10px" }}>
                10:30:00 - 10:31:10
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Center Column: Event Scrubber list & details card */}
      <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: "16px", minWidth: 0 }}>
        
        {/* Scrubber Event Timeline visualization */}
        <div className="card" style={{ padding: "16px" }}>
          <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "12px", textAlign: "left" }}>
            CHRONOLOGICAL EVENT scrub PATH
          </h2>
          <ReplayEventLane session={session} onSelectIndex={handleScrub} />
        </div>

        {/* Two Columns for Detail Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "16px", flexGrow: 1, minHeight: 0 }}>
          
          {/* Left: Active Event details card */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="card" style={{ padding: "16px", flexGrow: 1, overflowY: "auto" }}>
              <h3 className="card-title" style={{ fontSize: "12px", marginBottom: "12px", textAlign: "left" }}>
                CURRENT SCRUB EVENT
              </h3>
              <ReplayEventCard event={session.current_event} />
            </div>
          </div>

          {/* Right: Causality graph and Evidence refs */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="card" style={{ padding: "16px", flexGrow: 1, overflowY: "auto" }}>
              <h3 className="card-title" style={{ fontSize: "12px", marginBottom: "12px", textAlign: "left" }}>
                CAUSAL RECONSTRUCTION EVIDENCE
              </h3>
              {session.current_event ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <EvidenceChainViewer event={session.current_event} />
                  <CorrelationRunGraph events={activeTimelineEvents} />
                </div>
              ) : (
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic" }}>
                  No active event selected.
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Right Column: Incident Reconstruction Panel */}
      <div style={{ width: "280px", flexShrink: 0, display: "flex", flexDirection: "column", gap: "16px" }}>
        <div className="card" style={{ padding: "16px", height: "100%", display: "flex", flexDirection: "column", overflowY: "auto" }}>
          <IncidentSummaryPanel summary={incidentSummary} events={session.events} />
        </div>
      </div>

    </div>
  );
};
