export type TenantStatus =
  | "active"
  | "trial"
  | "suspended"
  | "archived";

export type TenantPlan =
  | "internal"
  | "pilot"
  | "enterprise"
  | "regulated";

export type TenantRecord = {
  tenant_id: string;
  name: string;
  status: TenantStatus;
  plan: TenantPlan;
  admins: {
    user_id: string;
    name: string;
    email: string;
  }[];
  isolation: {
    namespace: string;
    data_partition_key: string;
    dedicated_runtime: boolean;
    dedicated_key_material: boolean;
    cross_tenant_access_allowed: boolean;
  };
  quotas: {
    max_users: number;
    max_agents: number;
    max_events_per_day: number;
    max_integrations: number;
    max_storage_gb: number;
  };
  policy: {
    allowed_environments: ("LOCAL" | "DEV" | "STAGING" | "PROD")[];
    allowed_integrations: string[];
    approval_required_for_high_risk: boolean;
    data_residency_region?: string;
  };
  usage: {
    users: number;
    agents: number;
    events_today: number;
    integrations: number;
    storage_gb: number;
  };
  lifecycle: {
    created_at: string;
    updated_at: string;
    suspended_at?: string;
    archived_at?: string;
  };
};
