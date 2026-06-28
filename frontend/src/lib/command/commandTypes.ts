export type CommandMode = "draft" | "simulate" | "execute";
export type CommandRisk = "low" | "medium" | "high" | "critical";

export type ParsedCommand = {
  command_id: string;
  raw_text: string;
  intent:
    | "rebalance_workload"
    | "restart_agent"
    | "rollback_deploy"
    | "run_diagnostic"
    | "unknown";
  affected_assets: {
    id: string;
    name: string;
    current_status?: string;
  }[];
  affected_swarms?: {
    id: string;
    name: string;
  }[];
  confidence: number;
};

export type CommandPreview = {
  command_id: string;
  correlation_id: string;
  parsed: ParsedCommand;
  mode: CommandMode;
  risk: CommandRisk;
  policy: {
    required: boolean;
    result: "passed" | "failed" | "warning" | "not_required";
    policy_ids: string[];
    explanation: string;
  };
  impact: {
    summary: string;
    estimated_duration?: string;
    expected_latency_delta?: string;
    expected_cpu_delta?: Record<string, string>;
    expected_memory_delta?: Record<string, string>;
  };
  rollback: {
    available: boolean;
    rollback_id?: string;
    explanation: string;
  };
  executable: boolean;
  blockers: string[];
};
