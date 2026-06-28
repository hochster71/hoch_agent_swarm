import type { Asset } from "./assetTypes";

export function generateRecommendationsForAsset(asset: Asset): Asset["recommendations"] {
  const recs: Asset["recommendations"] = [];

  if (asset.status === "training" && asset.id === "L2") {
    recs.push(
      {
        id: `rec_${asset.id}_rebalance`,
        summary: "Simulate workload rebalance to offload active tasks to Dell 9440.",
        action_type: "simulate_rebalance",
        severity: "medium",
        confidence: 91,
        evidence_refs: ["iMac CPU load", "Dell available capacity"]
      },
      {
        id: `rec_${asset.id}_restart`,
        summary: "Restart active Gordy agent container to flush memory leak buffers.",
        action_type: "restart_agent",
        severity: "high",
        confidence: 85,
        evidence_refs: ["leak.pattern.detected"]
      }
    );
  } else if (asset.status === "offline") {
    recs.push({
      id: `rec_${asset.id}_diag`,
      summary: "Run diagnostic scan on offline node to verify physical host availability and SSH connection parameters.",
      action_type: "run_diagnostic",
      severity: "critical",
      confidence: 98,
      evidence_refs: ["ping.failure"]
    });
  } else if (asset.status === "self_healing") {
    recs.push({
      id: `rec_${asset.id}_observe`,
      summary: "Observe active healing cycles. Wait for canary rollback validation.",
      action_type: "observe",
      severity: "info",
      confidence: 100,
      evidence_refs: ["canary.revert.status"]
    });
  } else {
    recs.push({
      id: `rec_${asset.id}_default_diag`,
      summary: "Perform diagnostic scan check to evaluate container resources health.",
      action_type: "run_diagnostic",
      severity: "info",
      confidence: 95,
      evidence_refs: ["routine.maintenance"]
    });
  }

  return recs;
}
