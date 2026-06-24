import type { AuditEvent } from "../audit/auditTypes";
import type { IncidentSummary } from "./replayTypes";

export function buildIncidentSummary(events: AuditEvent[]): IncidentSummary {
  const sorted = [...events].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  
  const severityRank = {
    info: 0,
    low: 1,
    medium: 2,
    high: 3,
    critical: 4,
  } as const;

  const highest = sorted.reduce((max, event) => {
    return severityRank[event.severity] > severityRank[max] ? event.severity : max;
  }, "info" as AuditEvent["severity"]);

  const evidenceRefs = Array.from(
    new Set(sorted.flatMap((event) => event.provenance.evidence_refs || []))
  );

  const policyFindings = sorted
    .filter((event) => event.policy && event.policy.result !== "not_required")
    .map((event) => `${event.action.type}: policy check resolved as '${event.policy.result}'`);

  const primaryTargets = Array.from(
    new Map(
      sorted.map((event) => [
        event.target.id,
        {
          id: event.target.id,
          name: event.target.name || "Unnamed Target",
          type: event.target.type,
        },
      ])
    ).values()
  );

  const incidentId = `inc_${Date.now()}`;

  return {
    incident_id: incidentId,
    generated_at: new Date().toISOString(),
    title: `Operational incident reconstruction report (${incidentId})`,
    severity: highest === "info" ? "low" : highest,
    time_range: {
      start: sorted[0]?.timestamp ?? new Date().toISOString(),
      end: sorted[sorted.length - 1]?.timestamp ?? new Date().toISOString(),
    },
    primary_targets: primaryTargets,
    root_cause_hypothesis:
      "Telemetry anomaly triggered automated risk threshold warning. Subsequent command execution bypassed or passed ZTA policy validation.",
    timeline_summary: `Timeline contains ${sorted.length} transaction entries across ${primaryTargets.length} enclaves targets.`,
    evidence_refs: evidenceRefs,
    policy_findings: policyFindings,
    remediation_actions: [
      "Review failed or blocked actions in this timeline.",
      "Check ZTA posture telemetry logs around incident window.",
      "Confirm rollback validation status if mutations occurred."
    ],
    open_questions: [
      "Was telemetry fresh at the exact time of execution?",
      "Were credentials manually overridden by administrator operator?"
    ],
  };
}
