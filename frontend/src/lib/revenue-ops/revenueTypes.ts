export type PartnerTier = "strategic" | "technology" | "reseller" | "consulting";

export type PartnerRecord = {
  partner_id: string;
  name: string;
  tier: PartnerTier;
  referred_customers_count: number;
  influenced_arr_usd: number;
  certification_status: "certified" | "pending" | "expired";
  joined_at: string;
};

export type PricingPlan = {
  plan_id: string;
  name: string;
  base_price_monthly_usd: number;
  included_agents: number;
  extra_agent_price_monthly_usd: number;
};

export type RevenueSnapshot = {
  mrr_usd: number;
  arr_usd: number;
  customers_count: number;
  average_contract_value_usd: number;
  nps_score: number;
};
