import { PartnerRecord, PricingPlan, RevenueSnapshot } from "./revenueTypes";

export const initialPartners: PartnerRecord[] = [
  {
    partner_id: "part-01",
    name: "Skyline Cloud Swarms Corp",
    tier: "strategic",
    referred_customers_count: 14,
    influenced_arr_usd: 480000,
    certification_status: "certified",
    joined_at: "2025-01-15T09:00:00Z"
  },
  {
    partner_id: "part-02",
    name: "Helix DevOps consulting",
    tier: "consulting",
    referred_customers_count: 6,
    influenced_arr_usd: 180000,
    certification_status: "certified",
    joined_at: "2025-04-10T11:30:00Z"
  },
  {
    partner_id: "part-03",
    name: "Apex AI Platforms Ltd",
    tier: "technology",
    referred_customers_count: 8,
    influenced_arr_usd: 320000,
    certification_status: "pending",
    joined_at: "2025-11-20T08:00:00Z"
  },
  {
    partner_id: "part-04",
    name: "Vortex Reseller Network",
    tier: "reseller",
    referred_customers_count: 3,
    influenced_arr_usd: 90000,
    certification_status: "expired",
    joined_at: "2024-06-15T14:00:00Z"
  }
];

export const initialPlans: PricingPlan[] = [
  {
    plan_id: "plan-startup",
    name: "Startup Swarm Plan",
    base_price_monthly_usd: 499,
    included_agents: 10,
    extra_agent_price_monthly_usd: 49
  },
  {
    plan_id: "plan-growth",
    name: "Growth Swarm Tier",
    base_price_monthly_usd: 1499,
    included_agents: 40,
    extra_agent_price_monthly_usd: 39
  },
  {
    plan_id: "plan-enterprise",
    name: "Enterprise Dedicated Mesh",
    base_price_monthly_usd: 4999,
    included_agents: 150,
    extra_agent_price_monthly_usd: 29
  }
];

export const initialSnapshot: RevenueSnapshot = {
  mrr_usd: 135400,
  arr_usd: 1624800,
  customers_count: 84,
  average_contract_value_usd: 19342,
  nps_score: 74
};

export const initialStrategicPriorities = [
  { priority_id: "p-01", title: "Automate Onboarding Pipelines", weight: "high", progress: 85 },
  { priority_id: "p-02", title: "Expand Channel Partner Pipeline", weight: "medium", progress: 60 },
  { priority_id: "p-03", title: "Reduce Multi-Tenant CPU Overhead", weight: "high", progress: 45 },
  { priority_id: "p-04", title: "Roll Out Dedicated DB Connects", weight: "low", progress: 95 }
];
