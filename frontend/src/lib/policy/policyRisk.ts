
export function getCommandRisk(intent: string, rawText: string): "low" | "medium" | "high" | "critical" {
  const text = rawText.toLowerCase();
  
  if (text.includes("emergency") || text.includes("force") || text.includes("delete all")) {
    return "critical";
  }
  
  switch (intent) {
    case "rebalance_workload":
      return "medium";
    case "rollback_deploy":
      return "high";
    case "restart_agent":
      return "medium";
    case "run_diagnostic":
      return "low";
    default:
      return "medium";
  }
}

export function getRiskScore(risk: "low" | "medium" | "high" | "critical"): number {
  switch (risk) {
    case "low":
      return 10;
    case "medium":
      return 40;
    case "high":
      return 75;
    case "critical":
      return 95;
  }
}
