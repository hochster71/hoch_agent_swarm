export type PolicyDecision = "allow" | "warn" | "block";
export type Environment = "LOCAL" | "DEV" | "STAGING" | "PROD";
export type ZtaStatus = "verified" | "warning" | "failed" | "unknown";

export type PolicyEvaluationInput = {
  actor: {
    id: string;
    name: string;
    role: "viewer" | "operator" | "admin" | "approver";
  };
  command: {
    command_id: string;
    raw_text: string;
    intent: string;
    risk: "low" | "medium" | "high" | "critical";
  };
  target: {
    id: string;
    name: string;
    type: "asset" | "swarm" | "task" | "system";
    trust_score?: number;
  };
  environment: Environment;
  zta: {
    identity: ZtaStatus;
    device_posture: ZtaStatus;
    network_trust: ZtaStatus;
    session_integrity: ZtaStatus;
  };
  rollback: {
    available: boolean;
  };
};

export type PolicyEvaluationResult = {
  decision: PolicyDecision;
  score: number;
  passed: string[];
  warnings: string[];
  blockers: string[];
  approval_required: boolean;
  approval_reason?: string;
  override_allowed: boolean;
  override_reason?: string;
  evaluated_at: string;
};
