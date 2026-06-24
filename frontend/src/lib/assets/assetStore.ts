import { create } from "zustand";
import type { Asset, AssetStatus, AssetRisk } from "./assetTypes";

type AssetStore = {
  assets: Asset[];
  selectedAssetId: string | null;
  isDrilldownOpen: boolean;
  selectAsset: (assetId: string) => void;
  closeDrilldown: () => void;
  updateAsset: (assetId: string, patch: Partial<Asset>) => void;
  updateAssetsFromLegacy: (nodes: any[]) => void;
};

// Default seeded assets mapping the screenshots
const defaultAssets: Asset[] = [
  {
    id: "L1",
    name: "MBP MS PRO (CONTROL PLANE)",
    ip_address: "10.0.0.6",
    device_type: "MacBook Pro",
    status: "active",
    risk: "low",
    telemetry: { cpu_percent: 24, ram_used_gb: 18.0, ram_total_gb: 24.0, disk_used_gb: 512, disk_total_gb: 1024, network_latency_ms: 1.2 },
    state: {
      summary: "Control Plane Master node executing swarm scheduler and host coordination. No anomalies detected.",
      provenance: "observed",
      confidence: 100,
      last_updated: new Date().toISOString(),
      evidence_refs: ["master.orchestrator.health"]
    },
    active_swarms: [{ id: "c2_hub", name: "C2 Operations Hub", role: "Master" }],
    recommendations: [
      {
        id: "rec_l1_1",
        summary: "Run diagnostics scan to check Docker runtime containers status.",
        action_type: "run_diagnostic",
        severity: "info",
        confidence: 95,
        evidence_refs: ["runtime.docker.check"]
      }
    ]
  },
  {
    id: "L2",
    name: "MICHAEL'S IMAC",
    ip_address: "10.0.0.91",
    device_type: "iMac",
    status: "training",
    risk: "medium",
    telemetry: { cpu_percent: 84, ram_used_gb: 38.0, ram_total_gb: 64.0, disk_used_gb: 512, disk_total_gb: 1000, network_latency_ms: 2.1 },
    state: {
      summary: "Possible memory leak pattern detected. High RAM consumption over 30-minute tracking window.",
      provenance: "inferred",
      confidence: 87,
      last_updated: new Date().toISOString(),
      evidence_refs: ["RAM trend telemetry", "30-minute window"]
    },
    active_swarms: [{ id: "swarm_beta", name: "Agent Swarm Beta", role: "Coder" }],
    recommendations: [
      {
        id: "rec_l2_1",
        summary: "Simulate workload rebalance to offload active tasks to Dell 9440.",
        action_type: "simulate_rebalance",
        severity: "medium",
        confidence: 91,
        evidence_refs: ["iMac CPU load", "Dell available capacity"]
      },
      {
        id: "rec_l2_2",
        summary: "Restart active Gordy agent container to flush memory leak buffers.",
        action_type: "restart_agent",
        severity: "high",
        confidence: 85,
        evidence_refs: ["leak.pattern.detected"]
      }
    ]
  },
  {
    id: "L3",
    name: "HOCH-MESH MACBOOK NEO",
    ip_address: "10.0.0.8",
    device_type: "MacBook Neo",
    status: "self_healing",
    risk: "medium",
    telemetry: { cpu_percent: 42, ram_used_gb: 14.5, ram_total_gb: 32.0, disk_used_gb: 256, disk_total_gb: 512, network_latency_ms: 1.8 },
    state: {
      summary: "Canary rollback in progress. Reverting Gordy-Neo-01 container config to stable release.",
      provenance: "observed",
      confidence: 100,
      last_updated: new Date().toISOString(),
      evidence_refs: ["docker.canary.revert"]
    },
    active_swarms: [{ id: "swarm_beta", name: "Agent Swarm Beta", role: "Coder" }],
    recommendations: [
      {
        id: "rec_l3_1",
        summary: "Perform diagnostic scan to check rollback post-status integrity.",
        action_type: "run_diagnostic",
        severity: "info",
        confidence: 99,
        evidence_refs: ["rollback.stable.validate"]
      }
    ]
  },
  {
    id: "W1",
    name: "DELL 9440",
    ip_address: "10.0.0.207",
    device_type: "Dell XPS 14",
    status: "reasoning",
    risk: "low",
    telemetry: { cpu_percent: 62, ram_used_gb: 12.0, ram_total_gb: 16.0, disk_used_gb: 180, disk_total_gb: 512, network_latency_ms: 3.5 },
    state: {
      summary: "Node executing agent reasoning loop. Resource optimization metrics within target range.",
      provenance: "observed",
      confidence: 95,
      last_updated: new Date().toISOString(),
      evidence_refs: ["telemetry.process.vitals"]
    },
    active_swarms: [{ id: "swarm_alpha", name: "Agent Swarm Alpha", role: "Lead Coder" }],
    recommendations: [
      {
        id: "rec_w1_1",
        summary: "Diagnostic check for Docker daemon container status.",
        action_type: "run_diagnostic",
        severity: "info",
        confidence: 90,
        evidence_refs: ["docker.service.active"]
      }
    ]
  },
  {
    id: "IPAD",
    name: "IPAD PRO 12\"",
    ip_address: "10.0.0.129",
    device_type: "iPad",
    status: "active",
    risk: "low",
    telemetry: { cpu_percent: 18, ram_used_gb: 4.2, ram_total_gb: 8.0, disk_used_gb: 120, disk_total_gb: 256, network_latency_ms: 5.4 },
    state: {
      summary: "Mobile edge operator interface node online. Telemetry is active.",
      provenance: "observed",
      confidence: 100,
      last_updated: new Date().toISOString(),
      evidence_refs: ["mobile.edge.ping"]
    },
    active_swarms: [],
    recommendations: []
  },
  {
    id: "IPHONE",
    name: "IPHONE 15 PRO",
    ip_address: "10.0.0.130",
    device_type: "iPhone",
    status: "active",
    risk: "low",
    telemetry: { cpu_percent: 12, ram_used_gb: 3.1, ram_total_gb: 6.0, disk_used_gb: 90, disk_total_gb: 128, network_latency_ms: 6.8 },
    state: {
      summary: "Operator security monitoring endpoint online. Read-only session telemetry active.",
      provenance: "observed",
      confidence: 100,
      last_updated: new Date().toISOString(),
      evidence_refs: ["mobile.sec.ping"]
    },
    active_swarms: [],
    recommendations: []
  }
];

export const useAssetStore = create<AssetStore>((set, get) => ({
  assets: defaultAssets,
  selectedAssetId: null,
  isDrilldownOpen: false,

  selectAsset: (assetId) => {
    set({ selectedAssetId: assetId, isDrilldownOpen: true });
    
    // Log ASSET_DRILLDOWN_OPENED event into the ZTA Audit Trail if available
    if (typeof window !== "undefined" && window.addAuditEvent) {
      const asset = get().assets.find(a => a.id === assetId);
      window.addAuditEvent({
        actor: { id: "operator.michael", name: "Operator: Michael Hoch", type: "human", role: "Operator" },
        action: { type: "ASSET_DRILLDOWN_OPENED" as any, summary: `Operator opened details for node: ${asset ? asset.name : assetId}` },
        target: { type: "asset", id: assetId, name: asset?.name },
        result: "success",
        severity: "info",
        provenance: { source: "manual", evidence_refs: [] },
        policy: { required: false, result: "not_required" }
      });
    }
  },

  closeDrilldown: () => set({ isDrilldownOpen: false, selectedAssetId: null }),

  updateAsset: (assetId, patch) => set((state) => ({
    assets: state.assets.map(a => a.id === assetId ? { ...a, ...patch } : a)
  })),

  updateAssetsFromLegacy: (nodes) => set((state) => {
    const updated = state.assets.map((asset) => {
      const legacyNode = nodes.find(n => n.id === asset.id);
      if (!legacyNode) return asset;

      // Map status string to standard status
      let status: AssetStatus = "active";
      const legacyStatus = (legacyNode.status || "").toLowerCase().replace(/ /g, "-");
      if (legacyStatus.includes("train")) status = "training";
      else if (legacyStatus.includes("reason")) status = "reasoning";
      else if (legacyStatus.includes("heal")) status = "self_healing";
      else if (legacyStatus.includes("degrad")) status = "degraded";
      else if (legacyStatus.includes("offline") || legacyNode.latency_ms < 0) status = "offline";

      // Map risk
      let risk: AssetRisk = "low";
      if (status === "training" || status === "self_healing") risk = "medium";
      if (status === "degraded") risk = "high";
      if (status === "offline") risk = "critical";

      // Build active swarms list from legacy agents
      const active_swarms = (legacyNode.agents || []).map((ag: any) => ({
        id: ag.type.toLowerCase().replace(/ /g, "_"),
        name: ag.type,
        role: ag.status
      }));

      // Adjust explainable states dynamically based on status changes
      let summary = asset.state.summary;
      let provenance = asset.state.provenance;
      let confidence = asset.state.confidence;
      let evidence_refs = asset.state.evidence_refs;

      if (status === "offline") {
        summary = `Node connection lost. Last check failed to return response ping within timeout boundary.`;
        provenance = "observed";
        confidence = 100;
        evidence_refs = ["ping.timeout.failure"];
      } else if (status === "training" && asset.id === "L2") {
        summary = "Possible memory leak pattern detected. High RAM consumption over 30-minute tracking window.";
        provenance = "inferred";
        confidence = 87;
        evidence_refs = ["RAM trend telemetry", "30-minute window"];
      } else if (status === "self_healing" && asset.id === "L3") {
        summary = "Canary rollback in progress. Reverting Gordy-Neo-01 container config to stable release.";
        provenance = "observed";
        confidence = 100;
        evidence_refs = ["docker.canary.revert"];
      }

      return {
        ...asset,
        status,
        risk,
        ip_address: legacyNode.ip || asset.ip_address,
        active_swarms,
        telemetry: {
          ...asset.telemetry,
          cpu_percent: legacyNode.cpu_usage || asset.telemetry.cpu_percent,
          ram_used_gb: legacyNode.ram_usage_gb || asset.telemetry.ram_used_gb,
          ram_total_gb: legacyNode.ram_total_gb || asset.telemetry.ram_total_gb,
          network_latency_ms: legacyNode.latency_ms >= 0 ? legacyNode.latency_ms : undefined
        },
        state: {
          ...asset.state,
          summary,
          provenance,
          confidence,
          evidence_refs,
          last_updated: new Date().toISOString()
        }
      };
    });

    // Check if there are newly registered nodes not present in the default list
    const newAssets = [...updated];
    nodes.forEach((node) => {
      if (!newAssets.some(a => a.id === node.id)) {
        // Create new asset entry
        const isOffline = node.latency_ms < 0;
        const newAsset: Asset = {
          id: node.id,
          name: node.name.toUpperCase(),
          ip_address: node.ip || "10.0.0.X",
          device_type: "Compute Worker",
          status: isOffline ? "offline" : "active",
          risk: isOffline ? "critical" : "low",
          telemetry: {
            cpu_percent: node.cpu_usage || 0,
            ram_used_gb: node.ram_usage_gb || 0,
            ram_total_gb: node.ram_total_gb || 16.0,
            network_latency_ms: node.latency_ms >= 0 ? node.latency_ms : undefined
          },
          state: {
            summary: isOffline ? "Node offline." : "Dynamically registered Swarm worker node online.",
            provenance: "observed",
            confidence: 100,
            last_updated: new Date().toISOString(),
            evidence_refs: ["registration.sync"]
          },
          active_swarms: (node.agents || []).map((ag: any) => ({
            id: ag.type.toLowerCase().replace(/ /g, "_"),
            name: ag.type,
            role: ag.status
          })),
          recommendations: [
            {
              id: `rec_${node.id}_diag`,
              summary: "Perform initial diagnostic run on new worker node.",
              action_type: "run_diagnostic",
              severity: "info",
              confidence: 90,
              evidence_refs: ["new.node.registration"]
            }
          ]
        };
        newAssets.push(newAsset);
      }
    });

    // Handle deregistrations (filter out assets that were removed from backend nodes list, excluding default static clients if they aren't in nodes)
    // Actually, only filter if node is completely missing and its id does not belong to default edge devices (IPAD, IPHONE might not be in cluster_mgr if they are passive)
    const cleanedAssets = newAssets.filter(asset => {
      if (asset.id === "IPAD" || asset.id === "IPHONE") return true; // keep edge
      return nodes.some(n => n.id === asset.id);
    });

    return { assets: cleanedAssets };
  })
}));
