import type { OperationalInsight } from "./insightTypes";

export function generateMockInsights(): OperationalInsight[] {
  const now = new Date().toISOString();
  return [
    {
      insight_id: "insight_rebalance_imac_dell",
      created_at: now,
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
          "Cluster latency remains acceptable",
        ],
        assumptions: [
          "Telemetry is current",
          "Dell 9440 can accept workload without policy violation",
        ],
        evidence_refs: [
          "telemetry.cpu.imac.30m",
          "telemetry.ram.imac.30m",
          "telemetry.cpu.dell9440.latest",
        ],
      },
      recommendation: {
        action_label: "Simulate workload rebalance",
        command_text: "rebalance workload from Michael's iMac to Dell 9440",
        expected_impact: "Reduce iMac CPU pressure by approximately 18–24%.",
        risk: "medium",
      },
    },
    {
      insight_id: "insight_memory_leak_macbook",
      created_at: now,
      type: "anomaly",
      severity: "medium",
      status: "new",
      title: "Restart Telemetry Agent on MacBook Neo",
      summary: "Potential heap memory leak detected. Memory consumption grew linearly by 45% over 1 hour.",
      target: {
        type: "asset",
        id: "asset-neo",
        name: "MacBook Neo [L3]",
      },
      confidence: 76,
      explanation: {
        rationale: "Unusual continuous growth of memory buffer without gc compaction cycle on container node.",
        contributing_factors: [
          "Linear memory increase over 60m",
          "No container restart in 48 hours",
        ],
        assumptions: [
          "Telemetry scheduler is normal",
        ],
        evidence_refs: [
          "telemetry.memory.neo.1h",
        ],
      },
      recommendation: {
        action_label: "Simulate container restart",
        command_text: "restart telemetry agent on MacBook Neo [L3]",
        expected_impact: "Free up 2.4GB of RAM allocation.",
        risk: "medium",
      },
    },
  ];
}
