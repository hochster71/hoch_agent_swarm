export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "changes_requested"
  | "expired"
  | "escalated";

export type ApprovalDecision = "approve" | "reject" | "request_changes";

export type ApprovalRequest = {
  approval_id: string;
  created_at: string;
  expires_at?: string;
  status: ApprovalStatus;
  requested_by: {
    id: string;
    name: string;
    role: string;
  };
  required_approver_role: "approver" | "admin";
  command: {
    command_id: string;
    correlation_id: string;
    raw_text: string;
    risk: "low" | "medium" | "high" | "critical";
  };
  target: {
    id: string;
    name: string;
    type: string;
  };
  policy_context: {
    decision: "allow" | "warn" | "block";
    approval_reason: string;
    blockers: string[];
    warnings: string[];
  };
  decisions: {
    decision_id: string;
    decided_at: string;
    decided_by: {
      id: string;
      name: string;
      role: string;
    };
    decision: ApprovalDecision;
    note: string;
  }[];
};

export type OperatorPresence = {
  id: string;
  name: string;
  role: string;
  status: "online" | "away" | "offline";
  last_active: string;
};
