import type { AuditEvent } from "../audit/auditTypes";

export type ReplayMode = "live" | "paused" | "playing" | "step";

export type ReplaySession = {
  replay_id: string;
  created_at: string;
  mode: ReplayMode;
  filters: {
    time_start?: string;
    time_end?: string;
    correlation_id?: string;
    target_id?: string;
    actor_id?: string;
    severity?: string;
  };
  events: AuditEvent[];
  current_index: number;
  current_event?: AuditEvent;
};

export type IncidentSummary = {
  incident_id: string;
  generated_at: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  time_range: {
    start: string;
    end: string;
  };
  primary_targets: {
    id: string;
    name?: string;
    type: string;
  }[];
  root_cause_hypothesis: string;
  timeline_summary: string;
  evidence_refs: string[];
  policy_findings: string[];
  remediation_actions: string[];
  open_questions: string[];
};
