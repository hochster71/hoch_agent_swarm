import type { AuditEvent } from "./auditTypes";

export const qaValidEvents: AuditEvent[] = [
  {
    event_id: "evt_valid_001",
    correlation_id: "corr_qa_test_123",
    timestamp: "2026-06-24T10:00:00Z",
    actor: {
      id: "operator.michael",
      name: "Michael Hoch",
      type: "human",
      role: "Operator",
    },
    action: {
      type: "COMMAND_EXECUTED",
      summary: "Simulated task rebalancing execution on XPS 9440.",
      command_text: "rebalance iMac Dell 9440",
    },
    target: {
      type: "asset",
      id: "asset-dell9440",
      name: "Dell XPS 9440",
    },
    result: "success",
    severity: "info",
    provenance: {
      source: "manual",
      evidence_refs: ["rebalance_command_input", "user_confirmation"],
    },
    policy: {
      required: true,
      result: "passed",
      policy_ids: ["POL-SEC-01", "POL-RES-02"],
      explanation: "Actor possesses active executive credentials and ZTA posture is valid.",
    },
  },
];

export const qaInvalidEvents: AuditEvent[] = [
  {
    event_id: "", // Missing event_id
    correlation_id: "corr_qa_test_999",
    timestamp: "2026-06-24T10:05:00Z",
    actor: {
      id: "", // Missing actor.id
      name: "Malformed Event Sample",
      type: "agent",
    },
    action: {
      type: "TELEMETRY_UPDATED",
      summary: "Heartbeat update logged from cluster node.",
    },
    target: {
      type: "system",
      id: "control-plane",
    },
    result: "warning",
    severity: "low",
    provenance: {
      source: "inferred",
      // Missing confidence for inferred source
      evidence_refs: [], // Missing evidence refs
    },
    policy: null as any, // Missing policy context
  },
];
