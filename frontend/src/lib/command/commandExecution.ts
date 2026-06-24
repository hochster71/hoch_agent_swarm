import type { CommandPreview, CommandMode } from "./commandTypes";
import { parseCommandText } from "./commandParser";
import { classifyCommandRisk } from "./commandRisk";
import { runMockPolicyCheck } from "./commandPolicy";
import { estimateCommandImpact } from "./commandImpact";

const makeId = (prefix: string) => `${prefix}_${crypto.randomUUID().substring(0, 8)}`;

export function generatePreview(text: string, mode: CommandMode = "draft"): CommandPreview {
  const parsed = parseCommandText(text);
  const correlation_id = makeId("corr");
  const risk = classifyCommandRisk(parsed);
  const policyResult = runMockPolicyCheck(parsed);
  const impact = estimateCommandImpact(parsed);

  // Rollback configuration
  let rollbackAvailable = false;
  let rollbackExplanation = "No rollback available for this command.";
  let rollback_id: string | undefined;

  if (parsed.intent === "rebalance_workload") {
    rollbackAvailable = true;
    rollback_id = makeId("rb");
    rollbackExplanation = "Workload distribution configuration baseline recorded. Auto-rebalance script can revert.";
  } else if (parsed.intent === "rollback_deploy") {
    rollbackAvailable = true;
    rollback_id = makeId("rb");
    rollbackExplanation = "Prior deployment image tag is cached and ready.";
  } else if (parsed.intent === "restart_agent") {
    rollbackExplanation = "Container restart is stateful and non-reversible.";
  } else if (parsed.intent === "run_diagnostic") {
    rollbackExplanation = "Diagnostic check is read-only and requires no rollback.";
  }

  // Blockers check
  const blockers: string[] = [];
  if (parsed.intent === "unknown") {
    blockers.push("Command intent could not be parsed.");
  }
  if (policyResult.result === "failed") {
    blockers.push("Security compliance policy check failed.");
  }
  if (risk === "critical") {
    blockers.push("Critical risk level requires multi-party authorization.");
  }

  const executable = blockers.length === 0;

  const preview: CommandPreview = {
    command_id: parsed.command_id,
    correlation_id,
    parsed,
    mode,
    risk,
    policy: {
      required: policyResult.required,
      result: policyResult.result,
      policy_ids: policyResult.policy_ids,
      explanation: policyResult.explanation,
    },
    impact,
    rollback: {
      available: rollbackAvailable,
      rollback_id,
      explanation: rollbackExplanation,
    },
    executable,
    blockers,
  };

  // Dispatch initial preview events into ZTA Audit Trail
  if (typeof window !== "undefined" && window.addAuditEvent) {
    // 1. COMMAND_PREVIEWED
    window.addAuditEvent({
      correlation_id,
      actor: { id: "operator.michael", name: "Operator: Michael Hoch", type: "human", role: "Operator" },
      action: { type: "COMMAND_PREVIEWED", summary: `Command previewed: "${text}"`, command_text: text },
      target: { type: "command", id: parsed.command_id, name: parsed.intent },
      result: "success",
      severity: "info",
      provenance: { source: "manual", evidence_refs: [] },
      policy: { required: false, result: "not_required" }
    });

    // 2. POLICY_CHECKED
    window.addAuditEvent({
      correlation_id,
      actor: { id: "system.policy", name: "Policy Engine", type: "system" },
      action: { type: "POLICY_CHECKED", summary: `Policy check result for '${parsed.intent}': ${policyResult.result.toUpperCase()}` },
      target: { type: "policy", id: policyResult.policy_ids[0] || "POLICY_CHECK", name: "Operator Scope Enforcement" },
      result: policyResult.result === "failed" ? "failed" : "success",
      severity: policyResult.result === "failed" ? "high" : "low",
      provenance: { source: "observed", evidence_refs: [] },
      policy: { required: true, result: policyResult.result, explanation: policyResult.explanation }
    });

    // If blocked, log COMMAND_BLOCKED
    if (!executable) {
      window.addAuditEvent({
        correlation_id,
        actor: { id: "system.gatekeeper", name: "Execution Gatekeeper", type: "system" },
        action: { type: "COMMAND_BLOCKED", summary: `Execution blocked. Reason: ${blockers.join("; ")}` },
        target: { type: "command", id: parsed.command_id, name: parsed.intent },
        result: "blocked",
        severity: "high",
        provenance: { source: "observed", evidence_refs: [] },
        policy: { required: true, result: policyResult.result, explanation: "Block conditions met." }
      });
    }
  }

  return preview;
}

export function logSimulation(preview: CommandPreview) {
  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      correlation_id: preview.correlation_id,
      actor: { id: "operator.michael", name: "Operator: Michael Hoch", type: "human", role: "Operator" },
      action: { type: "COMMAND_SIMULATED", summary: `Dry-run simulation complete: "${preview.parsed.raw_text}"`, command_text: preview.parsed.raw_text },
      target: { type: "command", id: preview.command_id, name: preview.parsed.intent },
      result: "success",
      severity: "info",
      provenance: { source: "synthetic", confidence: 98, evidence_refs: ["simulation.engine.v1"] },
      policy: { required: false, result: "not_required" }
    });
  }
}

export function logExecution(preview: CommandPreview, success: boolean, override: boolean = false) {
  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      correlation_id: preview.correlation_id,
      actor: { id: "operator.michael", name: "Operator: Michael Hoch", type: "human", role: "Operator" },
      action: { 
        type: "COMMAND_EXECUTED", 
        summary: `${override ? "Emergency override " : ""}Instruction executed: "${preview.parsed.raw_text}"`, 
        command_text: preview.parsed.raw_text 
      },
      target: { type: "command", id: preview.command_id, name: preview.parsed.intent },
      result: success ? "success" : "failed",
      severity: override ? "critical" : preview.risk === "high" ? "high" : "medium",
      provenance: { source: "manual", evidence_refs: [] },
      policy: { 
        required: true, 
        result: override ? "failed" : preview.policy.result, 
        explanation: override ? "Bypassed via emergency operator credential." : preview.policy.explanation 
      }
    });
  }
}
