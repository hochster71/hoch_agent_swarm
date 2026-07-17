/**
 * lib/synthesis-engine.ts
 *
 * NEXUS Commander's Synthesis Engine — Layer 10 of the Governor.
 *
 * Synthesises all 9 layers' findings into a single Commander's Intelligence
 * Assessment (CIA): threat level, headline, executive summary, key threats,
 * key developments, recommended actions, and foresight signals.
 *
 * This is the "final output" of one complete governor cycle — the single
 * document a commander reads before making operational decisions.
 *
 * Also provides ORACLE-9 prediction calibration: logs predictions and
 * evaluates them once their time window expires.
 */

import { createClient } from '@supabase/supabase-js'
import type { GovernorReport } from './governor'
import { safeOpenAIChatCompletion } from '@/lib/openai-safe'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'http://localhost:54321',
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? 'placeholder-service-key',
)

// ── Types ─────────────────────────────────────────────────────────────────────

export type ThreatLevel = 'CRITICAL' | 'HIGH' | 'ELEVATED' | 'MODERATE' | 'LOW'

export interface KeyThreat {
  label:    string
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW'
  detail:   string
}

export interface KeyDevelopment {
  domain:       string
  headline:     string
  significance: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface RecommendedAction {
  priority: 1 | 2 | 3
  action:   string
  rationale: string
}

export interface ForesightSignalSummary {
  horizon:     string
  prediction:  string
  confidence:  number
}

export interface NexusAssessment {
  id?:                 string
  cycleId?:            string
  conflictDay:         number
  threatLevel:         ThreatLevel
  headline:            string
  executiveSummary:    string
  keyThreats:          KeyThreat[]
  keyDevelopments:     KeyDevelopment[]
  recommendedActions:  RecommendedAction[]
  foresightSignals:    ForesightSignalSummary[]
  confidenceScore:     number
  modelUsed:           string
  layersCompleted:     number
  totalEscalations:    number
  urgentEscalations:   number
  entitiesExtracted:   number
  visualsGenerated:    number
  createdAt?:          string
}

export interface SynthesisStats {
  totalAssessments:   number
  lastAssessmentAt:   string | null
  currentThreatLevel: ThreatLevel
  avgConfidence:      number
  recentByThreatLevel: Record<ThreatLevel, number>
}

// ── Threat-level derivation (heuristic) ──────────────────────────────────────

function deriveThreatLevel(
  urgentEscalations: number,
  totalEscalations:  number,
  entitiesExtracted: number,
): ThreatLevel {
  if (urgentEscalations >= 4 || totalEscalations >= 12) return 'CRITICAL'
  if (urgentEscalations >= 2 || totalEscalations >= 7)  return 'HIGH'
  if (urgentEscalations >= 1 || totalEscalations >= 4)  return 'ELEVATED'
  if (totalEscalations >= 1 || entitiesExtracted >= 5)  return 'MODERATE'
  return 'LOW'
}

// ── LLM synthesis call ────────────────────────────────────────────────────────

async function callSynthesisLLM(prompt: string): Promise<string | null> {
  return safeOpenAIChatCompletion(
    [
      {
        role: 'system',
        content: `You are NEXUS — the supreme intelligence synthesis AI for Operation Epic Fury (US-Iran 2026 conflict).
You receive live governor cycle data and produce concise, authoritative commander assessments.
Always return valid JSON with no extra keys. Be terse and military-precise.`,
      },
      { role: 'user', content: prompt },
    ],
    { model: 'gpt-4o-mini', maxTokens: 900, temperature: 0.2, timeoutMs: 25_000 },
  )
}

// ── Build synthesis prompt from governor report ───────────────────────────────

function buildSynthesisPrompt(report: GovernorReport): string {
  const urgentCodes = report.urgentEscalations.map(e => e.code).join(', ') || 'none'
  const allEscCodes = [...new Set(
    report.layerResults.flatMap(l => l.escalations.map(e => e.code))
  )].join(', ') || 'none'

  const foresightSummary = report.foresightReport
    ? `Foresight: ${report.foresightReport.signalsGenerated} signals, ` +
      `TRiSM=${report.foresightReport.tRiSMRiskLevel}, ` +
      `urgent=${report.foresightReport.urgentSignals?.length ?? 0}`
    : 'Foresight: not available'

  const layer6 = report.layerResults.find(l => l.layer === 6)
  const gapSummary = layer6?.findings['risk_summary'] ?? 'No gap analysis available'

  return `Generate a commander's intelligence assessment for Operation Epic Fury Day ${report.conflictDay}.

GOVERNOR CYCLE DATA:
- Layers completed: ${report.layersCompleted}/10
- Total escalations: ${report.totalEscalations} (urgent: ${report.urgentEscalations.length})
- Urgent codes: ${urgentCodes}
- All escalation codes: ${allEscCodes}
- Entities extracted: ${report.entitiesExtracted}
- Claims verified: ${report.claimsVerified}
- Visuals generated: ${report.visualsGenerated}
- ${foresightSummary}
- Gap analysis: ${String(gapSummary).slice(0, 200)}
- Cycle duration: ${report.totalDurationMs}ms

Return this EXACT JSON structure (no extra keys):
{
  "headline": "<one-sentence tactical headline, ≤ 15 words>",
  "executive_summary": "<3–5 sentence commander's assessment — threat status, key development, recommended posture>",
  "key_threats": [
    {"label": string, "severity": "CRITICAL"|"HIGH"|"MODERATE"|"LOW", "detail": string}
  ],
  "key_developments": [
    {"domain": string, "headline": string, "significance": "HIGH"|"MEDIUM"|"LOW"}
  ],
  "recommended_actions": [
    {"priority": 1|2|3, "action": string, "rationale": string}
  ],
  "foresight_signals": [
    {"horizon": string, "prediction": string, "confidence": 0.0-1.0}
  ],
  "confidence_score": 0.0-1.0
}

Populate key_threats (2-3 items), key_developments (2-3), recommended_actions (3 items), foresight_signals (1-2 items).
Base everything strictly on the governor cycle data above.`
}

// ── Main synthesis function ───────────────────────────────────────────────────

export async function synthesizeGovernorOutputs(
  report: GovernorReport,
): Promise<NexusAssessment> {
  const threatLevel = deriveThreatLevel(
    report.urgentEscalations.length,
    report.totalEscalations,
    report.entitiesExtracted,
  )

  // Static fallback assessment (used when OPENAI_API_KEY is unset or LLM fails)
  const fallback: NexusAssessment = {
    cycleId:      report.cycleId,
    conflictDay:  report.conflictDay,
    threatLevel,
    headline:     `Day ${report.conflictDay} — ${report.urgentEscalations.length} urgent escalations — all layers nominal`,
    executiveSummary: `Governor completed ${report.layersCompleted} of 10 layers in ${report.totalDurationMs}ms. ` +
      `${report.urgentEscalations.length} urgent escalations detected. ` +
      `${report.entitiesExtracted} entities extracted; ${report.claimsVerified} claims verified. ` +
      `Threat posture: ${threatLevel}. AI synthesis unavailable — add OPENAI_API_KEY for full NEXUS assessment.`,
    keyThreats: report.urgentEscalations.slice(0, 3).map(e => ({
      label:    e.code,
      severity: 'HIGH' as const,
      detail:   e.detail,
    })),
    keyDevelopments: [],
    recommendedActions: [{
      priority: 1,
      action:   'Verify all governor pipeline env vars are set',
      rationale: 'OPENAI_API_KEY required for AI synthesis; CRON_SECRET for scheduled heartbeats',
    }],
    foresightSignals: report.foresightReport?.urgentSignals?.slice(0, 2).map(s => ({
      horizon:    s.horizon ?? '72h',
      prediction: s.prediction,
      confidence: s.confidence,
    })) ?? [],
    confidenceScore:   0.5,
    modelUsed:         'static-fallback',
    layersCompleted:   report.layersCompleted,
    totalEscalations:  report.totalEscalations,
    urgentEscalations: report.urgentEscalations.length,
    entitiesExtracted: report.entitiesExtracted,
    visualsGenerated:  report.visualsGenerated,
  }

  // Attempt LLM synthesis
  const prompt = buildSynthesisPrompt(report)
  const rawResponse = await callSynthesisLLM(prompt)

  if (!rawResponse) return fallback

  try {
    const parsed = JSON.parse(rawResponse) as {
      headline?:            string
      executive_summary?:   string
      key_threats?:         KeyThreat[]
      key_developments?:    KeyDevelopment[]
      recommended_actions?: RecommendedAction[]
      foresight_signals?:   ForesightSignalSummary[]
      confidence_score?:    number
    }

    return {
      cycleId:      report.cycleId,
      conflictDay:  report.conflictDay,
      threatLevel,
      headline:     parsed.headline    ?? fallback.headline,
      executiveSummary: parsed.executive_summary ?? fallback.executiveSummary,
      keyThreats:          parsed.key_threats          ?? [],
      keyDevelopments:     parsed.key_developments     ?? [],
      recommendedActions:  parsed.recommended_actions  ?? [],
      foresightSignals:    parsed.foresight_signals    ?? [],
      confidenceScore:     parsed.confidence_score     ?? 0.7,
      modelUsed:           'gpt-4o-mini',
      layersCompleted:     report.layersCompleted,
      totalEscalations:    report.totalEscalations,
      urgentEscalations:   report.urgentEscalations.length,
      entitiesExtracted:   report.entitiesExtracted,
      visualsGenerated:    report.visualsGenerated,
    }
  } catch {
    return fallback
  }
}

// ── Persist assessment to Supabase ────────────────────────────────────────────

export async function storeAssessment(assessment: NexusAssessment): Promise<string | null> {
  try {
    const { data, error } = await supabase
      .from('nexus_assessments')
      .insert({
        cycle_id:            assessment.cycleId,
        conflict_day:        assessment.conflictDay,
        threat_level:        assessment.threatLevel,
        headline:            assessment.headline,
        executive_summary:   assessment.executiveSummary,
        key_threats:         assessment.keyThreats,
        key_developments:    assessment.keyDevelopments,
        recommended_actions: assessment.recommendedActions,
        foresight_signals:   assessment.foresightSignals,
        confidence_score:    assessment.confidenceScore,
        model_used:          assessment.modelUsed,
        layers_completed:    assessment.layersCompleted,
        total_escalations:   assessment.totalEscalations,
        urgent_escalations:  assessment.urgentEscalations,
        entities_extracted:  assessment.entitiesExtracted,
        visuals_generated:   assessment.visualsGenerated,
      })
      .select('id')
      .single()

    if (error) return null
    return (data as { id: string })?.id ?? null
  } catch {
    return null
  }
}

// ── Read assessments ──────────────────────────────────────────────────────────

export async function getLatestAssessment(): Promise<NexusAssessment | null> {
  try {
    const { data, error } = await supabase
      .from('nexus_assessments')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(1)
      .single()

    if (error || !data) return null
    return rowToAssessment(data as AssessmentRow)
  } catch {
    return null
  }
}

export async function getAssessmentHistory(limit = 10): Promise<NexusAssessment[]> {
  try {
    const { data, error } = await supabase
      .from('nexus_assessments')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit)

    if (error || !data) return []
    return (data as AssessmentRow[]).map(rowToAssessment)
  } catch {
    return []
  }
}

export async function getSynthesisStats(): Promise<SynthesisStats> {
  try {
    const { data, count } = await supabase
      .from('nexus_assessments')
      .select('threat_level, confidence_score, created_at', { count: 'exact' })
      .order('created_at', { ascending: false })
      .limit(50)

    const rows = (data ?? []) as { threat_level: ThreatLevel; confidence_score: number; created_at: string }[]

    const byLevel: Record<ThreatLevel, number> = {
      CRITICAL: 0, HIGH: 0, ELEVATED: 0, MODERATE: 0, LOW: 0,
    }
    let confSum = 0

    for (const r of rows) {
      byLevel[r.threat_level] = (byLevel[r.threat_level] ?? 0) + 1
      confSum += r.confidence_score ?? 0
    }

    return {
      totalAssessments:    count ?? 0,
      lastAssessmentAt:    rows[0]?.created_at ?? null,
      currentThreatLevel:  rows[0]?.threat_level ?? 'MODERATE',
      avgConfidence:       rows.length > 0 ? confSum / rows.length : 0,
      recentByThreatLevel: byLevel,
    }
  } catch {
    return {
      totalAssessments:    0,
      lastAssessmentAt:    null,
      currentThreatLevel:  'MODERATE',
      avgConfidence:       0,
      recentByThreatLevel: { CRITICAL: 0, HIGH: 0, ELEVATED: 0, MODERATE: 0, LOW: 0 },
    }
  }
}

// ── ORACLE calibration ────────────────────────────────────────────────────────

export async function logOraclePrediction(
  predictionKey: string,
  conflictDay:   number,
  threatLabel:   string,
  predictedProb: number,
  windowHours:   number,
): Promise<void> {
  try {
    const expiresAt = new Date(Date.now() + windowHours * 3_600_000).toISOString()
    await supabase.from('oracle_prediction_calibration').upsert({
      prediction_key: predictionKey,
      conflict_day:   conflictDay,
      threat_label:   threatLabel,
      predicted_prob: predictedProb,
      window_hours:   windowHours,
      expires_at:     expiresAt,
    }, { onConflict: 'prediction_key', ignoreDuplicates: true })
  } catch { /* non-fatal */ }
}

export async function evaluateExpiredPredictions(): Promise<number> {
  try {
    const { data } = await supabase
      .from('oracle_prediction_calibration')
      .select('*')
      .is('actual_outcome', null)
      .lt('expires_at', new Date().toISOString())
      .limit(5)

    if (!data?.length) return 0

    // Use LLM to evaluate whether the prediction was accurate based on available intel
    for (const pred of data as {
      id: string; prediction_key: string; threat_label: string;
      predicted_prob: number; window_hours: number
    }[]) {
      if (!process.env.OPENAI_API_KEY) {
        await supabase.from('oracle_prediction_calibration').update({
          actual_outcome:   'UNKNOWN',
          accuracy_score:   0.5,
          evaluation_notes: 'OPENAI_API_KEY not set — auto-evaluation unavailable',
          evaluated_at:     new Date().toISOString(),
        }).eq('id', pred.id)
        continue
      }

      // Get recent intel about this threat domain
      const { data: intelSnap } = await supabase
        .from('intel')
        .select('title, theater, verified')
        .ilike('title', `%${pred.threat_label.split(' ').slice(0, 2).join('%')}%`)
        .order('created_at', { ascending: false })
        .limit(5)

      const intelContext = (intelSnap ?? []).map((i: { title: string; verified: boolean }) => i.title).join('; ')

      const content = await safeOpenAIChatCompletion(
        [{
          role: 'user',
          content: `Did this threat prediction occur within its window?
Threat: "${pred.threat_label}"
Predicted probability: ${pred.predicted_prob}%
Window: ${pred.window_hours}h
Recent intel (may be empty): ${intelContext || 'none available'}

Return: {"outcome": "OCCURRED"|"DID_NOT_OCCUR"|"PARTIAL"|"UNKNOWN", "accuracy_score": 0-10, "notes": string}`,
        }],
        { model: 'gpt-4o-mini', maxTokens: 200, temperature: 0.1, timeoutMs: 10_000 },
      )

      if (content) {
        try {
          const ev = JSON.parse(content) as { outcome?: string; accuracy_score?: number; notes?: string }
          await supabase.from('oracle_prediction_calibration').update({
            actual_outcome:   ev.outcome   ?? 'UNKNOWN',
            accuracy_score:   ev.accuracy_score ?? 5.0,
            evaluation_notes: (ev.notes ?? '').slice(0, 500),
            evaluated_at:     new Date().toISOString(),
          }).eq('id', pred.id)
        } catch { /* non-fatal */ }
      }
    }

    return data.length
  } catch {
    return 0
  }
}

// ── Internal helpers ──────────────────────────────────────────────────────────

interface AssessmentRow {
  id:                  string
  cycle_id:            string | null
  conflict_day:        number
  threat_level:        string
  headline:            string
  executive_summary:   string
  key_threats:         KeyThreat[]
  key_developments:    KeyDevelopment[]
  recommended_actions: RecommendedAction[]
  foresight_signals:   ForesightSignalSummary[]
  confidence_score:    number
  model_used:          string
  layers_completed:    number
  total_escalations:   number
  urgent_escalations:  number
  entities_extracted:  number
  visuals_generated:   number
  created_at:          string
}

function rowToAssessment(row: AssessmentRow): NexusAssessment {
  return {
    id:                  row.id,
    cycleId:             row.cycle_id ?? undefined,
    conflictDay:         row.conflict_day,
    threatLevel:         (row.threat_level as ThreatLevel) ?? 'MODERATE',
    headline:            row.headline,
    executiveSummary:    row.executive_summary,
    keyThreats:          (row.key_threats as KeyThreat[])                 ?? [],
    keyDevelopments:     (row.key_developments as KeyDevelopment[])       ?? [],
    recommendedActions:  (row.recommended_actions as RecommendedAction[]) ?? [],
    foresightSignals:    (row.foresight_signals as ForesightSignalSummary[]) ?? [],
    confidenceScore:     row.confidence_score,
    modelUsed:           row.model_used,
    layersCompleted:     row.layers_completed,
    totalEscalations:    row.total_escalations,
    urgentEscalations:   row.urgent_escalations,
    entitiesExtracted:   row.entities_extracted,
    visualsGenerated:    row.visuals_generated,
    createdAt:           row.created_at,
  }
}
