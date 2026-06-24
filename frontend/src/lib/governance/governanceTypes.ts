export type AiSystemType =
  | "model"
  | "agent"
  | "swarm"
  | "tool"
  | "workflow"
  | "integration";

export type AiRiskTier = "low" | "medium" | "high" | "critical";

export type GovernanceStatus =
  | "registered"
  | "under_review"
  | "approved"
  | "restricted"
  | "retired";

export type ControlStatus =
  | "implemented"
  | "partial"
  | "missing"
  | "not_applicable";

export type AiSystemRecord = {
  system_id: string;
  name: string;
  type: AiSystemType;
  owner: string;
  description: string;
  status: GovernanceStatus;
  risk_tier: AiRiskTier;
  capabilities: string[];
  data_access: {
    classification: "public" | "internal" | "confidential" | "restricted";
    pii_access: boolean;
    secret_access: boolean;
  };
  autonomy: {
    can_recommend: boolean;
    can_execute: boolean;
    requires_human_approval: boolean;
    max_execution_scope: string;
  };
  controls: {
    control_id: string;
    framework: "NIST_AI_RMF" | "NIST_800_53" | "OWASP_SAMM" | "CUSTOM";
    status: ControlStatus;
    evidence_refs: string[];
  }[];
  review: {
    reviewed_at?: string;
    reviewed_by?: string;
    next_review_due?: string;
  };
};
