import type { PolicyEvaluationInput } from "./policyTypes";

export function isApprovalNeeded(input: PolicyEvaluationInput): boolean {
  // Production actions or High/Critical risk commands require approval signatures
  if (input.environment === "PROD") return true;
  if (["high", "critical"].includes(input.command.risk)) return true;
  return false;
}

export function getRequiredApproverRole(risk: string): "approver" | "admin" {
  if (risk === "critical") return "admin";
  return "approver";
}
