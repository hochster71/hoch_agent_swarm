import type {
  PolicyEvaluationInput,
  PolicyEvaluationResult,
} from "./policyTypes";

export function evaluatePolicy(
  input: PolicyEvaluationInput
): PolicyEvaluationResult {
  const passed: string[] = [];
  const warnings: string[] = [];
  const blockers: string[] = [];

  if (input.actor.role === "viewer") {
    blockers.push("Viewer role cannot execute operational commands.");
  } else {
    passed.push("Actor has executable role.");
  }

  if (input.zta.identity !== "verified") {
    blockers.push("Identity is not verified.");
  } else {
    passed.push("Identity verified.");
  }

  if (input.zta.device_posture !== "verified") {
    warnings.push("Device posture is not fully verified.");
  } else {
    passed.push("Device posture verified.");
  }

  if (input.zta.network_trust !== "verified") {
    warnings.push("Network trust is degraded or unknown.");
  } else {
    passed.push("Network trust verified.");
  }

  if (input.zta.session_integrity !== "verified") {
    blockers.push("Session integrity failed or unknown.");
  } else {
    passed.push("Session integrity verified.");
  }

  if (input.environment === "PROD" && input.command.risk !== "low") {
    warnings.push("Production command requires elevated approval.");
  }

  if (
    ["high", "critical"].includes(input.command.risk) &&
    !input.rollback.available
  ) {
    blockers.push("High-risk command requires rollback availability.");
  }

  if (input.command.risk === "critical") {
    blockers.push("Critical-risk command is blocked by default.");
  }

  const approval_required =
    input.environment === "PROD" ||
    input.command.risk === "high" ||
    input.command.risk === "critical";

  const decision =
    blockers.length > 0 ? "block" : warnings.length > 0 ? "warn" : "allow";

  const score = Math.max(0, 100 - blockers.length * 30 - warnings.length * 10);

  return {
    decision,
    score,
    passed,
    warnings,
    blockers,
    approval_required,
    approval_reason: approval_required
      ? "Approval required due to environment or command risk."
      : undefined,
    override_allowed: decision !== "allow" && input.actor.role === "admin",
    override_reason:
      decision !== "allow" && input.actor.role === "admin"
        ? "Admin override permitted with justification."
        : undefined,
    evaluated_at: new Date().toISOString(),
  };
}
