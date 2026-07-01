import type { AuditEvent } from "../audit/auditTypes";

export function getEventsByCorrelationId(events: AuditEvent[], corrId: string): AuditEvent[] {
  if (!corrId) return [];
  return events.filter(e => e.correlation_id === corrId).sort((a,b) => a.timestamp.localeCompare(b.timestamp));
}

export function getEventTimespanBounds(events: AuditEvent[]): { start: string; end: string } {
  if (events.length === 0) {
    const d = new Date().toISOString();
    return { start: d, end: d };
  }
  const sorted = [...events].sort((a,b) => a.timestamp.localeCompare(b.timestamp));
  return {
    start: sorted[0].timestamp,
    end: sorted[sorted.length - 1].timestamp
  };
}
