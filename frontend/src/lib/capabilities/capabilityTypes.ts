export type CapabilityKind =
  | "agent"
  | "skill"
  | "tool"
  | "connector"
  | "workflow"
  | "swarm";

export type CapabilityStatus =
  | "draft"
  | "testing"
  | "approved"
  | "restricted"
  | "deprecated"
  | "retired";

export type CapabilityRisk = "low" | "medium" | "high" | "critical";

export type CapabilityRecord = {
  capability_id: string;
  name: string;
  kind: CapabilityKind;
  version: string;
  owner: string;
  status: CapabilityStatus;
  risk: CapabilityRisk;
  description: string;
  tags: string[];
  permissions: {
    filesystem: boolean;
    network: boolean;
    email: boolean;
    calendar: boolean;
    browser: boolean;
    shell: boolean;
    secrets: boolean;
    external_write: boolean;
  };
  guardrails: {
    requires_human_approval: boolean;
    allowed_environments: ("LOCAL" | "DEV" | "STAGING" | "PROD")[];
    blocked_actions: string[];
    max_autonomy_level: "recommend" | "draft" | "execute_with_approval" | "execute";
  };
  lifecycle: {
    created_at: string;
    updated_at: string;
    approved_at?: string;
    deprecated_at?: string;
    retired_at?: string;
  };
  telemetry: {
    executions_30d: number;
    failure_rate_30d: number;
    avg_latency_ms: number;
    last_used_at?: string;
  };
};
