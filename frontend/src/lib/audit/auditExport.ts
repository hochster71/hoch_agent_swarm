import type { AuditEvent } from "./auditTypes";
import type { AuditReport, AuditReportFilters } from "./auditReportTypes";
import { validateAuditEvents } from "./auditValidation";

export function buildAuditReport(params: {
  events: AuditEvent[];
  filters?: AuditReportFilters;
  environment?: string;
}): AuditReport {
  const validation = validateAuditEvents(params.events);
  return {
    report_id: `audit_${new Date().toISOString().replace(/[:.]/g, "-")}`,
    generated_at: new Date().toISOString(),
    generated_by: {
      id: "michael.hoch",
      name: "Michael Hoch",
      role: "Operator",
    },
    environment: params.environment ?? "LOCAL",
    filters: params.filters ?? {},
    event_count: params.events.length,
    integrity: {
      valid_event_count: validation.valid.length,
      invalid_event_count: validation.invalid.length,
      missing_evidence_count: validation.missingEvidence.length,
      missing_policy_count: validation.missingPolicy.length,
      missing_confidence_count: validation.missingConfidence.length,
      inferred_without_confidence_count: validation.inferredWithoutConfidence.length,
      predicted_without_confidence_count: validation.predictedWithoutConfidence.length,
    },
    events: params.events,
  };
}

export function downloadJsonAudit(events: AuditEvent[]): void {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(events, null, 2));
  const downloadAnchor = document.createElement("a");
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `swarm_audit_${new Date().toISOString()}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}
