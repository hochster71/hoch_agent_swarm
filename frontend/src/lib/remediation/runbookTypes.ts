export type RunbookStatus =
  | "draft"
  | "validated"
  | "approved"
  | "deprecated"
  | "retired";

export type RunbookStepType =
  | "diagnostic"
  | "command"
  | "policy_check"
  | "approval"
  | "integration"
  | "verification"
  | "rollback";

export type RunbookExecutionStatus =
  | "pending"
  | "running"
  | "paused"
  | "succeeded"
  | "failed"
  | "rolled_back"
  | "cancelled";

export type Runbook = {
  runbook_id: string;
  name: string;
  version: string;
  status: RunbookStatus;
  owner: string;
  risk: "low" | "medium" | "high" | "critical";
  trigger_conditions: string[];
  steps: {
    step_id: string;
    order: number;
    type: RunbookStepType;
    title: string;
    description: string;
    command_text?: string;
    requires_approval: boolean;
    rollback_step_id?: string;
  }[];
  verification: {
    success_conditions: string[];
    timeout_seconds: number;
    evidence_refs_required: boolean;
  };
};

export type RunbookExecution = {
  execution_id: string;
  runbook_id: string;
  correlation_id: string;
  status: RunbookExecutionStatus;
  started_at: string;
  completed_at?: string;
  current_step_id?: string;
  step_results: {
    step_id: string;
    status: "pending" | "running" | "succeeded" | "failed" | "skipped";
    started_at?: string;
    completed_at?: string;
    output?: string;
    evidence_refs: string[];
  }[];
  rollback: {
    available: boolean;
    triggered: boolean;
    rollback_execution_id?: string;
  };
};
