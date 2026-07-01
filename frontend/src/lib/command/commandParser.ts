import type { ParsedCommand } from "./commandTypes";

export function parseCommandText(text: string): ParsedCommand {
  const normalized = text.toLowerCase();
  
  let intent: ParsedCommand["intent"] = "unknown";
  if (normalized.includes("rebalance")) {
    intent = "rebalance_workload";
  } else if (normalized.includes("rollback")) {
    intent = "rollback_deploy";
  } else if (normalized.includes("restart")) {
    intent = "restart_agent";
  } else if (normalized.includes("diagnostic") || normalized.includes("scan")) {
    intent = "run_diagnostic";
  }

  // Find affected assets
  const affected_assets: ParsedCommand["affected_assets"] = [];
  
  if (normalized.includes("imac") || normalized.includes("l2")) {
    affected_assets.push({ id: "L2", name: "Michael's iMac", current_status: "Training" });
  }
  if (normalized.includes("dell") || normalized.includes("w1") || normalized.includes("9440")) {
    affected_assets.push({ id: "W1", name: "Dell 9440", current_status: "Reasoning" });
  }
  if (normalized.includes("neo") || normalized.includes("l3")) {
    affected_assets.push({ id: "L3", name: "MacBook Neo", current_status: "Self-Healing" });
  }
  if (normalized.includes("mbp") || normalized.includes("l1") || normalized.includes("control") || normalized.includes("macbook pro")) {
    affected_assets.push({ id: "L1", name: "MBP MS PRO", current_status: "Active" });
  }
  if (normalized.includes("ipad")) {
    affected_assets.push({ id: "IPAD", name: "iPad Pro 12\"", current_status: "Active" });
  }
  if (normalized.includes("iphone")) {
    affected_assets.push({ id: "IPHONE", name: "iPhone 15 Pro", current_status: "Active" });
  }

  // Fallback to routing heuristics if no node was mentioned explicitly
  if (affected_assets.length === 0 && intent !== "unknown") {
    // Default to L2 and W1 if rebalancing
    if (intent === "rebalance_workload") {
      affected_assets.push(
        { id: "L2", name: "Michael's iMac", current_status: "Training" },
        { id: "W1", name: "Dell 9440", current_status: "Reasoning" }
      );
    } else {
      affected_assets.push({ id: "L1", name: "MBP MS PRO (Control Plane)", current_status: "Active" });
    }
  }

  return {
    command_id: `cmd_${crypto.randomUUID()}`,
    raw_text: text,
    intent,
    affected_assets,
    confidence: intent === "unknown" ? 0.2 : 0.95,
  };
}
