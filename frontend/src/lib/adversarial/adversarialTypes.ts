export type ScenarioKind =
  | "prompt_injection"
  | "policy_bypass"
  | "approval_abuse"
  | "telemetry_failure"
  | "integration_failure"
  | "backend_sync_failure"
  | "ledger_tamper"
  | "model_drift"
  | "resource_exhaustion";

export type ScenarioSeverity = "low" | "medium" | "high" | "critical";

export type ScenarioResult = "passed" | "failed" | "warning" | "not_run";

export type AdversarialScenario = {
  scenario_id: string;
  name: string;
  kind: ScenarioKind;
  severity: ScenarioSeverity;
  description: string;
  setup: {
    target_system_id?: string;
    target_asset_id?: string;
    injected_faults: string[];
    input_payload?: string;
  };
  assertions: {
    assertion_id: string;
    description: string;
    expected: string;
  }[];
  result?: {
    status: ScenarioResult;
    started_at: string;
    completed_at: string;
    findings: string[];
    failed_assertions: string[];
    evidence_refs: string[];
  };
};
