import type { ApprovalRequest } from "./collaborationTypes";

export type EscalationPolicy = {
  id: string;
  name: string;
  triggerMinutes: number;
  action: "escalate_to_admin" | "auto_reject" | "notify_security_ops";
  description: string;
};

export const DEFAULT_ESCALATION_POLICIES: EscalationPolicy[] = [
  {
    id: "esc-1",
    name: "Stalled Critical Swarm Approval",
    triggerMinutes: 10,
    action: "escalate_to_admin",
    description: "Escalate high or critical risk commands to admin role if pending for more than 10 minutes."
  },
  {
    id: "esc-2",
    name: "Expiry Auto-Rejection",
    triggerMinutes: 0, // at expiration time
    action: "auto_reject",
    description: "Automatically reject any pending approval that reaches its expiration time."
  },
  {
    id: "esc-3",
    name: "Security Ops Incident Escalation",
    triggerMinutes: 15,
    action: "notify_security_ops",
    description: "Send alert to security ops center if a high risk command is escalated or remains unhandled."
  }
];

export const checkRequestEscalation = (
  request: ApprovalRequest,
  policies: EscalationPolicy[] = DEFAULT_ESCALATION_POLICIES
): { shouldEscalate: boolean; action?: EscalationPolicy["action"]; reason?: string } => {
  if (request.status !== "pending") {
    return { shouldEscalate: false };
  }

  const createdAt = new Date(request.created_at).getTime();
  const durationMs = Date.now() - createdAt;
  const durationMin = durationMs / 60000;

  // Check if expired
  if (request.expires_at) {
    const expiresAt = new Date(request.expires_at).getTime();
    if (Date.now() >= expiresAt) {
      return {
        shouldEscalate: true,
        action: "auto_reject",
        reason: "Request has exceeded its expiration limit."
      };
    }
  }

  // Check high/critical risk escalation policy
  if (request.command.risk === "high" || request.command.risk === "critical") {
    const criticalPolicy = policies.find((p) => p.id === "esc-1");
    if (criticalPolicy && durationMin >= criticalPolicy.triggerMinutes) {
      return {
        shouldEscalate: true,
        action: "escalate_to_admin",
        reason: `Pending for ${Math.round(durationMin)}m. Escalated to Administrator role.`
      };
    }
  }

  return { shouldEscalate: false };
};
