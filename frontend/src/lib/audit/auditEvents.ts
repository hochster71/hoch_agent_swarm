import type { AuditEvent } from "./auditTypes";

const makeId = (prefix: string) =>
  `${prefix}_${crypto.randomUUID()}`;

export function createAuditEvent(
  input: Omit<AuditEvent, "event_id" | "timestamp" | "correlation_id"> & {
    correlation_id?: string;
  }
): AuditEvent {
  return {
    ...input,
    event_id: makeId("evt"),
    correlation_id: input.correlation_id ?? makeId("corr"),
    timestamp: new Date().toISOString(),
  };
}

export function createTelemetryUpdatedEvent(params: {
  assetId: string;
  assetName: string;
  summary: string;
  confidence?: number;
  evidenceRefs?: string[];
}): AuditEvent {
  return createAuditEvent({
    actor: {
      id: "system.telemetry",
      name: "Telemetry System",
      type: "system",
    },
    action: {
      type: "TELEMETRY_UPDATED",
      summary: params.summary,
    },
    target: {
      type: "asset",
      id: params.assetId,
      name: params.assetName,
    },
    result: "success",
    severity: "info",
    provenance: {
      source: "observed",
      confidence: params.confidence,
      evidence_refs: params.evidenceRefs ?? [],
    },
    policy: {
      required: false,
      result: "not_required",
    },
  });
}

export function createAiRecommendationEvent(params: {
  targetId: string;
  targetName: string;
  summary: string;
  confidence: number;
  evidenceRefs?: string[];
}): AuditEvent {
  return createAuditEvent({
    actor: {
      id: "agent.cluster-intel",
      name: "Cluster Intel Agent",
      type: "agent",
    },
    action: {
      type: "AI_RECOMMENDATION_GENERATED",
      summary: params.summary,
    },
    target: {
      type: "asset",
      id: params.targetId,
      name: params.targetName,
    },
    result: "success",
    severity: "medium",
    provenance: {
      source: "inferred",
      confidence: params.confidence,
      evidence_refs: params.evidenceRefs ?? [],
    },
    policy: {
      required: false,
      result: "not_required",
    },
  });
}
