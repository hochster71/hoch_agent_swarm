export type CustomerLifecycleStage =
  | "provisioning"
  | "onboarding"
  | "active_adoption"
  | "expansion"
  | "at_risk"
  | "churned";

export type DeploymentHealthStatus =
  | "healthy"
  | "degraded"
  | "unreachable"
  | "critical";

export type OnboardingTask = {
  task_id: string;
  title: string;
  completed: boolean;
  completed_at?: string;
};

export type CustomerRecord = {
  customer_id: string;
  company_name: string;
  tenant_id: string;
  lifecycle_stage: CustomerLifecycleStage;
  deployment_health: DeploymentHealthStatus;
  sla_target_percent: number;
  sla_actual_percent: number;
  active_users: number;
  agent_pools_count: number;
  automations_triggered_24h: number;
  support_tickets_open: number;
  avg_ticket_response_minutes: number;
  churn_risk_score: number; // 0 to 100
  churn_risk_reasons: string[];
  efficiency_improved_percent: number; // outcome metric
  cost_saved_usd: number;
  onboarding_checklist: OnboardingTask[];
  onboarding_progress_percent: number;
};
