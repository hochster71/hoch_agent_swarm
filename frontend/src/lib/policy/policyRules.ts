export type PolicyRule = {
  rule_id: string;
  name: string;
  description: string;
  target_intent: string;
  required_role: "operator" | "admin";
  max_risk_allowed: "low" | "medium" | "high" | "critical";
  requires_rollback: boolean;
};

export const defaultPolicyRules: PolicyRule[] = [
  {
    rule_id: "RULE-REBAL-01",
    name: "Workload Rebalance Restriction",
    description: "Allows operators to redistribute tasks across nodes during resource warnings.",
    target_intent: "rebalance_workload",
    required_role: "operator",
    max_risk_allowed: "high",
    requires_rollback: true,
  },
  {
    rule_id: "RULE-ROLL-02",
    name: "Emergency Rollback Control",
    description: "Allows operators to revert containers to baseline packages.",
    target_intent: "rollback_deploy",
    required_role: "operator",
    max_risk_allowed: "high",
    requires_rollback: false,
  },
  {
    rule_id: "RULE-RESTART-03",
    name: "Container Cycle Gatekeeper",
    description: "Restarts container service nodes in case of heap warnings.",
    target_intent: "restart_agent",
    required_role: "operator",
    max_risk_allowed: "medium",
    requires_rollback: false,
  },
  {
    rule_id: "RULE-DIAG-04",
    name: "System Diagnostics Probe",
    description: "Allows read-only security probes in tactical enclaves.",
    target_intent: "run_diagnostic",
    required_role: "operator",
    max_risk_allowed: "low",
    requires_rollback: false,
  },
];
