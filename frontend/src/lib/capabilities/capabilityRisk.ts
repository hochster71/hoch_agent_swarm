import type { CapabilityRecord, CapabilityRisk } from "./capabilityTypes";

export function scoreCapabilityRisk(capability: CapabilityRecord): {
  risk: CapabilityRisk;
  score: number;
  reasons: string[];
} {
  let score = 0;
  const reasons: string[] = [];
  if (capability.permissions.shell) {
    score += 30;
    reasons.push("Capability can execute shell commands.");
  }
  if (capability.permissions.secrets) {
    score += 30;
    reasons.push("Capability can access secrets.");
  }
  if (capability.permissions.external_write) {
    score += 20;
    reasons.push("Capability can write to external systems.");
  }
  if (capability.guardrails.max_autonomy_level === "execute") {
    score += 25;
    reasons.push("Capability can execute autonomously.");
  }
  if (capability.telemetry.failure_rate_30d > 0.05) {
    score += 15;
    reasons.push("Capability failure rate exceeds 5%.");
  }
  const risk: CapabilityRisk =
    score >= 80 ? "critical" : score >= 55 ? "high" : score >= 30 ? "medium" : "low";
  return { risk, score, reasons };
}
