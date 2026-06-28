import type { AuditEvent } from "../audit/auditTypes";

export const sampleIncidentTimeline: AuditEvent[] = [
  {
    event_id: "evt_rep_001",
    correlation_id: "corr_incident_rebalance",
    timestamp: "2026-06-24T10:30:00Z",
    actor: { id: "telemetry.monitor", name: "Telemetry Engine", type: "system" },
    action: { type: "TELEMETRY_UPDATED", summary: "MacBook iMac memory utilization reached critical warning: 91%." },
    target: { type: "asset", id: "asset-imac", name: "Michael's iMac" },
    result: "warning",
    severity: "medium",
    provenance: { source: "observed", evidence_refs: ["telemetry.ram.imac.latest"] },
    policy: { required: false, result: "not_required" }
  },
  {
    event_id: "evt_rep_002",
    correlation_id: "corr_incident_rebalance",
    timestamp: "2026-06-24T10:30:15Z",
    actor: { id: "intel.agent", name: "AI Insight Engine", type: "agent" },
    action: { type: "AI_RECOMMENDATION_GENERATED", summary: "Generated recommendation: rebalance workload from Michael's iMac to Dell 9440." },
    target: { type: "system", id: "insight-rebalance-imac-dell" },
    result: "success",
    severity: "info",
    provenance: { source: "inferred", confidence: 87, evidence_refs: ["telemetry.cpu.imac.30m", "telemetry.cpu.dell9440.latest"] },
    policy: { required: false, result: "not_required" }
  },
  {
    event_id: "evt_rep_003",
    correlation_id: "corr_incident_rebalance",
    timestamp: "2026-06-24T10:31:00Z",
    actor: { id: "michael.operator", name: "Michael Hoch", type: "human", role: "Operator" },
    action: { type: "COMMAND_PREVIEWED", summary: "Previewed task: rebalance workload from Michael's iMac to Dell 9440" },
    target: { type: "command", id: "cmd_active_eval" },
    result: "success",
    severity: "info",
    provenance: { source: "manual", evidence_refs: ["user_ui_preview_click"] },
    policy: { required: true, result: "passed", policy_ids: ["RULE-REBAL-01"] }
  },
  {
    event_id: "evt_rep_004",
    correlation_id: "corr_incident_rebalance",
    timestamp: "2026-06-24T10:31:10Z",
    actor: { id: "michael.operator", name: "Michael Hoch", type: "human", role: "Operator" },
    action: { type: "COMMAND_EXECUTED", summary: "Confirmed rebalance workload dispatch from Michael's iMac to Dell 9440." },
    target: { type: "asset", id: "asset-dell9440", name: "Dell XPS 9440" },
    result: "success",
    severity: "info",
    provenance: { source: "manual", evidence_refs: ["user_ui_confirm_click"] },
    policy: { required: true, result: "passed", policy_ids: ["RULE-REBAL-01"] },
    rollback: { available: true, rollback_id: "RB-REBAL-004", status: "completed" }
  }
];
