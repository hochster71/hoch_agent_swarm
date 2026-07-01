import type { TenantRecord } from "./tenantTypes";

export const initialTenants: TenantRecord[] = [
  {
    tenant_id: "acme-corp",
    name: "Acme Corporation",
    status: "active",
    plan: "enterprise",
    admins: [
      { user_id: "usr-acme-1", name: "Road Runner", email: "runner@acme.com" },
      { user_id: "usr-acme-2", name: "Wile E. Coyote", email: "coyote@acme.com" }
    ],
    isolation: {
      namespace: "acme-prod",
      data_partition_key: "part-acme-99",
      dedicated_runtime: true,
      dedicated_key_material: false,
      cross_tenant_access_allowed: false,
    },
    quotas: {
      max_users: 150,
      max_agents: 50,
      max_events_per_day: 2000000,
      max_integrations: 20,
      max_storage_gb: 1000
    },
    policy: {
      allowed_environments: ["LOCAL", "DEV", "STAGING", "PROD"],
      allowed_integrations: ["slack", "github", "jira"],
      approval_required_for_high_risk: true,
      data_residency_region: "US-East"
    },
    usage: {
      users: 128,
      agents: 24,
      events_today: 1200000,
      integrations: 12,
      storage_gb: 620
    },
    lifecycle: {
      created_at: "2026-01-10T08:00:00Z",
      updated_at: "2026-06-24T09:00:00Z"
    }
  },
  {
    tenant_id: "globex-ind",
    name: "Globex Industries",
    status: "active",
    plan: "enterprise",
    admins: [
      { user_id: "usr-globex-1", name: "Hank Scorpio", email: "scorpio@globex.com" }
    ],
    isolation: {
      namespace: "globex-mesh",
      data_partition_key: "part-globex-42",
      dedicated_runtime: true,
      dedicated_key_material: true,
      cross_tenant_access_allowed: false,
    },
    quotas: {
      max_users: 100,
      max_agents: 30,
      max_events_per_day: 1500000,
      max_integrations: 15,
      max_storage_gb: 800
    },
    policy: {
      allowed_environments: ["DEV", "STAGING", "PROD"],
      allowed_integrations: ["slack", "teams", "pagerduty"],
      approval_required_for_high_risk: true,
      data_residency_region: "EU-West"
    },
    usage: {
      users: 94,
      agents: 18,
      events_today: 930000,
      integrations: 8,
      storage_gb: 480
    },
    lifecycle: {
      created_at: "2026-02-15T09:00:00Z",
      updated_at: "2026-06-24T10:00:00Z"
    }
  },
  {
    tenant_id: "initech",
    name: "Initech",
    status: "trial",
    plan: "pilot",
    admins: [
      { user_id: "usr-ini-1", name: "Peter Gibbons", email: "peter@initech.com" },
      { user_id: "usr-ini-2", name: "Bill Lumbergh", email: "lumbergh@initech.com" }
    ],
    isolation: {
      namespace: "initech-staging",
      data_partition_key: "part-initech-13",
      dedicated_runtime: false,
      dedicated_key_material: false,
      cross_tenant_access_allowed: false,
    },
    quotas: {
      max_users: 80,
      max_agents: 15,
      max_events_per_day: 800000,
      max_integrations: 5,
      max_storage_gb: 500
    },
    policy: {
      allowed_environments: ["DEV", "STAGING"],
      allowed_integrations: ["slack"],
      approval_required_for_high_risk: true,
      data_residency_region: "AP-Southeast"
    },
    usage: {
      users: 76,
      agents: 10,
      events_today: 640000,
      integrations: 4,
      storage_gb: 310
    },
    lifecycle: {
      created_at: "2026-05-01T10:00:00Z",
      updated_at: "2026-06-20T14:30:00Z"
    }
  },
  {
    tenant_id: "stark-ind",
    name: "Stark Industries",
    status: "active",
    plan: "pilot",
    admins: [
      { user_id: "usr-stark-1", name: "Pepper Potts", email: "pepper@stark.com" }
    ],
    isolation: {
      namespace: "stark-core",
      data_partition_key: "part-stark-01",
      dedicated_runtime: true,
      dedicated_key_material: true,
      cross_tenant_access_allowed: false,
    },
    quotas: {
      max_users: 50,
      max_agents: 20,
      max_events_per_day: 500000,
      max_integrations: 10,
      max_storage_gb: 250
    },
    policy: {
      allowed_environments: ["DEV", "STAGING", "PROD"],
      allowed_integrations: ["slack", "teams"],
      approval_required_for_high_risk: true,
      data_residency_region: "US-West"
    },
    usage: {
      users: 48,
      agents: 12,
      events_today: 310000,
      integrations: 6,
      storage_gb: 130
    },
    lifecycle: {
      created_at: "2026-04-12T08:00:00Z",
      updated_at: "2026-06-24T11:00:00Z"
    }
  },
  {
    tenant_id: "wayne-ent",
    name: "Wayne Enterprises",
    status: "suspended",
    plan: "regulated",
    admins: [
      { user_id: "usr-wayne-1", name: "Lucius Fox", email: "lucius@wayne.com" }
    ],
    isolation: {
      namespace: "wayne-vault",
      data_partition_key: "part-wayne-88",
      dedicated_runtime: true,
      dedicated_key_material: true,
      cross_tenant_access_allowed: false,
    },
    quotas: {
      max_users: 100,
      max_agents: 40,
      max_events_per_day: 1200000,
      max_integrations: 15,
      max_storage_gb: 500
    },
    policy: {
      allowed_environments: ["DEV", "STAGING", "PROD"],
      allowed_integrations: ["slack", "github", "jira"],
      approval_required_for_high_risk: true,
      data_residency_region: "US-East"
    },
    usage: {
      users: 42,
      agents: 14,
      events_today: 280000,
      integrations: 10,
      storage_gb: 160
    },
    lifecycle: {
      created_at: "2026-03-01T09:00:00Z",
      suspended_at: "2026-06-24T11:45:00Z",
      updated_at: "2026-06-24T11:45:00Z"
    }
  },
  {
    tenant_id: "umbrella-corp",
    name: "Umbrella Corp",
    status: "active",
    plan: "enterprise",
    admins: [
      { user_id: "usr-umb-1", name: "Albert Wesker", email: "wesker@umbrella.com" }
    ],
    isolation: {
      namespace: "umbrella-lab",
      data_partition_key: "part-umbrella-66",
      dedicated_runtime: true,
      dedicated_key_material: true,
      cross_tenant_access_allowed: false,
    },
    quotas: {
      max_users: 50,
      max_agents: 15,
      max_events_per_day: 500000,
      max_integrations: 5,
      max_storage_gb: 300
    },
    policy: {
      allowed_environments: ["STAGING", "PROD"],
      allowed_integrations: ["slack"],
      approval_required_for_high_risk: true,
      data_residency_region: "Other"
    },
    usage: {
      users: 30,
      agents: 8,
      events_today: 210000,
      integrations: 3,
      storage_gb: 140
    },
    lifecycle: {
      created_at: "2026-05-10T08:00:00Z",
      updated_at: "2026-06-24T09:00:00Z"
    }
  }
];
