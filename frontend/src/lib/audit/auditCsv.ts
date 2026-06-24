import type { AuditEvent } from "./auditTypes";

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const stringValue = String(value);
  return `"${stringValue.replace(/"/g, '""')}"`;
}

export function auditEventsToCsv(events: AuditEvent[]): string {
  const headers = [
    "event_id",
    "correlation_id",
    "timestamp",
    "actor_id",
    "actor_name",
    "actor_type",
    "action_type",
    "summary",
    "target_type",
    "target_id",
    "target_name",
    "result",
    "severity",
    "provenance_source",
    "confidence",
    "policy_required",
    "policy_result",
    "policy_ids",
    "evidence_refs",
    "rollback_available",
    "rollback_id",
  ];

  const rows = events.map((event) => [
    event.event_id,
    event.correlation_id,
    event.timestamp,
    event.actor.id,
    event.actor.name,
    event.actor.type,
    event.action.type,
    event.action.summary,
    event.target.type,
    event.target.id,
    event.target.name ?? "",
    event.result,
    event.severity,
    event.provenance.source,
    event.provenance.confidence ?? "",
    event.policy.required ? "true" : "false",
    event.policy.result,
    event.policy.policy_ids?.join(";") ?? "",
    event.provenance.evidence_refs?.join(";") ?? "",
    event.rollback?.available ? "true" : "false",
    event.rollback?.rollback_id ?? "",
  ]);

  return [headers, ...rows]
    .map((row) => row.map(csvEscape).join(","))
    .join("\n");
}
