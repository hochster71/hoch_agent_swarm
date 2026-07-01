import type { AuditEvent } from "./auditTypes";
import type { AuditReportFilters } from "./auditReportTypes";

export function filterAuditEvents(
  events: AuditEvent[],
  filters: AuditReportFilters
): AuditEvent[] {
  return events.filter((event) => {
    if (filters.time_start && event.timestamp < filters.time_start) return false;
    if (filters.time_end && event.timestamp > filters.time_end) return false;
    if (filters.actor_id && event.actor.id !== filters.actor_id) return false;
    if (filters.actor_type && event.actor.type !== filters.actor_type) return false;
    if (filters.target_id && event.target.id !== filters.target_id) return false;
    if (filters.target_type && event.target.type !== filters.target_type) return false;
    if (filters.severity && event.severity !== filters.severity) return false;
    if (filters.result && event.result !== filters.result) return false;
    if (filters.policy_result && event.policy?.result !== filters.policy_result) return false;
    if (filters.correlation_id && event.correlation_id !== filters.correlation_id) return false;
    return true;
  });
}
