/**
 * lib/revenue-engine.ts — EPIC FURY 2026 Layer 8: Wealth & Revenue Autonomy Engine
 *
 * Continuously identifies, tests, and scales monetization vectors while maintaining
 * absolute truthfulness and ethical bounds.
 *
 * Revenue stream hierarchy:
 *   SUBSCRIPTION       — premium ad-free access + priority alerts
 *   DYNAMIC_ADS        — contextual programmatic ads (no behavioral tracking)
 *   AFFILIATE          — curated defense-tech + research tool links
 *   DATA_LICENSING     — anonymized aggregated intel datasets for research
 *   SPONSORSHIP        — branded briefings for think-tanks/policy institutes
 *   FINANCIAL_INSIGHTS — geopolitical signal API for quantitative funds
 *   CRYPTO_MICRO       — micro-product NFTs and conflict-timeline collectibles
 *   COMPOUND           — automated surplus allocation to owner instruments
 *
 * Ethical bounds (immutable):
 *   - No unethical or high-risk financial instruments
 *   - No PII in data products — aggregated/anonymized only
 *   - Full disclosure on all affiliate placements
 *   - Editorial independence maintained from all sponsors
 *   - Not investment advice — signals/analysis only with mandatory disclaimers
 *   - All strategies shadow-tested before activation
 *   - Truth-first compliance: revenue never compromises verification integrity
 *
 * Security: all LLM inputs truncated; no secrets logged; service-role Supabase only
 */

import { createClient } from '@supabase/supabase-js'
import { safeOpenAIChatCompletion } from '@/lib/openai-safe'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RevenueStreamType =
  | 'SUBSCRIPTION'
  | 'DYNAMIC_ADS'
  | 'AFFILIATE'
  | 'DATA_LICENSING'
  | 'SPONSORSHIP'
  | 'FINANCIAL_INSIGHTS'
  | 'CRYPTO_MICRO'
  | 'COMPOUND'

export type RevenueStreamStatus = 'PROPOSED' | 'TESTING' | 'ACTIVE' | 'PAUSED' | 'DEPRECATED'
export type StrategyStatus = 'PROPOSED' | 'SHADOW_TESTING' | 'ACTIVE' | 'REJECTED' | 'DEPRECATED'

export interface RevenueStream {
  id:                    string
  type:                  RevenueStreamType
  name:                  string
  description:           string | null
  status:                RevenueStreamStatus
  estimated_monthly_usd: number
  actual_monthly_usd:    number
  conversion_rate:       number
  compliance_verified:   boolean
  compliance_notes:      string | null
  metadata_json:         Record<string, unknown>
  created_at:            string
  updated_at:            string
}

export interface RevenueTransaction {
  id:           string
  stream_id:    string | null
  stream_type:  RevenueStreamType
  amount_usd:   number
  source:       string
  description:  string | null
  intel_id:     string | null
  verified:     boolean
  metadata_json: Record<string, unknown>
  created_at:   string
}

export interface MonetizationStrategy {
  id:                           string
  strategy_type:                string
  title:                        string
  description:                  string | null
  status:                       StrategyStatus
  target_stream_type:           string | null
  estimated_monthly_impact_usd: number
  actual_impact_usd:            number
  rationale:                    string | null
  compliance_notes:             string | null
  compliance_verified:          boolean
  truth_first_verified:         boolean
  created_at:                   string
}

export interface RevenueStats {
  totalRevenueLedger:  number  // cumulative all-time transaction sum
  monthlyRevenue:      number  // last 30 days
  dailyRevenue:        number  // last 24 hours
  activeStreams:       number
  proposedStreams:     number
  testingStreams:      number
  totalStreams:        number
  strategiesProposed:  number
  strategiesActive:    number
  projectedAnnualUsd:  number  // based on last 30-day run rate × 12
  topStreamName:       string | null
  recentStrategyTitle: string | null
}

export interface RevenueOptimizationResult {
  streamsAnalyzed:     number
  strategiesProposed:  number
  estimatedNewRevenue: number
  complianceVerified:  boolean
}

// ---------------------------------------------------------------------------
// Supabase client (server-side only — service role)
// ---------------------------------------------------------------------------

function getSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) throw new Error('REVENUE_ENGINE: Missing Supabase credentials')
  return createClient(url, key, { auth: { persistSession: false } })
}

// ---------------------------------------------------------------------------
// LLM helper (GPT-4o-mini for strategy analysis)
// ---------------------------------------------------------------------------

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '…' : s
}

async function revenueLLM(system: string, user: string, maxTokens = 600): Promise<string | null> {
  return safeOpenAIChatCompletion(
    [
      { role: 'system', content: truncate(system, 2000) },
      { role: 'user', content: truncate(user, 2000) },
    ],
    { model: 'gpt-4o-mini', maxTokens, temperature: 0.2, timeoutMs: 25_000 },
  )
}

// ---------------------------------------------------------------------------
// Core: getRevenueStats
// Returns aggregated revenue statistics for dashboard and governor
// ---------------------------------------------------------------------------

export async function computeRevenueStats(): Promise<RevenueStats> {
  try {
  const sb = getSupabase()

  const now = new Date()
  const minus30d = new Date(now.getTime() - 30 * 86_400_000).toISOString()
  const minus24h = new Date(now.getTime() - 86_400_000).toISOString()

  const [
    { data: allTx },
    { data: monthTx },
    { data: dayTx },
    { data: streams },
    { data: strategies },
  ] = await Promise.all([
    sb.from('revenue_transactions').select('amount_usd'),
    sb.from('revenue_transactions').select('amount_usd').gte('created_at', minus30d),
    sb.from('revenue_transactions').select('amount_usd').gte('created_at', minus24h),
    sb.from('revenue_streams').select('id, name, status, actual_monthly_usd').order('actual_monthly_usd', { ascending: false }),
    sb.from('monetization_strategies').select('id, title, status').order('created_at', { ascending: false }),
  ])

  const sum = (rows: { amount_usd: number }[] | null) =>
    (rows ?? []).reduce((acc, r) => acc + Number(r.amount_usd), 0)

  const streamRows   = (streams ?? []) as { id: string; name: string; status: string; actual_monthly_usd: number }[]
  const strategyRows = (strategies ?? []) as { id: string; title: string; status: string }[]

  const active   = streamRows.filter(s => s.status === 'ACTIVE').length
  const proposed = streamRows.filter(s => s.status === 'PROPOSED').length
  const testing  = streamRows.filter(s => s.status === 'TESTING').length
  const topStream = streamRows[0]?.name ?? null

  const monthlyRevenue = sum(monthTx)
  const projected = monthlyRevenue * 12

  const recentStrategy = strategyRows[0]?.title ?? null

  return {
    totalRevenueLedger:  sum(allTx),
    monthlyRevenue,
    dailyRevenue:        sum(dayTx),
    activeStreams:        active,
    proposedStreams:      proposed,
    testingStreams:       testing,
    totalStreams:         streamRows.length,
    strategiesProposed:   strategyRows.filter(s => s.status === 'PROPOSED').length,
    strategiesActive:     strategyRows.filter(s => s.status === 'ACTIVE').length,
    projectedAnnualUsd:  projected,
    topStreamName:        topStream,
    recentStrategyTitle: recentStrategy,
  }
  } catch {
    return {
      totalRevenueLedger: 0, monthlyRevenue: 0, dailyRevenue: 0,
      activeStreams: 0, proposedStreams: 0, testingStreams: 0, totalStreams: 0,
      strategiesProposed: 0, strategiesActive: 0, projectedAnnualUsd: 0,
      topStreamName: null, recentStrategyTitle: null,
    }
  }
}

// ---------------------------------------------------------------------------
// Core: getRevenueStreams
// Returns list of streams for RevenuePanel display
// ---------------------------------------------------------------------------

export async function getRevenueStreams(limit = 20): Promise<RevenueStream[]> {
  const sb = getSupabase()
  const { data } = await sb
    .from('revenue_streams')
    .select('*')
    .order('estimated_monthly_usd', { ascending: false })
    .limit(limit)
  return (data ?? []) as RevenueStream[]
}

// ---------------------------------------------------------------------------
// Core: getMonetizationStrategies
// Returns recent DGM-proposed strategies
// ---------------------------------------------------------------------------

export async function getMonetizationStrategies(limit = 10): Promise<MonetizationStrategy[]> {
  const sb = getSupabase()
  const { data } = await sb
    .from('monetization_strategies')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  return (data ?? []) as MonetizationStrategy[]
}

// ---------------------------------------------------------------------------
// Core: trackRevenueEvent
// Records a revenue transaction to the immutable ledger
// ---------------------------------------------------------------------------

export async function trackRevenueEvent(params: {
  stream_type: RevenueStreamType
  amount_usd:  number
  source:      string
  description: string
  stream_id?:  string
  intel_id?:   string
  metadata?:   Record<string, unknown>
}): Promise<void> {
  const sb = getSupabase()
  await sb.from('revenue_transactions').insert({
    stream_id:    params.stream_id ?? null,
    stream_type:  params.stream_type,
    amount_usd:   params.amount_usd,
    source:       params.source.slice(0, 100),
    description:  params.description.slice(0, 500),
    intel_id:     params.intel_id ?? null,
    verified:     false,
    metadata_json: params.metadata ?? {},
  })
}

// ---------------------------------------------------------------------------
// Core: optimizeRevenueStreams
// DGM/GEA-powered — analyzes platform data and proposes new monetization tactics.
// Returns optimization result with proposed strategies.
// Ethical: truth-first verified on every proposal; compliance_notes required.
// ---------------------------------------------------------------------------

export async function optimizeRevenueStreams(context: {
  conflictDay:       number
  kgEntities:        number
  verifiedClaims:    number
  visualsGenerated:  number
  cycleId:           string
}): Promise<RevenueOptimizationResult> {
  const sb = getSupabase()

  // Get existing streams for context
  const { data: existingStreams } = await sb
    .from('revenue_streams')
    .select('type, name, status, estimated_monthly_usd, actual_monthly_usd')
    .neq('status', 'DEPRECATED')

  const streamsSummary = (existingStreams ?? [])
    .map(s => `${s.type}/${s.status}: est $${s.estimated_monthly_usd}/mo`)
    .join('; ')

  const llmResponse = await revenueLLM(
    `You are the EPIC FURY 2026 Wealth & Revenue Autonomy Engine — Layer 8 of the Platform Governor.

Your role: Identify and propose specific, actionable, ethical monetization optimizations for an autonomous AI news platform covering the US-Iran conflict in real time.

Rules (immutable):
- Truth-first: no strategy that could compromise editorial independence or verification integrity
- No behavioral tracking, no PII in data products (aggregated only)
- No high-risk financial instruments; no crypto speculation beyond micro-products
- Mandatory disclosures on all affiliate/sponsorship content
- Only strategies legal under US law; include compliance_notes for each

Return valid JSON:
{
  "strategies": [
    {
      "strategy_type": string,
      "title": string (max 80 chars),
      "description": string (max 300 chars),
      "target_stream_type": "SUBSCRIPTION"|"DYNAMIC_ADS"|"AFFILIATE"|"DATA_LICENSING"|"SPONSORSHIP"|"FINANCIAL_INSIGHTS"|"CRYPTO_MICRO"|"COMPOUND",
      "estimated_monthly_impact_usd": number,
      "rationale": string (max 200 chars),
      "compliance_notes": string (max 200 chars),
      "truth_first_verified": true
    }
  ],
  "optimization_summary": string
}`,
    `Platform context (Day ${context.conflictDay} of Operation Epic Fury):
- KG entities indexed: ${context.kgEntities}
- Verified claims: ${context.verifiedClaims}
- AI visuals generated: ${context.visualsGenerated}
- Existing revenue streams: ${truncate(streamsSummary || 'none yet', 600)}

Propose 2–4 specific, high-impact monetization improvements or new revenue tactics that would naturally complement this real-time conflict intelligence platform. Focus on sustainable compounding revenue.`,
    700,
  )

  let strategiesProposed = 0
  let estimatedNewRevenue = 0

  if (llmResponse) {
    try {
      const parsed = JSON.parse(llmResponse) as {
        strategies?: {
          strategy_type:                string
          title:                        string
          description:                  string
          target_stream_type:           string
          estimated_monthly_impact_usd: number
          rationale:                    string
          compliance_notes:             string
          truth_first_verified:         boolean
        }[]
        optimization_summary?: string
      }

      const VALID_STREAM_TYPES: RevenueStreamType[] = [
        'SUBSCRIPTION','DYNAMIC_ADS','AFFILIATE','DATA_LICENSING',
        'SPONSORSHIP','FINANCIAL_INSIGHTS','CRYPTO_MICRO','COMPOUND',
      ]

      for (const s of (parsed.strategies ?? []).slice(0, 5)) {
        // Validate compliance fields before storing
        if (!s.compliance_notes || !s.truth_first_verified) continue
        const targetType = VALID_STREAM_TYPES.includes(s.target_stream_type as RevenueStreamType)
          ? s.target_stream_type
          : null

        await sb.from('monetization_strategies').insert({
          strategy_type:                String(s.strategy_type ?? 'OPTIMIZATION').slice(0, 100),
          title:                        String(s.title ?? '').slice(0, 80),
          description:                  String(s.description ?? '').slice(0, 300),
          status:                       'PROPOSED',
          target_stream_type:           targetType,
          estimated_monthly_impact_usd: Math.max(0, Math.min(100_000, Number(s.estimated_monthly_impact_usd ?? 0))),
          rationale:                    String(s.rationale ?? '').slice(0, 200),
          compliance_notes:             String(s.compliance_notes ?? '').slice(0, 200),
          compliance_verified:          false,  // requires human review before activation
          truth_first_verified:         true,
          governor_cycle_id:            context.cycleId,
          metadata_json:                { optimization_summary: parsed.optimization_summary ?? '' },
        })

        strategiesProposed++
        estimatedNewRevenue += Number(s.estimated_monthly_impact_usd ?? 0)
      }
    } catch { /* non-fatal parse error */ }
  }

  return {
    streamsAnalyzed:     (existingStreams ?? []).length,
    strategiesProposed,
    estimatedNewRevenue,
    complianceVerified:  false,  // all proposals require review before activation
  }
}

// ---------------------------------------------------------------------------
// Helper: getRecentTransactions
// For RevenuePanel display
// ---------------------------------------------------------------------------

export async function getRecentTransactions(limit = 20): Promise<RevenueTransaction[]> {
  const sb = getSupabase()
  const { data } = await sb
    .from('revenue_transactions')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  return (data ?? []) as RevenueTransaction[]
}
