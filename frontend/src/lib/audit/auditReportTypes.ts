import type { AuditEvent } from "./auditTypes";

export type AuditReportFormat = "json" | "csv" | "markdown";

export type AuditReportFilters = {
  time_start?: string;
  time_end?: string;
  actor_id?: string;
  actor_type?: string;
  target_id?: string;
  target_type?: string;
  severity?: string;
  result?: string;
  policy_result?: string;
  correlation_id?: string;
};

export type AuditIntegritySummary = {
  valid_event_count: number;
  invalid_event_count: number;
  missing_evidence_count: number;
  missing_policy_count: number;
  missing_confidence_count: number;
  inferred_without_confidence_count: number;
  predicted_without_confidence_count: number;
};

export type AuditReport = {
  report_id: string;
  generated_at: string;
  generated_by: {
    id: string;
    name: string;
    role?: string;
  };
  environment: string;
  filters: AuditReportFilters;
  event_count: number;
  integrity: AuditIntegritySummary;
  events: AuditEvent[];
};
