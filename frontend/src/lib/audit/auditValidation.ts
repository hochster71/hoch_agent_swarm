import type { AuditEvent } from "./auditTypes";

export type AuditValidationResult = {
  valid: AuditEvent[];
  invalid: {
    event: AuditEvent;
    reasons: string[];
  }[];
  missingEvidence: AuditEvent[];
  missingPolicy: AuditEvent[];
  missingConfidence: AuditEvent[];
  inferredWithoutConfidence: AuditEvent[];
  predictedWithoutConfidence: AuditEvent[];
};

export function validateAuditEvent(event: AuditEvent): string[] {
  const errors: string[] = [];
  if (!event.event_id) errors.push("Missing event_id");
  if (!event.correlation_id) errors.push("Missing correlation_id");
  if (!event.timestamp) errors.push("Missing timestamp");
  if (!event.actor?.id) errors.push("Missing actor.id");
  if (!event.actor?.name) errors.push("Missing actor.name");
  if (!event.actor?.type) errors.push("Missing actor.type");
  if (!event.action?.type) errors.push("Missing action.type");
  if (!event.action?.summary) errors.push("Missing action.summary");
  if (!event.target?.type) errors.push("Missing target.type");
  if (!event.target?.id) errors.push("Missing target.id");
  if (!event.result) errors.push("Missing result");
  if (!event.severity) errors.push("Missing severity");
  if (!event.provenance?.source) errors.push("Missing provenance.source");
  if (!event.provenance?.evidence_refs) {
    errors.push("Missing provenance.evidence_refs");
  }
  if (!event.policy) errors.push("Missing policy");
  if (event.policy && !event.policy.result) errors.push("Missing policy.result");
  return errors;
}

export function validateAuditEvents(events: AuditEvent[]): AuditValidationResult {
  const invalid = events
    .map((event) => ({
      event,
      reasons: validateAuditEvent(event),
    }))
    .filter((item) => item.reasons.length > 0);

  const invalidIds = new Set(invalid.map((item) => item.event.event_id));
  
  const inferredWithoutConfidence = events.filter(
    (event) =>
      event.provenance.source === "inferred" &&
      event.provenance.confidence === undefined
  );
  
  const predictedWithoutConfidence = events.filter(
    (event) =>
      event.provenance.source === "predicted" &&
      event.provenance.confidence === undefined
  );

  return {
    valid: events.filter((event) => !invalidIds.has(event.event_id)),
    invalid,
    missingEvidence: events.filter(
      (event) => !event.provenance.evidence_refs || event.provenance.evidence_refs.length === 0
    ),
    missingPolicy: events.filter((event) => !event.policy),
    missingConfidence: [...inferredWithoutConfidence, ...predictedWithoutConfidence],
    inferredWithoutConfidence,
    predictedWithoutConfidence,
  };
}
