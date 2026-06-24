export type AssetStatus =
  | "healthy"
  | "active"
  | "training"
  | "reasoning"
  | "self_healing"
  | "degraded"
  | "offline";

export type AssetRisk = "low" | "medium" | "high" | "critical";

export type Asset = {
  id: string;
  name: string;
  ip_address: string;
  device_type: string;
  status: AssetStatus;
  risk: AssetRisk;
  telemetry: {
    cpu_percent?: number;
    ram_used_gb?: number;
    ram_total_gb?: number;
    disk_used_gb?: number;
    disk_total_gb?: number;
    network_latency_ms?: number;
  };
  state: {
    summary: string;
    provenance: "observed" | "inferred" | "predicted" | "manual" | "synthetic";
    confidence?: number;
    last_updated: string;
    evidence_refs: string[];
  };
  active_swarms: {
    id: string;
    name: string;
    role?: string;
  }[];
  recommendations: {
    id: string;
    summary: string;
    action_type:
      | "simulate_rebalance"
      | "run_diagnostic"
      | "restart_agent"
      | "rollback"
      | "observe";
    severity: "info" | "low" | "medium" | "high" | "critical";
    confidence: number;
    evidence_refs: string[];
  }[];
};
