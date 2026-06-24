import type { ReplaySession } from "./replayTypes";
import type { AuditEvent } from "../audit/auditTypes";

export function selectActiveEventsBeforeCurrent(session: ReplaySession): AuditEvent[] {
  if (session.events.length === 0) return [];
  return session.events.slice(0, session.current_index + 1);
}

export function selectCausalChain(events: AuditEvent[], correlationId?: string): AuditEvent[] {
  if (!correlationId) return [];
  return events.filter(e => e.correlation_id === correlationId).sort((a,b) => a.timestamp.localeCompare(b.timestamp));
}
