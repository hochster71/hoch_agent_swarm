import type { AuditEvent } from "../audit/auditTypes";
import type { ReplaySession } from "./replayTypes";

export function createReplaySession(params: {
  events: AuditEvent[];
  correlationId?: string;
  targetId?: string;
  timeStart?: string;
  timeEnd?: string;
}): ReplaySession {
  const filtered = params.events
    .filter((event) => {
      if (params.correlationId && event.correlation_id !== params.correlationId) return false;
      if (params.targetId && event.target.id !== params.targetId) return false;
      if (params.timeStart && event.timestamp < params.timeStart) return false;
      if (params.timeEnd && event.timestamp > params.timeEnd) return false;
      return true;
    })
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  return {
    replay_id: `replay_${Date.now()}`,
    created_at: new Date().toISOString(),
    mode: "paused",
    filters: {
      correlation_id: params.correlationId,
      target_id: params.targetId,
      time_start: params.timeStart,
      time_end: params.timeEnd,
    },
    events: filtered,
    current_index: 0,
    current_event: filtered[0],
  };
}

export function stepReplay(session: ReplaySession, direction: "forward" | "backward"): ReplaySession {
  if (session.events.length === 0) return session;
  const delta = direction === "forward" ? 1 : -1;
  const nextIndex = Math.max(0, Math.min(session.events.length - 1, session.current_index + delta));
  return {
    ...session,
    current_index: nextIndex,
    current_event: session.events[nextIndex],
  };
}
