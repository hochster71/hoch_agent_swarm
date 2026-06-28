import type { CommandRisk, ParsedCommand } from "./commandTypes";

export function classifyCommandRisk(command: ParsedCommand): CommandRisk {
  if (command.intent === "rollback_deploy") return "high";
  if (command.intent === "restart_agent") return "medium";
  if (command.intent === "rebalance_workload") return "medium";
  if (command.intent === "run_diagnostic") return "low";
  return "critical";
}
