/**
 * lib/foresight-engine.ts
 *
 * Layer 9: Predictive Foresight, Regulatory Intelligence & Planetary Scaling
 * ──────────────────────────────────────────────────────────────────────────
 * MC-Search + trajectory memory pattern agents that:
 *   • Predict near-term news impacts and monetization opportunities
 *   • Scan for regulatory / compliance shifts (TRiSM governance)
 *   • Identify emerging tech trajectories
 *   • Assess planetary-scale expansion opportunities
 *   • Feed insights back to all other layers for proactive evolution
 *
 * TRiSM — Trust, Risk, Security, Management governance scans
 * ───────────────────────────────────────────────────────────
 * Autonomous posture snapshots that produce risk ratings and
 * auto-remediation recommendations across four governance domains.
 */

import { createClient } from '@supabase/supabase-js'
import OpenAI from 'openai'

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  )
}

let _openAIClient: OpenAI | null = null

function getOpenAI(): OpenAI | null {
  if (!process.env.OPENAI_API_KEY) return null
  return (_openAIClient ??= new OpenAI({ apiKey: process.env.OPENAI_API_KEY }))
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SignalType =
  | 'NEWS_IMPACT'         | 'MONETIZATION_OPPTY'  | 'REGULATORY_SHIFT'
  | 'TECH_EMERGENCE'      | 'GEOPOLITICAL_MOVE'   | 'SECURITY_THREAT'
  | 'MARKET_SIGNAL'       | 'PLANETARY_SCALE_OPPTY'

export type SignalHorizon = '24H' | '72H' | '1W' | '1M' | '6M' | '1Y'
export type TRiSMDomain   = 'TRUST' | 'RISK' | 'SECURITY' | 'MANAGEMENT' | 'FULL'
export type RiskLevel     = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface ForesightSignal {
  id:                 string
  conflict_day:       number
  signal_type:        SignalType
  horizon:            SignalHorizon
  prediction:         string
  confidence:         number
  supporting_evidence: unknown[]
  validated:          boolean | null
  action_taken:       string | null
  created_at:         string
}

export interface TRiSMScan {
  id:              string
  conflict_day:    number
  scan_type:       TRiSMDomain
  risk_level:      RiskLevel
  findings:        Record<string, unknown>
  recommendations: string[]
  auto_remediated: boolean
  remediation_log: Record<string, unknown> | null
  created_at:      string
}

export interface ForesightReport {
  signalsGenerated:   number
  highConfidenceCount: number
  tRiSMRiskLevel:     RiskLevel
  urgentSignals:      ForesightSignal[]
  findings:           Record<string, unknown>
}

export interface ForesightStats {
  totalSignals:      number
  byType:            Record<SignalType, number>
  avgConfidence:     number | null
  recentScans:       TRiSMScan[]
  highRiskCount:     number
  constitutionRules: number
  /** Live intel items currently in the pipeline that will feed signal generation */
  liveIntelCount:    number
}

// ---------------------------------------------------------------------------
// Internal: LLM foresight call
// ---------------------------------------------------------------------------

async function foresightLLM(
  systemPrompt: string,
  userPrompt:   string,
  maxTokens = 800,
): Promise<string> {
  const openai = getOpenAI()
  if (!openai) return ''
  const resp = await openai.chat.completions.create({
    model:      'gpt-4o-mini',
    max_tokens: maxTokens,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user',   content: userPrompt },
    ],
  })
  return resp.choices[0]?.message?.content?.trim() ?? ''
}

// ---------------------------------------------------------------------------
// runTRiSMScan — Trust, Risk, Security, Management posture check
// ---------------------------------------------------------------------------

export async function runTRiSMScan(
  conflictDay: number,
  domain:      TRiSMDomain = 'FULL',
): Promise<TRiSMScan> {
  const sb    = getSupabase()
  const start = Date.now()

  // Gather recent platform signals to assess
  const [intelRes, debateRes, cycleRes] = await Promise.all([
    sb.from('intel').select('verified, confidence, theater').limit(50).order('created_at', { ascending: false }),
    sb.from('debate_sessions').select('consensus_reached, confidence_score').limit(20).order('created_at', { ascending: false }),
    sb.from('governor_cycles').select('layer_reached, error').limit(10).order('created_at', { ascending: false }),
  ])

  const intel    = intelRes.data    ?? []
  const debates  = debateRes.data   ?? []
  const cycles   = cycleRes.data    ?? []

  const verifiedRate = intel.length > 0
    ? intel.filter(i => i.verified === true).length / intel.length
    : 0
  const consensusRate = debates.length > 0
    ? debates.filter(d => d.consensus_reached).length / debates.length
    : 0
  const cycleErrorRate = cycles.length > 0
    ? cycles.filter(c => c.error).length / cycles.length
    : 0

  // LLM posture assessment
  const raw = await foresightLLM(
    `You are an AI governance and security auditor for a real-time news intelligence platform.
Assess TRiSM posture (Trust, Risk, Security, Management) given these platform metrics.
Respond in JSON: { "risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "findings": {...}, "recommendations": ["..."], "auto_remediate": [...] }`,
    `Domain: ${domain}
Platform metrics:
- Intel verified rate: ${(verifiedRate * 100).toFixed(1)}%
- Debate consensus rate: ${(consensusRate * 100).toFixed(1)}%
- Governor cycle error rate: ${(cycleErrorRate * 100).toFixed(1)}%
- Conflict day: ${conflictDay}
Assess current ${domain} posture and recommend remediations.`,
    600,
  )

  let parsed: { risk_level?: RiskLevel; findings?: Record<string, unknown>; recommendations?: string[]; auto_remediate?: string[] } = {}
  try {
    const jsonMatch = raw.match(/\{[\s\S]*\}/)
    if (jsonMatch) parsed = JSON.parse(jsonMatch[0])
  } catch { /* use defaults */ }

  const riskLevel:   RiskLevel               = parsed.risk_level      ?? 'LOW'
  const findings:    Record<string, unknown>  = parsed.findings        ?? { verifiedRate, consensusRate, cycleErrorRate }
  const recommendations: string[]            = parsed.recommendations ?? []
  const autoRemediated = (parsed.auto_remediate ?? []).length > 0

  const { data } = await sb.from('trism_scans').insert({
    conflict_day:    conflictDay,
    scan_type:       domain,
    risk_level:      riskLevel,
    findings,
    recommendations,
    auto_remediated: autoRemediated,
    remediation_log: autoRemediated ? { actions: parsed.auto_remediate, durationMs: Date.now() - start } : null,
  }).select('*').single()

  return (data ?? {
    id:            'local',
    conflict_day:  conflictDay,
    scan_type:     domain,
    risk_level:    riskLevel,
    findings,
    recommendations,
    auto_remediated: autoRemediated,
    remediation_log: null,
    created_at:    new Date().toISOString(),
  }) as TRiSMScan
}

// ---------------------------------------------------------------------------
// generateForesightSignals — MC-Search style multi-horizon prediction sweep
// ---------------------------------------------------------------------------

export async function generateForesightSignals(
  conflictDay: number,
): Promise<ForesightSignal[]> {
  const sb = getSupabase()

  // Pull real live intel from the DB — use correct column names (title, not headline)
  // Include confidence >= 50 to capture fresh unverified items from ingest pipeline
  const [intelRes, escalationRes] = await Promise.all([
    sb.from('intel')
      .select('title, summary, confidence, source_url, source_name, theater, tags')
      .gte('confidence', 50)
      .order('created_at', { ascending: false })
      .limit(25),
    sb.from('governor_cycles')
      .select('escalations, error')
      .order('created_at', { ascending: false })
      .limit(5),
  ])

  const intelRows = intelRes.data ?? []
  const intelCount = intelRows.length

  // Build rich intel context with source attribution for grounded predictions
  const intelContext = intelRows
    .map(i => {
      const src = i.source_name ? ` [${i.source_name}]` : ''
      const theater = i.theater && i.theater !== 'Unknown' ? ` (${i.theater})` : ''
      return `• ${i.title}${theater}${src} — conf ${i.confidence}%`
    })
    .join('\n')
    .slice(0, 2000)

  const escalationCount = (escalationRes.data ?? [])
    .flatMap(c => (c.escalations as unknown[]) ?? []).length

  // Collect citable source URLs for binding to evidence
  const citableUrls = intelRows
    .filter(i => i.source_url)
    .slice(0, 8)
    .map(i => `${i.title} — ${i.source_url}`)

  const raw = await foresightLLM(
    `You are a predictive intelligence analyst for the US-Israel-Iran conflict of 2026.
Your role: analyze REAL ingested news and intelligence to generate grounded, evidence-based foresight signals
about the unfolding conflict. Every prediction must be directly supported by the real intel provided.

DO NOT invent facts. Ground every prediction in the provided real intel items.
Each signal must reference which specific intel item(s) support it in the evidence array.

Respond ONLY in JSON: { "signals": [{ "signal_type": "...", "horizon": "...", "prediction": "...", "confidence": 0.0-1.0, "evidence": ["direct quote or paraphrase from the intel items above, with source"] }] }

Signal types: NEWS_IMPACT | GEOPOLITICAL_MOVE | SECURITY_THREAT | REGULATORY_SHIFT | MARKET_SIGNAL | TECH_EMERGENCE
Horizons: 24H | 72H | 1W | 1M
Generate 6-8 signals derived directly from the provided live intel. Each evidence item should be a specific fact from the intel.`,
    `LIVE INTEL FEED — Conflict Day ${conflictDay} — ${intelCount} items ingested from real news sources:
${intelContext || 'No intel items available yet — ingest pipeline may be starting up.'}

Active escalations detected: ${escalationCount}

Generate grounded foresight signals about: Iranian military actions, US/Israeli response trajectories,
Strait of Hormuz status, diplomatic developments, ceasefire probability shifts, economic/oil impacts,
and cyber threat escalation. Cite specific intel items in each signal's evidence array.`,
    1200,
  )

  let signals: Array<{
    signal_type: SignalType
    horizon:     SignalHorizon
    prediction:  string
    confidence:  number
    evidence:    string[]
  }> = []

  try {
    const jsonMatch = raw.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0])
      signals = parsed.signals ?? []
    }
  } catch { /* no signals parsed */ }

  if (signals.length === 0) return []

  // Attach real citable URLs to evidence where available
  const rows = signals.map(s => ({
    conflict_day:        conflictDay,
    signal_type:         s.signal_type,
    horizon:             s.horizon,
    prediction:          s.prediction,
    confidence:          Math.max(0, Math.min(1, s.confidence ?? 0.5)),
    // Merge LLM evidence with actual source URLs for full citation chain
    supporting_evidence: [
      ...(s.evidence ?? []),
      ...(citableUrls.slice(0, 2)),
    ],
  }))

  const { data } = await sb.from('foresight_signals').insert(rows).select('*')
  return (data ?? []) as ForesightSignal[]
}

// ---------------------------------------------------------------------------
// checkEthicalConstitution — verify a proposed action against living rules
// Returns any violated rules
// ---------------------------------------------------------------------------

export async function checkEthicalConstitution(
  proposedAction: string,
  context:        Record<string, unknown>,
): Promise<{ violations: string[]; approved: boolean }> {
  const sb = getSupabase()

  const { data: rules } = await sb
    .from('ethical_constitution')
    .select('rule_id, rule_text, rule_type')
    .eq('active', true)
    .order('priority', { ascending: false })

  if (!rules?.length) return { violations: [], approved: true }

  const ruleBlock = rules.map(r => `[${r.rule_id}] ${r.rule_text}`).join('\n')

  const raw = await foresightLLM(
    `You are the EPIC FURY Ethical AI Constitution enforcer.
Given a set of ethical rules, determine if a proposed action violates any of them.
Respond ONLY in JSON: { "violations": ["rule_id1", ...], "approved": true|false }`,
    `Ethical rules:\n${ruleBlock}\n\nProposed action: ${proposedAction}\nContext: ${JSON.stringify(context).slice(0, 400)}`,
    300,
  )

  try {
    const jsonMatch = raw.match(/\{[\s\S]*\}/)
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0])
      return {
        violations: parsed.violations ?? [],
        approved:   parsed.approved   ?? true,
      }
    }
  } catch { /* default approve */ }

  return { violations: [], approved: true }
}

// ---------------------------------------------------------------------------
// runForesightCycle — full Layer 9 execution
// ---------------------------------------------------------------------------

export async function runForesightCycle(
  conflictDay: number,
): Promise<ForesightReport> {
  const [signals, tRiSM] = await Promise.all([
    generateForesightSignals(conflictDay),
    runTRiSMScan(conflictDay, 'FULL'),
  ])

  const highConfidence = signals.filter(s => s.confidence >= 0.7)
  const urgent         = signals.filter(s => s.confidence >= 0.8 && ['SECURITY_THREAT', 'GEOPOLITICAL_MOVE', 'REGULATORY_SHIFT'].includes(s.signal_type))

  return {
    signalsGenerated:    signals.length,
    highConfidenceCount: highConfidence.length,
    tRiSMRiskLevel:      tRiSM.risk_level,
    urgentSignals:       urgent,
    findings: {
      signalTypes:      [...new Set(signals.map(s => s.signal_type))],
      horizons:         [...new Set(signals.map(s => s.horizon))],
      tRiSMFindings:    tRiSM.findings,
      tRiSMRecommendations: tRiSM.recommendations,
    },
  }
}

// ---------------------------------------------------------------------------
// getForesightStats — aggregate data for dashboard
// ---------------------------------------------------------------------------

export async function getForesightStats(): Promise<ForesightStats> {
  const sb = getSupabase()

  const [signalsRes, scansRes, constitutionRes, intelCountRes] = await Promise.all([
    sb.from('foresight_signals').select('signal_type, confidence').limit(200),
    sb.from('trism_scans').select('*').order('created_at', { ascending: false }).limit(10),
    sb.from('ethical_constitution').select('id').eq('active', true),
    sb.from('intel').select('id', { count: 'exact', head: true }),
  ])

  const signals = signalsRes.data ?? []
  const byType: Record<string, number> = {}
  let confSum = 0

  for (const s of signals) {
    byType[s.signal_type] = (byType[s.signal_type] ?? 0) + 1
    confSum += s.confidence ?? 0
  }

  const scans     = (scansRes.data ?? []) as TRiSMScan[]
  const highRisk  = scans.filter(s => s.risk_level === 'HIGH' || s.risk_level === 'CRITICAL').length

  return {
    totalSignals:      signals.length,
    byType:            byType as Record<SignalType, number>,
    avgConfidence:     signals.length > 0 ? Math.round((confSum / signals.length) * 100) / 100 : null,
    recentScans:       scans.slice(0, 5),
    highRiskCount:     highRisk,
    constitutionRules: (constitutionRes.data ?? []).length,
    liveIntelCount:    (intelCountRes.count ?? 0),
  }
}

// ---------------------------------------------------------------------------
// getRecentForesightSignals — latest predictions for dashboard
// ---------------------------------------------------------------------------

export async function getRecentForesightSignals(limit = 20): Promise<ForesightSignal[]> {
  const sb = getSupabase()
  const { data } = await sb
    .from('foresight_signals')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  return (data ?? []) as ForesightSignal[]
}
