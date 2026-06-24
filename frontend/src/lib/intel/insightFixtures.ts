import type { OperationalInsight } from "./insightTypes";

export const sampleInsights: OperationalInsight[] = [
  {
    insight_id: "insight_rebalance_imac_dell",
    created_at: new Date().toISOString(),
    type: "recommendation",
    severity: "high",
    status: "new",
    title: "Rebalance workload from iMac to Dell 9440",
    summary: "The iMac shows elevated CPU and memory pressure while Dell 9440 has available capacity.",
    target: {
      type: "asset",
      id: "asset-imac",
      name: "Michael's iMac",
    },
    confidence: 87,
    explanation: {
      rationale: "Memory pressure on the iMac increased 24% over the last 30 minutes while alternate capacity is available.",
      contributing_factors: [
        "iMac CPU sustained above 80%",
        "RAM usage trend increasing",
        "Dell 9440 CPU below 65%",
      ],
      assumptions: [
        "Telemetry is current",
        "Dell 9440 can accept workload without policy violation",
      ],
      evidence_refs: [
        "telemetry.cpu.imac.30m",
        "telemetry.ram.imac.30m",
      ],
    },
    recommendation: {
      action_label: "Simulate workload rebalance",
      command_text: "rebalance workload from Michael's iMac to Dell 9440",
      expected_impact: "Reduce iMac CPU pressure by approximately 18–24%.",
      risk: "medium",
    },
  },
];
