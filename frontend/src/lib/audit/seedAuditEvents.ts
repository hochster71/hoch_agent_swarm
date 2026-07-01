import type { AuditEvent } from "./auditTypes";
import { createAuditEvent } from "./auditEvents";

export const seedAuditEvents: AuditEvent[] = [
  createAuditEvent({
    actor: {
      id: "michael.hoch",
      name: "Michael Hoch",
      type: "human",
      role: "Operator",
    },
    action: {
      type: "TELEMETRY_UPDATED",
      summary: "Telemetry synchronized across 6 active mesh assets.",
    },
    target: {
      type: "system",
      id: "hoch-swarm-dashboard",
      name: "HOCH Swarm Dashboard",
    },
    result: "success",
    severity: "info",
    provenance: {
      source: "observed",
      confidence: 100,
      evidence_refs: ["telemetry.sync.latest"],
    },
    policy: {
      required: false,
      result: "not_required",
    },
  }),
  createAuditEvent({
    actor: {
      id: "agent.memory-analysis",
      name: "Memory Analysis Agent",
      type: "agent",
    },
    action: {
      type: "AI_RECOMMENDATION_GENERATED",
      summary: "Memory leak pattern inferred on Michael's iMac.",
    },
    target: {
      type: "asset",
      id: "asset-imac",
      name: "Michael's iMac",
    },
    result: "warning",
    severity: "medium",
    provenance: {
      source: "inferred",
      confidence: 87,
      evidence_refs: ["telemetry.ram.imac.30m"],
    },
    policy: {
      required: false,
      result: "not_required",
    },
    rollback: {
      available: false,
      status: "not_started",
    },
  }),
  createAuditEvent({
    actor: {
      id: "agent.deploy-guard",
      name: "Deploy Guard Agent",
      type: "agent",
    },
    action: {
      type: "ROLLBACK_STARTED",
      summary: "Canary rollback started on HOCH-Mesh MacBook Neo after failed deploy.",
    },
    target: {
      type: "asset",
      id: "asset-macbook-neo",
      name: "HOCH-Mesh MacBook Neo",
    },
    result: "pending",
    severity: "medium",
    provenance: {
      source: "observed",
      confidence: 94,
      evidence_refs: ["deploy.canary.macbook-neo.latest"],
    },
    policy: {
      required: true,
      result: "passed",
      policy_ids: ["POLICY_CANARY_ROLLBACK_ALLOWED"],
      explanation: "Rollback permitted because failed canary crossed error threshold.",
    },
    rollback: {
      available: true,
      rollback_id: "rb_canary_macbook_neo_latest",
      status: "started",
    },
  }),
];
