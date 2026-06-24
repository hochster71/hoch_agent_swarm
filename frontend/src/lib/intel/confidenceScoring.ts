export function calculateInsightConfidence(factorsCount: number, evidenceCount: number, assumptionsCount: number): number {
  // Simple heuristic confidence calculator
  const baseConfidence = 75;
  const factorsBonus = factorsCount * 3;
  const evidenceBonus = evidenceCount * 4;
  const assumptionsPenalty = assumptionsCount * 3;
  
  const rawScore = baseConfidence + factorsBonus + evidenceBonus - assumptionsPenalty;
  return Math.max(50, Math.min(99, rawScore));
}
