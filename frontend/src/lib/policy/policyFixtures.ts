import type { PolicyEvaluationInput } from "./policyTypes";

export const samplePolicyInputs: Record<string, PolicyEvaluationInput> = {
  allowed: {
    actor: { id: "michael.operator", name: "Michael Hoch", role: "operator" },
    command: { command_id: "cmd_001", raw_text: "run diagnostics on Dell 9440", intent: "run_diagnostic", risk: "low" },
    target: { id: "asset-dell9440", name: "Dell XPS 9440", type: "asset", trust_score: 98 },
    environment: "LOCAL",
    zta: { identity: "verified", device_posture: "verified", network_trust: "verified", session_integrity: "verified" },
    rollback: { available: false }
  },
  warned: {
    actor: { id: "michael.operator", name: "Michael Hoch", role: "operator" },
    command: { command_id: "cmd_002", raw_text: "rebalance iMac load", intent: "rebalance_workload", risk: "medium" },
    target: { id: "asset-imac", name: "Michael's iMac", type: "asset", trust_score: 85 },
    environment: "LOCAL",
    zta: { identity: "verified", device_posture: "warning", network_trust: "warning", session_integrity: "verified" },
    rollback: { available: true }
  },
  blocked: {
    actor: { id: "viewer.guest", name: "Guest Viewer", role: "viewer" },
    command: { command_id: "cmd_003", raw_text: "force rollback main cluster", intent: "rollback_deploy", risk: "high" },
    target: { id: "control-plane", name: "Control Plane L1", type: "system", trust_score: 95 },
    environment: "PROD",
    zta: { identity: "failed", device_posture: "failed", network_trust: "failed", session_integrity: "failed" },
    rollback: { available: false }
  }
};
