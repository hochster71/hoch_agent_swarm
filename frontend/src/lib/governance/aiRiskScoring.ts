import type { AiRiskTier, AiSystemRecord } from "./governanceTypes";

export function scoreAiSystemRisk(system: AiSystemRecord): {
  score: number;
  tier: AiRiskTier;
  reasons: string[];
} {
  let score = 0;
  const reasons: string[] = [];

  if (system.autonomy.can_execute) {
    score += 30;
    reasons.push("System can execute actions.");
  }
  if (system.data_access.secret_access) {
    score += 25;
    reasons.push("System has access to secrets.");
  }
  if (system.data_access.pii_access) {
    score += 20;
    reasons.push("System has access to PII.");
  }
  if (system.data_access.classification === "restricted") {
    score += 20;
    reasons.push("System accesses restricted data.");
  }
  if (!system.autonomy.requires_human_approval && system.autonomy.can_execute) {
    score += 25;
    reasons.push("Executable autonomy without mandatory approval.");
  }

  const missingControls = system.controls.filter(
    (control) => control.status === "missing"
  );
  if (missingControls.length > 0) {
    score += Math.min(30, missingControls.length * 10);
    reasons.push(`${missingControls.length} controls are missing.`);
  }

  const tier: AiRiskTier =
    score >= 80 ? "critical" : score >= 55 ? "high" : score >= 30 ? "medium" : "low";

  return { score, tier, reasons };
}
