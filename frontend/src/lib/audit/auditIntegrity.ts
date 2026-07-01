import type { AuditEvent } from "./auditTypes";
import { validateAuditEvents } from "./auditValidation";

export function getAuditIntegrityScore(events: AuditEvent[]): number {
  if (events.length === 0) return 100;
  const validation = validateAuditEvents(events);
  const totalChecks = events.length * 4; // Check fields, policy, evidence, confidence
  let failedChecks = 0;
  
  failedChecks += validation.invalid.length * 2.0; // Heavy penalty for malformed
  failedChecks += validation.missingPolicy.length * 1.0;
  failedChecks += validation.missingEvidence.length * 0.5;
  failedChecks += validation.missingConfidence.length * 0.5;
  
  const score = Math.max(0, 100 - (failedChecks / totalChecks) * 100);
  return Math.round(score);
}
