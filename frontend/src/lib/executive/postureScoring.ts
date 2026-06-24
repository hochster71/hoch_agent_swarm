export function calculateExecutivePosture(params: {
  unresolvedCriticalRisks: number;
  failedReleaseGates: number;
  missingGovernanceControls: number;
  openPolicyViolations: number;
  ledgerVerified: boolean;
  sloHealthy: boolean;
}): {
  risk_score: number;
  readiness_score: number;
  governance_score: number;
  overall_status: "strong" | "stable" | "watch" | "degraded" | "critical";
} {
  let riskPenalty = 0;
  riskPenalty += params.unresolvedCriticalRisks * 20;
  riskPenalty += params.openPolicyViolations * 8;
  riskPenalty += params.failedReleaseGates * 12;
  if (!params.ledgerVerified) riskPenalty += 30;
  if (!params.sloHealthy) riskPenalty += 15;
  
  const risk_score = Math.max(0, 100 - riskPenalty);
  const readiness_score = Math.max(
    0,
    100 - params.failedReleaseGates * 15 - (params.sloHealthy ? 0 : 20)
  );
  const governance_score = Math.max(
    0,
    100 - params.missingGovernanceControls * 8
  );
  const minScore = Math.min(risk_score, readiness_score, governance_score);
  const overall_status =
    minScore >= 90
      ? "strong"
      : minScore >= 75
      ? "stable"
      : minScore >= 60
      ? "watch"
      : minScore >= 40
      ? "degraded"
      : "critical";
      
  return {
    risk_score,
    readiness_score,
    governance_score,
    overall_status,
  };
}
