import { CustomerRecord } from "./customerTypes";

export const initialCustomers: CustomerRecord[] = [
  {
    customer_id: "cust-01",
    company_name: "Acme Enterprise Swarms",
    tenant_id: "tenant-acme-prod",
    lifecycle_stage: "active_adoption",
    deployment_health: "healthy",
    sla_target_percent: 99.9,
    sla_actual_percent: 99.95,
    active_users: 142,
    agent_pools_count: 8,
    automations_triggered_24h: 3120,
    support_tickets_open: 1,
    avg_ticket_response_minutes: 14,
    churn_risk_score: 12,
    churn_risk_reasons: [],
    efficiency_improved_percent: 34.5,
    cost_saved_usd: 12400,
    onboarding_checklist: [
      { task_id: "t-01", title: "Provision Control Plane", completed: true, completed_at: "2026-06-01T10:00:00Z" },
      { task_id: "t-02", title: "Link Tenancy Policies", completed: true, completed_at: "2026-06-02T11:00:00Z" },
      { task_id: "t-03", title: "Integrate Audit Ledgers", completed: true, completed_at: "2026-06-05T09:00:00Z" },
      { task_id: "t-04", title: "Verify Compliance Mappings", completed: true, completed_at: "2026-06-08T15:00:00Z" }
    ],
    onboarding_progress_percent: 100
  },
  {
    customer_id: "cust-02",
    company_name: "Nova Global Logistics",
    tenant_id: "tenant-nova-logistics",
    lifecycle_stage: "onboarding",
    deployment_health: "healthy",
    sla_target_percent: 99.5,
    sla_actual_percent: 99.8,
    active_users: 32,
    agent_pools_count: 3,
    automations_triggered_24h: 450,
    support_tickets_open: 2,
    avg_ticket_response_minutes: 25,
    churn_risk_score: 35,
    churn_risk_reasons: ["Incomplete onboarding integration", "Low active usage relative to licensing"],
    efficiency_improved_percent: 12.0,
    cost_saved_usd: 1800,
    onboarding_checklist: [
      { task_id: "t-01", title: "Provision Control Plane", completed: true, completed_at: "2026-06-20T14:30:00Z" },
      { task_id: "t-02", title: "Link Tenancy Policies", completed: true, completed_at: "2026-06-22T09:00:00Z" },
      { task_id: "t-03", title: "Integrate Audit Ledgers", completed: false },
      { task_id: "t-04", title: "Verify Compliance Mappings", completed: false }
    ],
    onboarding_progress_percent: 50
  },
  {
    customer_id: "cust-03",
    company_name: "Apex AI Finance",
    tenant_id: "tenant-apex-finance",
    lifecycle_stage: "at_risk",
    deployment_health: "degraded",
    sla_target_percent: 99.99,
    sla_actual_percent: 99.85,
    active_users: 210,
    agent_pools_count: 14,
    automations_triggered_24h: 5800,
    support_tickets_open: 4,
    avg_ticket_response_minutes: 42,
    churn_risk_score: 78,
    churn_risk_reasons: [
      "SLA breach (99.85% vs 99.99% target)",
      "Unresolved high-priority support tickets",
      "Degraded host deployment node health"
    ],
    efficiency_improved_percent: 41.2,
    cost_saved_usd: 35000,
    onboarding_checklist: [
      { task_id: "t-01", title: "Provision Control Plane", completed: true, completed_at: "2026-05-10T10:00:00Z" },
      { task_id: "t-02", title: "Link Tenancy Policies", completed: true, completed_at: "2026-05-11T12:00:00Z" },
      { task_id: "t-03", title: "Integrate Audit Ledgers", completed: true, completed_at: "2026-05-14T08:30:00Z" },
      { task_id: "t-04", title: "Verify Compliance Mappings", completed: true, completed_at: "2026-05-15T16:00:00Z" }
    ],
    onboarding_progress_percent: 100
  },
  {
    customer_id: "cust-04",
    company_name: "Vortex Biotech",
    tenant_id: "tenant-vortex-bio",
    lifecycle_stage: "provisioning",
    deployment_health: "unreachable",
    sla_target_percent: 99.5,
    sla_actual_percent: 0.0,
    active_users: 0,
    agent_pools_count: 0,
    automations_triggered_24h: 0,
    support_tickets_open: 1,
    avg_ticket_response_minutes: 5,
    churn_risk_score: 45,
    churn_risk_reasons: ["Host deployment unreachable", "Provisioning delay"],
    efficiency_improved_percent: 0.0,
    cost_saved_usd: 0,
    onboarding_checklist: [
      { task_id: "t-01", title: "Provision Control Plane", completed: false },
      { task_id: "t-02", title: "Link Tenancy Policies", completed: false },
      { task_id: "t-03", title: "Integrate Audit Ledgers", completed: false },
      { task_id: "t-04", title: "Verify Compliance Mappings", completed: false }
    ],
    onboarding_progress_percent: 0
  }
];
