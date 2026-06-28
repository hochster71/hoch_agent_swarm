import type { ParsedCommand } from "./commandTypes";

export function estimateCommandImpact(command: ParsedCommand) {
  let summary = "No significant cluster impact expected.";
  let estimated_duration = "N/A";
  let expected_latency_delta = "0.0ms";
  const expected_cpu_delta: Record<string, string> = {};
  const expected_memory_delta: Record<string, string> = {};

  if (command.intent === "rebalance_workload") {
    summary = "Reallocates agent docker workload instances across target nodes to optimize CPU/RAM utilization.";
    estimated_duration = "~ 2m";
    expected_latency_delta = "+0.3ms";
    expected_cpu_delta["L2"] = "-18% to -24%";
    expected_cpu_delta["W1"] = "+10% to +14%";
    expected_memory_delta["L2"] = "-1.2GB";
    expected_memory_delta["W1"] = "+1.2GB";
  } else if (command.intent === "restart_agent") {
    summary = "Restarts selected container agent instance, causing temporary execution downtime.";
    estimated_duration = "~ 15s";
    expected_latency_delta = "+1.2ms (transient)";
    command.affected_assets.forEach(asset => {
      expected_cpu_delta[asset.id] = "-5% (idle) then +20% (init)";
    });
  } else if (command.intent === "rollback_deploy") {
    summary = "Reverts active software version of deployed agent container to the previous verified commit.";
    estimated_duration = "~ 45s";
    expected_latency_delta = "+0.1ms";
    command.affected_assets.forEach(asset => {
      expected_cpu_delta[asset.id] = "+15% (building)";
      expected_memory_delta[asset.id] = "+256MB";
    });
  } else if (command.intent === "run_diagnostic") {
    summary = "Launches remote diagnostics shell checks. Non-disruptive compliance scanning.";
    estimated_duration = "~ 5s";
    expected_latency_delta = "+0.0ms";
    command.affected_assets.forEach(asset => {
      expected_cpu_delta[asset.id] = "+2% (temporary)";
    });
  }

  return {
    summary,
    estimated_duration,
    expected_latency_delta,
    expected_cpu_delta,
    expected_memory_delta,
  };
}
