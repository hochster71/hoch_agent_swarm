import type { ApprovalRequest, OperatorPresence } from "./collaborationTypes";

export const generateMockOperators = (): OperatorPresence[] => [
  {
    id: "op-1",
    name: "Alex Vance",
    role: "approver",
    status: "online",
    last_active: new Date(Date.now() - 2 * 60000).toISOString()
  },
  {
    id: "op-2",
    name: "Dr. Judith Mossman",
    role: "admin",
    status: "online",
    last_active: new Date(Date.now() - 30 * 1000).toISOString()
  },
  {
    id: "op-3",
    name: "Barney Calhoun",
    role: "operator",
    status: "away",
    last_active: new Date(Date.now() - 15 * 60000).toISOString()
  },
  {
    id: "op-4",
    name: "Wallace Breen",
    role: "approver",
    status: "offline",
    last_active: new Date(Date.now() - 24 * 3600000).toISOString()
  }
];

export const generateMockApprovals = (): ApprovalRequest[] => [
  {
    approval_id: "app-101",
    created_at: new Date(Date.now() - 10 * 60000).toISOString(),
    expires_at: new Date(Date.now() + 50 * 60000).toISOString(),
    status: "pending",
    requested_by: {
      id: "op-3",
      name: "Barney Calhoun",
      role: "operator"
    },
    required_approver_role: "approver",
    command: {
      command_id: "cmd-301",
      correlation_id: "corr-111",
      raw_text: "swarm deploy --node-group gamma --override-safety-limits",
      risk: "high"
    },
    target: {
      id: "swarm-gamma",
      name: "Swarm Node Group Gamma",
      type: "swarm"
    },
    policy_context: {
      decision: "block",
      approval_reason: "High risk command executed by standard operator requires approver authorization.",
      blockers: ["high_risk_command_execution", "operator_role_insufficient_for_high_risk"],
      warnings: ["target_node_group_near_capacity"]
    },
    decisions: []
  },
  {
    approval_id: "app-102",
    created_at: new Date(Date.now() - 25 * 60000).toISOString(),
    expires_at: new Date(Date.now() + 35 * 60000).toISOString(),
    status: "approved",
    requested_by: {
      id: "op-3",
      name: "Barney Calhoun",
      role: "operator"
    },
    required_approver_role: "approver",
    command: {
      command_id: "cmd-302",
      correlation_id: "corr-112",
      raw_text: "swarm scale --node-group beta --replicas 12",
      risk: "medium"
    },
    target: {
      id: "swarm-beta",
      name: "Swarm Node Group Beta",
      type: "swarm"
    },
    policy_context: {
      decision: "warn",
      approval_reason: "Scaling replicas above baseline warning limit (8).",
      blockers: [],
      warnings: ["replicas_exceed_warning_limit"]
    },
    decisions: [
      {
        decision_id: "dec-201",
        decided_at: new Date(Date.now() - 20 * 60000).toISOString(),
        decided_by: {
          id: "op-1",
          name: "Alex Vance",
          role: "approver"
        },
        decision: "approve",
        note: "Scaling approved for scheduled load test event."
      }
    ]
  },
  {
    approval_id: "app-103",
    created_at: new Date(Date.now() - 45 * 60000).toISOString(),
    expires_at: new Date(Date.now() + 15 * 60000).toISOString(),
    status: "rejected",
    requested_by: {
      id: "op-1",
      name: "Alex Vance",
      role: "approver"
    },
    required_approver_role: "admin",
    command: {
      command_id: "cmd-303",
      correlation_id: "corr-113",
      raw_text: "swarm purge --all-inactive-nodes --force",
      risk: "critical"
    },
    target: {
      id: "system-root",
      name: "System Root Swarm Controller",
      type: "system"
    },
    policy_context: {
      decision: "block",
      approval_reason: "Critical destructive swarm-wide operations require dual-operator admin signoff.",
      blockers: ["destructive_system_operation", "dual_operator_signoff_missing"],
      warnings: []
    },
    decisions: [
      {
        decision_id: "dec-202",
        decided_at: new Date(Date.now() - 35 * 60000).toISOString(),
        decided_by: {
          id: "op-2",
          name: "Dr. Judith Mossman",
          role: "admin"
        },
        decision: "reject",
        note: "Purging active swarms is unsafe during live operations. Resubmit after maintenance window starts."
      }
    ]
  },
  {
    approval_id: "app-104",
    created_at: new Date(Date.now() - 90 * 60000).toISOString(),
    expires_at: new Date(Date.now() - 30 * 60000).toISOString(),
    status: "expired",
    requested_by: {
      id: "op-3",
      name: "Barney Calhoun",
      role: "operator"
    },
    required_approver_role: "approver",
    command: {
      command_id: "cmd-304",
      correlation_id: "corr-114",
      raw_text: "swarm debug --node-id node-442 --tunnel-port 8080",
      risk: "medium"
    },
    target: {
      id: "node-442",
      name: "Mission Node 442",
      type: "asset"
    },
    policy_context: {
      decision: "warn",
      approval_reason: "Remote port forwarding request requires authorization.",
      blockers: [],
      warnings: ["remote_access_tunnel_open"]
    },
    decisions: []
  }
];
