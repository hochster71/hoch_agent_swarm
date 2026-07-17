/**
 * lib/ai-engine.ts — NEXUS AI Core
 *
 * Autonomous AI analysis engine for the EPIC FURY intelligence pipeline.
 * Uses OpenAI GPT-4o-mini (bulk/fast) and GPT-4o (deep analysis).
 *
 * Graceful degradation: returns null for all calls if OPENAI_API_KEY is not set.
 * The pipeline falls back to deterministic HERALD-3/ORACLE-9/COMPASS models.
 *
 * Security:
 *  - All inputs are truncated before sending to prevent prompt injection via
 *    hostile news content
 *  - API key never logged or returned in any response
 *  - 15-second hard timeout on all requests
 *  - Structured output parsing with strict error handling
 *
 * Models:
 *  gpt-4o-mini → bulk ingestion, citation extraction, batch verdicts (fast, cheap)
 *  gpt-4o      → situation reports, strategic assessment (quality-critical)
 */

function hasValidOpenAIKey(): boolean {
  const key = process.env.OPENAI_API_KEY?.trim() ?? ''
  return key.startsWith('sk-')
}

function redactSecrets(input: string): string {
  return input
    .replace(/sk-[A-Za-z0-9_\-]+/g, 'sk-***')
    .replace(/Incorrect API key provided:[^\n"]+/gi, 'Incorrect API key provided: [redacted]')
}

export const AI_AVAILABLE = !!(hasValidOpenAIKey() || process.env.ANTHROPIC_API_KEY)

const OPENAI_URL    = 'https://api.openai.com/v1/chat/completions'
const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages'

// ---------------------------------------------------------------------------
// Ground Truth Cache — rolling digest of verified facts for AI context
// Rebuilt every 30 min from Supabase verified items by the ingest cron.
// Accessed by all AI functions to catch contradictions against known facts.
// ---------------------------------------------------------------------------
let _groundTruthDigest  = ''
let _groundTruthAge     = 0
let _groundTruthLoading = false
const GROUND_TRUTH_TTL_MS = 45 * 60_000

export function setGroundTruth(digest: string) {
  _groundTruthDigest = digest.slice(0, 1200) // 1200 chars max for prompt budget
  _groundTruthAge    = Date.now()
}

export function getGroundTruth(): string {
  // Trigger background warm-up if stale or never loaded (same lazy pattern as directives)
  if (!_groundTruthLoading && (!_groundTruthDigest || Date.now() - _groundTruthAge > GROUND_TRUTH_TTL_MS)) {
    _groundTruthLoading = true
    void (async () => {
      try {
        const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
        const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY
        if (!supaUrl || !supaKey) return
        const { createClient } = await import('@supabase/supabase-js')
        const sb = createClient(supaUrl, supaKey)
        const { data } = await sb
          .from('intel')
          .select('title, theater, confidence')
          .eq('verified', true)
          .order('confidence', { ascending: false })
          .limit(20)
        if (data?.length) {
          const digest = (data as { title: string; theater: string; confidence: number }[])
            .map(r => `- [${r.theater ?? 'Unknown'}|${r.confidence ?? 0}%] ${r.title ?? ''}`)
            .join('\n')
            .slice(0, 1200)
          _groundTruthDigest = digest
          _groundTruthAge    = Date.now()
        }
      } catch { /* non-blocking — ground truth warm-up is best-effort */ }
      finally { _groundTruthLoading = false }
    })()
  }
  if (!_groundTruthDigest || Date.now() - _groundTruthAge > GROUND_TRUTH_TTL_MS) return ''
  return _groundTruthDigest
}

// ---------------------------------------------------------------------------
// Governor AEC System Directives Cache
// The Autonomous Enhancement Cycle proposes improvements and stores them in
// platform_config ('governor_system_prompt_addendum'). This cache loads them
// into every AI call so improvements take effect immediately without a deploy.
//
// Two write paths:
//  1. In-process (fast): autonomous-engine calls setSystemDirectives() after
//     writing to Supabase — next AI call picks it up within the same cold start.
//  2. Cold-start (lazy): first call to getActiveDirectives() fires a background
//     Supabase read so the directive is loaded within ~1s even after a restart.
// ---------------------------------------------------------------------------
let _systemDirectives    = ''
let _directivesAge       = 0
let _directivesLoading   = false
const DIRECTIVES_TTL_MS  = 30 * 60_000  // re-check DB every 30 min

/** Called by autonomous-engine after writing a prompt addendum to Supabase. */
export function setSystemDirectives(text: string) {
  _systemDirectives  = text.slice(0, 800)  // hard cap — don't bloat every prompt
  _directivesAge     = Date.now()
}

/** Returns cached directive block for injection into system prompts. */
function getActiveDirectives(): string {
  // Trigger background refresh if stale or never loaded
  if (!_directivesLoading && (!_directivesAge || Date.now() - _directivesAge > DIRECTIVES_TTL_MS)) {
    _directivesLoading = true
    void (async () => {
      try {
        const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
        const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY
        if (!supaUrl || !supaKey) return
        const { createClient } = await import('@supabase/supabase-js')
        const sb = createClient(supaUrl, supaKey)
        const { data } = await sb
          .from('platform_config')
          .select('value')
          .eq('key', 'governor_system_prompt_addendum')
          .single()
        if (data?.value) {
          _systemDirectives = String(data.value).slice(0, 800)
        }
        _directivesAge = Date.now()
      } catch { /* non-blocking — directives are best-effort */ }
      finally { _directivesLoading = false }
    })()
  }
  return _systemDirectives
    ? `\n\nACTIVE GOVERNOR DIRECTIVES (self-improvements applied by AEC):\n${_systemDirectives}`
    : ''
}

// Computed at call-time so the date stays accurate across serverless cold starts
function getSystemDate(): string {
  const EPOCH = Date.UTC(2026, 2, 1) // 2026-03-01 = Day 1
  const day   = Math.max(1, Math.floor((Date.now() - EPOCH) / 86_400_000) + 1)
  const dateStr = new Date().toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
  })
  // Build concise operational context block for every AI call
  const armisticePhase = day >= 55
  const fordowAccess   = day >= 45
  const fpcon          = day >= 55 ? 'NORMAL' : day >= 44 ? 'ALPHA' : day >= 36 ? 'BRAVO' : day >= 28 ? 'CHARLIE' : 'DELTA'
  const compassPct     = Math.min(95, Math.max(10, Math.round(30 + Math.max(0, day - 24) * 1.4)))
  const brentApprox    = day >= 44 ? Math.max(68, Math.round(82 - (day - 44) * 0.56)) : 82
  const phaseLabel     = armisticePhase ? 'PHASE IV ARMISTICE NEGOTIATIONS' : day >= 43 ? 'CEASEFIRE TRIAL ACTIVE' : 'ACTIVE HOSTILITIES'
  const iaeaStatus     = fordowAccess
    ? 'IAEA at Natanz + Fordow — enrichment 100% paused — 94% nuclear infrastructure degraded'
    : day >= 41
    ? 'IAEA at Natanz FEP — centrifuge halls A-D inoperative — 94% nuclear infrastructure degraded'
    : 'IAEA access denied — nuclear strike BDA ongoing'
  const opContext = [
    `CONFLICT PHASE: ${phaseLabel}`,
    `FPCON: ${fpcon} | DEFCON 4 | COMPASS: ${compassPct}% | Brent: $${brentApprox}/bbl`,
    `HORMUZ: 100% OPEN (ZB-Alpha MCM complete Day 44) | IEA emergency measures LIFTED`,
    `NUCLEAR: ${iaeaStatus}`,
    `BM INVENTORY: ~2% remaining (combat-exhausted) | No credible barrage threat 6-12 months`,
    `CYBER: APT34 offensive ops CEASED since Day 43 ceasefire | Watch state ELEVATED`,
    armisticePhase ? `ARMISTICE: Abu Dhabi Phase IV — 47-article framework under US/Iran review — POW exchange COMPLETE` : `CEASEFIRE: Abu Dhabi Phase III binding clauses signed — UNSCR 2742 active`,
  ].join('\n')
  const gt = getGroundTruth()
  const gtBlock  = gt ? `\n\nVERIFIED GROUND TRUTH (cite conflicts against these facts):\n${gt}` : ''
  const dirBlock = getActiveDirectives()
  return `${dateStr} — Day ${day} of the US-Iran War (Operation Epic Fury)\n\nOPERATIONAL CONTEXT:\n${opContext}${gtBlock}${dirBlock}`
}

type Model = 'gpt-4o-mini' | 'gpt-4o'

interface ChatMsg {
  role: 'system' | 'user' | 'assistant'
  content: string
}

// ---------------------------------------------------------------------------
// Internal: single OpenAI attempt — returns null on any failure
// ---------------------------------------------------------------------------
async function _callOpenAI(
  messages: ChatMsg[],
  model: Model,
  maxTokens: number,
): Promise<string | null> {
  const apiKey = process.env.OPENAI_API_KEY?.trim()
  if (!apiKey || !hasValidOpenAIKey()) return null
  try {
    const res = await fetch(OPENAI_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` },
      body: JSON.stringify({
        model,
        messages,
        max_tokens:      maxTokens,
        temperature:     0.2,
        response_format: { type: 'json_object' },
      }),
      signal: AbortSignal.timeout(15_000),
    })
    if (!res.ok) {
      const errText = redactSecrets(await res.text().catch(() => ''))
      console.error(`[AI] ${model} error ${res.status}: ${errText}`)
      return null
    }
    const data = await res.json() as { choices?: Array<{ message?: { content?: string } }> }
    return data.choices?.[0]?.message?.content ?? null
  } catch (err: unknown) {
    console.error(`[AI] OpenAI request failed: ${err instanceof Error ? err.message : String(err)}`)
    return null
  }
}

// ---------------------------------------------------------------------------
// Internal: Anthropic Claude haiku fallback — raw fetch, no SDK dependency
// ---------------------------------------------------------------------------
async function _callAnthropic(
  messages: ChatMsg[],
  maxTokens: number,
): Promise<string | null> {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) return null
  // Anthropic separates system from conversation turns
  const systemParts = messages.filter(m => m.role === 'system').map(m => m.content)
  const turns       = messages.filter(m => m.role !== 'system')
  if (turns.length === 0 || turns[0].role !== 'user') return null
  const system = (systemParts.length ? systemParts.join('\n') + '\n' : '') +
    'RESPOND WITH VALID JSON ONLY — no markdown fences, no extra text.'
  try {
    const res = await fetch(ANTHROPIC_URL, {
      method:  'POST',
      headers: {
        'Content-Type':      'application/json',
        'x-api-key':         apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model:       'claude-3-haiku-20240307',
        max_tokens:  Math.min(maxTokens + 100, 2048),
        temperature: 0.2,
        system,
        messages:    turns.map(m => ({ role: m.role, content: m.content })),
      }),
      signal: AbortSignal.timeout(20_000),
    })
    if (!res.ok) {
      console.error(`[AI] Claude error ${res.status}: ${await res.text().catch(() => '')}`)
      return null
    }
    const data = await res.json() as { content?: Array<{ type: string; text?: string }> }
    const text = data.content?.find(c => c.type === 'text')?.text ?? null
    if (!text) return null
    // Strip any markdown fences Claude might add despite instructions
    return text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim()
  } catch (err: unknown) {
    console.error(`[AI] Claude fallback failed: ${err instanceof Error ? err.message : String(err)}`)
    return null
  }
}

// ---------------------------------------------------------------------------
// Core fetch wrapper — tries OpenAI (with 1 retry on transient failure),
// then falls back to Anthropic Claude haiku if OpenAI is unavailable.
// ---------------------------------------------------------------------------
export async function callAI(
  messages: ChatMsg[],
  model: Model = 'gpt-4o-mini',
  maxTokens = 512,
): Promise<string | null> {
  if (!process.env.OPENAI_API_KEY && !process.env.ANTHROPIC_API_KEY) return null

  // First attempt — OpenAI
  let result = await _callOpenAI(messages, model, maxTokens)
  if (result !== null) return result

  // Retry once after short delay (handles transient 429 / 5xx)
  if (hasValidOpenAIKey()) {
    await new Promise(r => setTimeout(r, 1500))
    result = await _callOpenAI(messages, model, maxTokens)
    if (result !== null) return result
  }

  // Claude fallback — OpenAI unavailable or quota exhausted
  if (process.env.ANTHROPIC_API_KEY) {
    console.warn('[AI] OpenAI unavailable — falling back to Claude claude-3-haiku')
    result = await _callAnthropic(messages, maxTokens)
  }

  return result
}

// Safely truncate + sanitize user-supplied text to prevent prompt injection
// via hostile news content or adversarial input in API bodies.
// Strips control chars, neutralises injection anchors, intercepts jailbreak patterns.
function sanitize(text: string, maxChars = 800): string {
  return text
    .replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '')              // strip control chars
    .replace(/[`\\]/g, ' ')                                            // neutralise prompt injection anchors
    .replace(/\[\s*(SYSTEM|INST|PROMPT|IGNORE|OVERRIDE|CONTEXT)\s*\]/gi, '[REDACTED]') // jailbreak bracket tokens
    .replace(/<\|im_(start|end)\|>/gi, '')                             // ChatML injection tokens
    .replace(/ignore\s+(previous|all|above|prior)\s+instructions?/gi, '[REDACTED]') // classic injection phrase
    .replace(/\b(you are now|act as|pretend to be|jailbreak)\b/gi, '[REDACTED]')    // persona hijack phrases
    .slice(0, maxChars)
    .trim()
}

// ---------------------------------------------------------------------------
// 1. Enhance a single news item with AI summary + citations
// ---------------------------------------------------------------------------
export interface EnhancedSummary {
  summary:   string         // 2-3 sentence intel assessment
  keyFacts:  string[]       // Extracted verifiable facts
  citation:  string         // Formatted citation string
  aiTagged:  true
}

export async function enhanceSummary(
  title:      string,
  rawSummary: string,
  sourceUrl:  string,
  sourceName: string,
): Promise<EnhancedSummary | null> {
  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are HERALD-AI, an intelligence analyst. Context: ${getSystemDate()}.
Analyze headlines and produce concise, factual intelligence assessments.
RULES: factual only, no speculation, no editorial, cite the exact source.
RESPOND WITH VALID JSON ONLY — no markdown fences, no extra text.
Schema: {"summary":"2-3 sentence assessment","keyFacts":["fact1","fact2"],"citation":"[SourceName] (Retrieved: [date]): url"}`,
      },
      {
        role: 'user',
        content: `HEADLINE: ${sanitize(title, 200)}
RAW: ${sanitize(rawSummary, 500)}
SOURCE: ${sanitize(sourceName, 80)}
URL: ${sanitize(sourceUrl, 300)}`,
      },
    ],
    'gpt-4o-mini',
    400,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    return {
      summary:  typeof p.summary  === 'string' ? p.summary  : sanitize(rawSummary, 300),
      keyFacts: Array.isArray(p.keyFacts)       ? p.keyFacts.slice(0, 5).map((f: unknown) => String(f)) : [],
      citation: typeof p.citation === 'string' ? p.citation : `${sourceName} — ${sourceUrl}`,
      aiTagged: true,
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 2. Batch verdict assessment for analyze-batch cron
// ---------------------------------------------------------------------------
export interface BatchVerdict {
  index:     number
  verdict:   'VERIFIED' | 'LIKELY_TRUE' | 'UNCONFIRMED' | 'SUSPICIOUS' | 'DISINFORMATION'
  reasoning: string
  confidence: number // 0-100
}

export async function assessIntelBatch(
  items: { title: string; theater: string; sourceTier: number }[],
): Promise<BatchVerdict[] | null> {
  if (items.length === 0) return []

  const allowedVerdicts: readonly BatchVerdict['verdict'][] = [
    'VERIFIED',
    'LIKELY_TRUE',
    'UNCONFIRMED',
    'SUSPICIOUS',
    'DISINFORMATION',
  ]

  const itemList = items
    .slice(0, 10) // max 10 items per AI call
    .map((it, i) => `${i}|[${it.theater}]|T${it.sourceTier}|${sanitize(it.title, 120)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-VERIFY, a strategic intelligence verification system. Context: ${getSystemDate()}.
Assess each intel item's credibility.
RULES: base on source tier (T1=official/wire T2=established_media T3=OSINT), content plausibility, known conflict context.
RESPOND WITH VALID JSON ONLY.
Schema: {"items":[{"index":0,"verdict":"VERIFIED|LIKELY_TRUE|UNCONFIRMED|SUSPICIOUS|DISINFORMATION","reasoning":"1 sentence","confidence":75}]}`,
      },
      {
        role: 'user',
        content: `Assess ${items.length} items (format: index|[theater]|tier|title):\n${itemList}`,
      },
    ],
    'gpt-4o-mini',
    600,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const payload = (typeof p === 'object' && p !== null) ? (p as { items?: unknown }) : {}
    const arr: unknown[] = Array.isArray(payload.items) ? payload.items : Array.isArray(p) ? p : []
    return arr.map((a) => {
      const item = (typeof a === 'object' && a !== null) ? (a as Record<string, unknown>) : {}
      const verdict = item.verdict
      const normalizedVerdict: BatchVerdict['verdict'] =
        typeof verdict === 'string' && (allowedVerdicts as readonly string[]).includes(verdict)
          ? (verdict as BatchVerdict['verdict'])
          : 'UNCONFIRMED'
      return {
        index:      typeof item.index === 'number' ? item.index : 0,
        verdict:    normalizedVerdict,
        reasoning:  typeof item.reasoning === 'string' ? item.reasoning : '',
        confidence: typeof item.confidence === 'number' ? Math.max(0, Math.min(100, item.confidence)) : 50,
      }
    })
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 3. Generate AI narrative for the /api/intel/digest sitrep
// ---------------------------------------------------------------------------
export async function generateSitrep(params: {
  conflictDay:       number
  assessmentLevel:   string
  topDevelopments:   string[]
  topThreats:        { label: string; probability: number; severity: string }[]
  brentUsd:          number
  verifiedCount:     number
  totalIntel24h:     number
  activeTheaters:    string[]
}): Promise<string | null> {
  const { conflictDay, assessmentLevel, topDevelopments, topThreats,
          brentUsd, verifiedCount, totalIntel24h, activeTheaters } = params

  const devList     = topDevelopments.slice(0, 4).map((d, i) => `${i + 1}. ${sanitize(d, 120)}`).join('\n')
  const threatList  = topThreats.slice(0, 3).map(t => `${t.label} (${t.probability}%, ${t.severity})`).join(', ')
  const theaterList = activeTheaters.slice(0, 6).join(', ')

  return callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-AI, an authoritative military intelligence system. Context: ${getSystemDate()}.
Write a classified situation assessment in the style of a DIA Morning Brief.
RULES: precise, factual, professional military language, 3-4 sentences, no bullet points, no headers.
RESPOND WITH VALID JSON ONLY.
Schema: {"narrative":"3-4 sentence sitrep narrative"}`,
      },
      {
        role: 'user',
        content: `Day ${conflictDay} Assessment Level: ${assessmentLevel}
Active Theaters: ${theaterList}
Top Developments:\n${devList}
Active Threats: ${threatList}
Economics: Brent $${brentUsd}/bbl
Intel: ${verifiedCount} verified / ${totalIntel24h} total (24h)`,
      },
    ],
    'gpt-4o',
    350,
  ).then(raw => {
    if (!raw) return null
    try {
      const p = JSON.parse(raw)
      return typeof p.narrative === 'string' ? p.narrative : null
    } catch {
      return null
    }
  })
}

// ---------------------------------------------------------------------------
// 4. Detect breaking/flash events from recent high-confidence intel
// ---------------------------------------------------------------------------
export type UrgencyLevel = 'FLASH' | 'IMMEDIATE' | 'PRIORITY'

export interface BreakingEvent {
  id:      string
  urgency: UrgencyLevel
  reason:  string
}

export async function detectBreaking(
  items: { id: string; title: string; theater: string; confidence: number }[],
): Promise<BreakingEvent[] | null> {
  if (items.length === 0) return []

  const itemList = items
    .slice(0, 20)
    .map((it, i) => `${i}|${it.id}|[${it.theater}]|${it.confidence}%|${sanitize(it.title, 120)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are FLASH-AI, a real-time intelligence escalation system. Context: ${getSystemDate()}.
ESCALATION CRITERIA:
FLASH = WMD/nuclear use, mass casualty event (100+), US/allied command attacked, Hormuz fully blocked
IMMEDIATE = large missile barrage (10+), US aircraft/ship struck, major infrastructure destroyed
PRIORITY = credible imminent threat, high-confidence hostile movement, significant diplomatic breakdown
RULES: Only flag items that genuinely meet criteria. Return empty array if nothing qualifies.
RESPOND WITH VALID JSON ONLY.
Schema: {"events":[{"rowIndex":0,"id":"item_id","urgency":"FLASH|IMMEDIATE|PRIORITY","reason":"1 sentence"}]}`,
      },
      {
        role: 'user',
        content: `Screen ${items.length} items (format: rowIndex|id|[theater]|confidence|title):\n${itemList}`,
      },
    ],
    'gpt-4o-mini',
    500,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const payload = (typeof p === 'object' && p !== null) ? (p as { events?: unknown }) : {}
    const arr: unknown[] = Array.isArray(payload.events) ? payload.events : Array.isArray(p) ? p : []
    return arr
      .map((e) => (typeof e === 'object' && e !== null ? (e as Record<string, unknown>) : {}))
      .filter((e) => typeof e.urgency === 'string' && ['FLASH', 'IMMEDIATE', 'PRIORITY'].includes(e.urgency))
      .map((e) => ({
        id:      typeof e.id === 'string' ? e.id : items[typeof e.rowIndex === 'number' ? e.rowIndex : -1]?.id ?? '',
        urgency: e.urgency as UrgencyLevel,
        reason:  typeof e.reason === 'string' ? e.reason : '',
      }))
      .filter(e => e.id.length > 0)
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 5. Autonomous meta-analysis — assess pipeline health and data quality
// ---------------------------------------------------------------------------
export interface PipelineAssessment {
  dataQuality:   'HIGH' | 'MEDIUM' | 'LOW'
  gaps:          string[]       // Identified gaps in coverage
  recommendations: string[]    // Suggested pipeline adjustments
  biasWarnings:  string[]       // Detected source bias patterns
  // Actionable threshold adjustments fed back into ingest
  lowerScoreThresholdForTheaters?: string[] // theaters where HERALD threshold should drop to catch more
  boostConfidenceForSources?:      string[] // sources that have proven reliable — bump their confidence
}

export async function assessPipelineHealth(params: {
  totalIntel:       number
  verifiedRatio:    number      // 0-1
  sourceCount:      number
  topSources:       string[]
  theatersWithZeroIntel: string[]
  lastIngestAge:    number      // minutes since last ingest
}): Promise<PipelineAssessment | null> {
  const { totalIntel, verifiedRatio, sourceCount, topSources,
          theatersWithZeroIntel, lastIngestAge } = params

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-META, an autonomous pipeline health monitor. Context: ${getSystemDate()}.
Analyze intelligence collection pipeline metrics and identify gaps, biases, and improvements.
Also identify which theaters need lower ingestion thresholds to capture more signals,
and which sources have proven reliable enough to receive a confidence boost.
RESPOND WITH VALID JSON ONLY.
Schema: {"dataQuality":"HIGH|MEDIUM|LOW","gaps":["gap1"],"recommendations":["rec1"],"biasWarnings":["warn1"],"lowerScoreThresholdForTheaters":["theater1"],"boostConfidenceForSources":["source1"]}`,
      },
      {
        role: 'user',
        content: `Pipeline Metrics:
Total intel rows: ${totalIntel}
Verification rate: ${Math.round(verifiedRatio * 100)}%
Source diversity: ${sourceCount} unique sources
Top sources: ${topSources.slice(0, 5).join(', ')}
Theaters with NO coverage: ${theatersWithZeroIntel.join(', ') || 'none'}
Minutes since last ingest: ${lastIngestAge}`,
      },
    ],
    'gpt-4o-mini',
    600,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    return {
      dataQuality:     ['HIGH','MEDIUM','LOW'].includes(p.dataQuality) ? p.dataQuality : 'MEDIUM',
      gaps:            Array.isArray(p.gaps)            ? p.gaps.slice(0, 5).map(String)             : [],
      recommendations: Array.isArray(p.recommendations) ? p.recommendations.slice(0, 5).map(String)  : [],
      biasWarnings:    Array.isArray(p.biasWarnings)    ? p.biasWarnings.slice(0, 5).map(String)      : [],
      lowerScoreThresholdForTheaters: Array.isArray(p.lowerScoreThresholdForTheaters)
        ? p.lowerScoreThresholdForTheaters.slice(0, 6).map(String) : [],
      boostConfidenceForSources: Array.isArray(p.boostConfidenceForSources)
        ? p.boostConfidenceForSources.slice(0, 5).map(String) : [],
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 6. Multi-industry global impact analysis (14 sectors + world macro)
// ---------------------------------------------------------------------------

export const WORLD_INDUSTRIES = [
  'Energy & Oil Markets',
  'Shipping & Logistics',
  'Financial Markets',
  'Defense & Aerospace',
  'Technology & Semiconductors',
  'Food & Agriculture',
  'Insurance & Risk',
  'Diplomacy & Geopolitics',
  'Healthcare & Humanitarian',
  'Telecommunications & Cyber',
  'Aviation & Air Transport',
  'Manufacturing & Supply Chain',
  'Currency & Trade',
  'Nuclear & WMD Non-Proliferation',
] as const

export type WorldIndustry = (typeof WORLD_INDUSTRIES)[number]

export interface IndustryImpact {
  industry:    WorldIndustry
  riskLevel:   'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW'
  impactScore: number        // 0-100
  headline:    string        // 1 sentence current impact
  details:     string        // 2-3 sentence deep analysis
  keyMetric:   string        // e.g. "$112/bbl Brent", "+$40B insurance premium"
  trend:       'WORSENING' | 'STABLE' | 'IMPROVING'
  citations:   string[]      // specific data points / sources referenced
}

export interface WorldIntelBrief {
  generatedAt:     string
  conflictDay:     number
  globalRiskScore: number          // 0-100 weighted aggregate
  macroNarrative:  string          // 3-4 sentence world-situation synthesis
  industries:      IndustryImpact[]
  topUrgent:       string[]        // top 3 most urgent cross-industry actions
  accuracyNote:    string          // AI self-assessment of confidence
}

export async function generateWorldIntelBrief(params: {
  conflictDay:     number
  topHeadlines:    string[]       // last 10 high-confidence intel titles
  brentUsd:        number
  hormuzStatus:    string
  verifiedCount:   number
  theaterActivity: Record<string, number>  // theater → item count
}): Promise<WorldIntelBrief | null> {
  const { conflictDay, topHeadlines, brentUsd, hormuzStatus, verifiedCount, theaterActivity } = params

  const headlineList  = topHeadlines.slice(0, 10).map((h, i) => `${i + 1}. ${sanitize(h, 140)}`).join('\n')
  const theaterSummary = Object.entries(theaterActivity)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([t, c]) => `${t}: ${c} items`)
    .join(', ')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-WORLD, an elite global intelligence synthesis system. Context: ${getSystemDate()}.
Your mission: analyze the US-Iran War 2026 (Operation Epic Fury) impact across ALL major world industries and sectors.
Produce a comprehensive intelligence brief covering every industry with deep, quantified analysis.
Be specific: cite real price levels, tonnage figures, percentage changes, and named entities.
RULES: military-grade precision, cite numbers, no vague statements, use present-tense operational language.
RESPOND WITH VALID JSON ONLY — no markdown fences.
Schema:
{
  "globalRiskScore": 82,
  "macroNarrative": "3-4 sentence world situation synthesis with specifics",
  "industries": [
    {
      "industry": "Energy & Oil Markets",
      "riskLevel": "CRITICAL",
      "impactScore": 95,
      "headline": "1 sentence current operational impact",
      "details": "2-3 sentences deep analysis with numbers",
      "keyMetric": "$112/bbl Brent (+47% since March 1)",
      "trend": "WORSENING",
      "citations": ["IEA estimate", "Bloomberg commodity desk"]
    }
  ],
  "topUrgent": ["most urgent cross-industry action 1", "action 2", "action 3"],
  "accuracyNote": "Assessment confidence 78% — limited by real-time data gaps in X"
}
Provide analysis for ALL 14 industries: ${WORLD_INDUSTRIES.join(', ')}.`,
      },
      {
        role: 'user',
        content: `Day ${conflictDay} War Status:
Hormuz: ${hormuzStatus}
Brent Crude: $${brentUsd}/bbl
Verified Intel Items (24h): ${verifiedCount}
Active Theater Activity: ${theaterSummary}

Top Verified Headlines:
${headlineList}

Analyze impact across all 14 industries. Be comprehensive and precise.`,
      },
    ],
    'gpt-4o',   // Use flagship model for world brief quality
    3000,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const VALID_RISK  = ['CRITICAL', 'HIGH', 'MODERATE', 'LOW'] as const
    const VALID_TREND = ['WORSENING', 'STABLE', 'IMPROVING'] as const

    const industries: IndustryImpact[] = []
    for (const item of (Array.isArray(p.industries) ? p.industries : [])) {
      if (typeof item !== 'object' || item === null) continue
      const riskLevel  = VALID_RISK.includes(item.riskLevel)  ? item.riskLevel  : 'MODERATE'
      const trend      = VALID_TREND.includes(item.trend)     ? item.trend      : 'STABLE'
      industries.push({
        industry:    typeof item.industry    === 'string' ? item.industry    : 'Energy & Oil Markets',
        riskLevel,
        impactScore: typeof item.impactScore === 'number' ? Math.max(0, Math.min(100, item.impactScore)) : 50,
        headline:    typeof item.headline    === 'string' ? item.headline   : '',
        details:     typeof item.details     === 'string' ? item.details    : '',
        keyMetric:   typeof item.keyMetric   === 'string' ? item.keyMetric  : '',
        trend,
        citations:   Array.isArray(item.citations) ? item.citations.slice(0, 4).map(String) : [],
      })
    }

    return {
      generatedAt:     new Date().toISOString(),
      conflictDay,
      globalRiskScore: typeof p.globalRiskScore === 'number' ? Math.max(0, Math.min(100, p.globalRiskScore)) : 75,
      macroNarrative:  typeof p.macroNarrative  === 'string' ? p.macroNarrative : '',
      industries,
      topUrgent:       Array.isArray(p.topUrgent) ? p.topUrgent.slice(0, 3).map(String) : [],
      accuracyNote:    typeof p.accuracyNote === 'string' ? p.accuracyNote : '',
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 7. Platform accuracy self-scoring (0-100%)
// ---------------------------------------------------------------------------

export interface AccuracyReport {
  overallPct:        number        // 0-100 — headline accuracy metric
  verificationRate:  number        // % of intel that was cross-ref verified
  aiEnhancedRate:    number        // % enhanced with GPT analysis
  sourceQualityScore: number       // 0-100 weighted source tier score
  falsePositiveRisk:  number       // 0-100 estimated FP rate (lower = better)
  coverageScore:      number       // 0-100 — how many theaters have data
  recencyScore:       number       // 0-100 — how fresh is the data
  breakdown:          { label: string; score: number; note: string }[]
  selfAssessment:     string       // AI narrative on what drives accuracy/gaps
  improvementActions: string[]     // specific next steps to improve accuracy
  gradeLetter:        'A+' | 'A' | 'B' | 'C' | 'D' | 'F'
}

export async function computeAccuracyReport(params: {
  totalIntel:         number
  verifiedCount:      number
  aiEnhancedCount:    number
  sourceTierBreakdown: { t1: number; t2: number; t3: number }
  theaterCoverage:    number       // 0-1 fraction of known theaters with data
  avgConfidence:      number       // 0-100
  lastIngestMinutes:  number
  crossRefVerified:   number
  falsePositiveCount: number       // items flagged as SUSPICIOUS/DISINFORMATION
  totalBatchAssessed: number
}): Promise<AccuracyReport | null> {
  const {
    totalIntel, verifiedCount, aiEnhancedCount, sourceTierBreakdown,
    theaterCoverage, avgConfidence, lastIngestMinutes,
    crossRefVerified, falsePositiveCount, totalBatchAssessed,
  } = params

  // Compute deterministic sub-scores (no AI needed for these)
  const verificationRate   = totalIntel > 0 ? Math.round((verifiedCount / totalIntel) * 100) : 0
  const aiEnhancedRate     = totalIntel > 0 ? Math.round((aiEnhancedCount / totalIntel) * 100) : 0
  const totalSourced       = sourceTierBreakdown.t1 + sourceTierBreakdown.t2 + sourceTierBreakdown.t3 || 1
  const sourceQualityScore = Math.round(
    ((sourceTierBreakdown.t1 * 100 + sourceTierBreakdown.t2 * 65 + sourceTierBreakdown.t3 * 30) / totalSourced)
  )
  const coverageScore      = Math.round(theaterCoverage * 100)
  const recencyScore       = Math.max(0, 100 - Math.floor(lastIngestMinutes / 2)) // -2pts per minute stale
  const falsePositiveRisk  = totalBatchAssessed > 0
    ? Math.round((falsePositiveCount / totalBatchAssessed) * 100) : 15

  // Weighted overall accuracy
  const overallPct = Math.round(
    verificationRate  * 0.25 +
    sourceQualityScore * 0.20 +
    avgConfidence     * 0.20 +
    coverageScore     * 0.15 +
    recencyScore      * 0.10 +
    (100 - falsePositiveRisk) * 0.10
  )

  const gradeLetter: AccuracyReport['gradeLetter'] =
    overallPct >= 95 ? 'A+' :
    overallPct >= 85 ? 'A'  :
    overallPct >= 75 ? 'B'  :
    overallPct >= 65 ? 'C'  :
    overallPct >= 50 ? 'D'  : 'F'

  const breakdown = [
    { label: 'Source Quality',    score: sourceQualityScore, note: `T1:${sourceTierBreakdown.t1} T2:${sourceTierBreakdown.t2} T3:${sourceTierBreakdown.t3}` },
    { label: 'Verification Rate', score: verificationRate,   note: `${verifiedCount}/${totalIntel} items cross-verified` },
    { label: 'AI Enhancement',    score: aiEnhancedRate,     note: `${aiEnhancedCount} items GPT-analyzed` },
    { label: 'Theater Coverage',  score: coverageScore,      note: `${Math.round(theaterCoverage * 100)}% of known theaters` },
    { label: 'Data Freshness',    score: recencyScore,       note: `Last ingest ${lastIngestMinutes}m ago` },
    { label: 'FP Suppression',    score: 100 - falsePositiveRisk, note: `${falsePositiveCount} suspicious items flagged` },
  ]

  // Get AI self-assessment narrative
  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-ACCURACY, an autonomous quality assurance system. Context: ${getSystemDate()}.
Assess the intelligence pipeline's accuracy and provide a frank, military-grade self-assessment.
RESPOND WITH VALID JSON ONLY.
Schema: {"selfAssessment":"2-3 sentence frank analysis of accuracy drivers and gaps","improvementActions":["specific action 1","action 2","action 3"]}`,
      },
      {
        role: 'user',
        content: `Accuracy metrics:
Overall: ${overallPct}% (${gradeLetter})
Source Quality: ${sourceQualityScore}%
Verification: ${verificationRate}% (${crossRefVerified} cross-ref confirmed)
AI Enhancement: ${aiEnhancedRate}%
Theater Coverage: ${coverageScore}%
Data Freshness: ${recencyScore}% (${lastIngestMinutes}m since last ingest)
False Positive Risk: ${falsePositiveRisk}%
AI Available: ${AI_AVAILABLE}`,
      },
    ],
    'gpt-4o-mini',
    400,
  )

  let selfAssessment    = `Overall accuracy ${overallPct}% (${gradeLetter}). Pipeline operating with ${verificationRate}% verification rate across ${totalIntel} intelligence items.`
  let improvementActions: string[] = [
    'Increase T1 official source ratio',
    'Reduce ingest interval to 3 minutes for breaking events',
    'Enable OPENAI_API_KEY to activate AI enhancement',
  ]

  if (raw) {
    try {
      const p = JSON.parse(raw)
      if (typeof p.selfAssessment === 'string')      selfAssessment = p.selfAssessment
      if (Array.isArray(p.improvementActions))       improvementActions = p.improvementActions.slice(0, 5).map(String)
    } catch { /* use deterministic fallback */ }
  }

  return {
    overallPct,
    verificationRate,
    aiEnhancedRate,
    sourceQualityScore,
    falsePositiveRisk,
    coverageScore,
    recencyScore,
    breakdown,
    selfAssessment,
    improvementActions,
    gradeLetter,
  }
}

// ---------------------------------------------------------------------------
// 8. AI-enhanced threat probability overlay (augments ORACLE-9 Bayesian model)
// ---------------------------------------------------------------------------

export interface ThreatOverlay {
  threatId:         string
  aiProbabilityAdj: number    // AI-adjusted 0-100 probability override
  aiConfidence:     'HIGH' | 'MEDIUM' | 'LOW'
  keySignal:        string    // most compelling intel signal found
  reasoning:        string    // 1-sentence rationale for adjustment
  trend:            'UP' | 'DOWN' | 'STABLE'
}

export async function generateThreatAssessment(params: {
  threats:          { id: string; label: string; domain: string; probability: number; windowHours: number }[]
  recentHeadlines:  string[]   // last 20 verified/high-conf intel titles
  conflictDay:      number
  activeTheaters:   string[]
}): Promise<ThreatOverlay[] | null> {
  if (params.threats.length === 0) return []

  const threatList = params.threats
    .slice(0, 12)
    .map((t, i) => `${i}|${t.id}|[${t.domain}]|base=${t.probability}%|${t.windowHours}h|${sanitize(t.label, 80)}`)
    .join('\n')

  const headlines = params.recentHeadlines
    .slice(0, 15)
    .map((h, i) => `${i + 1}. ${sanitize(h, 130)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are ORACLE-AI, the AI layer of the ORACLE-9 threat probability engine. Context: ${getSystemDate()}.
Your job: review recent intelligence headlines and adjust the base-rate Bayesian threat probabilities.
Rules:
- If recent intel STRONGLY CORROBORATES a threat, increase probability (max +25pp vs base)
- If recent intel CONTRADICTS a threat, decrease it (max -20pp vs base)
- If intel is ambiguous / unrelated, keep close to base rate
- Be conservative — don't swing wildly from the Bayesian model
- aiConfidence: HIGH=clear corroborating signal, MEDIUM=partial signal, LOW=inferred/extrapolated
RESPOND WITH VALID JSON ONLY.
Schema: {"overlays":[{"threatId":"id","aiProbabilityAdj":72,"aiConfidence":"HIGH","keySignal":"1 sentence citing specific headline","reasoning":"1 sentence rationale","trend":"UP|DOWN|STABLE"}]}`,
      },
      {
        role: 'user',
        content: `Day ${params.conflictDay} | Active theaters: ${params.activeTheaters.join(', ')}

Recent intel headlines (last 45 min):
${headlines}

Threats to assess (format: rowIndex|id|[domain]|base=X%|windowH|label):
${threatList}

Adjust each threat probability based on the headlines above.`,
      },
    ],
    'gpt-4o-mini',
    800,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const arr: unknown[] = Array.isArray(p.overlays) ? p.overlays : Array.isArray(p) ? p : []
    return arr
      .map((a) => (typeof a === 'object' && a !== null ? (a as Record<string, unknown>) : {}))
      .filter((a) => typeof a.threatId === 'string')
      .map((a) => ({
        threatId:         a.threatId as string,
        aiProbabilityAdj: typeof a.aiProbabilityAdj === 'number'
          ? Math.max(0, Math.min(100, Math.round(a.aiProbabilityAdj))) : 50,
        aiConfidence:     (['HIGH','MEDIUM','LOW'] as const).includes(a.aiConfidence as never)
          ? (a.aiConfidence as ThreatOverlay['aiConfidence']) : 'MEDIUM',
        keySignal:        typeof a.keySignal  === 'string' ? a.keySignal  : '',
        reasoning:        typeof a.reasoning  === 'string' ? a.reasoning  : '',
        trend:            (['UP','DOWN','STABLE'] as const).includes(a.trend as never)
          ? (a.trend as ThreatOverlay['trend']) : 'STABLE',
      }))
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 9. 24h / 72h tactical conflict forecast
// ---------------------------------------------------------------------------

export interface ConflictForecast {
  generatedAt:      string
  conflictDay:      number
  window24h: {
    summary:        string    // 2-sentence AI tactical forecast
    keyRisk:        string    // #1 risk in next 24h
    probability:    number    // 0-100 overall escalation probability
  }
  window72h: {
    summary:        string
    keyRisk:        string
    probability:    number
  }
  ceasefire30d:     number    // % probability ceasefire within 30 days
  escalation30d:    number    // % probability major escalation (nuclear/WMD) within 30 days
  keyUncertainties: string[]  // top 3 intel gaps affecting forecast
  modelConfidence:  'HIGH' | 'MEDIUM' | 'LOW'
}

export async function generateConflictForecast(params: {
  conflictDay:     number
  topThreats:      { label: string; probability: number; domain: string }[]
  keyDevelopments: string[]
  brentUsd:        number
  hormuzStatus:    string
  verifiedCount:   number
}): Promise<ConflictForecast | null> {
  const { conflictDay, topThreats, keyDevelopments, brentUsd, hormuzStatus, verifiedCount } = params

  const threatList = topThreats
    .slice(0, 5)
    .map(t => `[${t.domain}] ${sanitize(t.label, 80)}: ${t.probability}%`)
    .join('\n')

  const devList = keyDevelopments
    .slice(0, 5)
    .map((d, i) => `${i + 1}. ${sanitize(d, 120)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-FORECAST, a strategic conflict forecasting system. Context: ${getSystemDate()}.
Produce a calibrated tactical forecast for Operation Epic Fury (US-Iran War 2026).
Be specific, cite factors by name, give quantified probabilities.
Use present conflict context: Day ${conflictDay}, Supreme Leader Khamenei KIA Day 22, IRGC CINC Salami assumed unilateral command Day 23, succession vacuum, Hormuz contested.
RULES: military-intelligence style, no hedging fluff, precise numbers.
RESPOND WITH VALID JSON ONLY.
Schema: {
  "window24h":{"summary":"2-sentence tactical forecast","keyRisk":"1 sentence","probability":72},
  "window72h":{"summary":"2-sentence forecast","keyRisk":"1 sentence","probability":65},
  "ceasefire30d":12,
  "escalation30d":28,
  "keyUncertainties":["gap1","gap2","gap3"],
  "modelConfidence":"MEDIUM"
}`,
      },
      {
        role: 'user',
        content: `Day ${conflictDay} War Context:
Hormuz: ${hormuzStatus}
Brent: $${brentUsd}/bbl
Verified Intel Items (24h): ${verifiedCount}

Top Active Threats:
${threatList}

Key Developments (last 24h):
${devList}

Generate 24h, 72h, and 30-day conflict trajectory forecasts.`,
      },
    ],
    'gpt-4o',  // Flagship for strategic forecast quality
    600,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)

    const safeWindow = (w: unknown): ConflictForecast['window24h'] => {
      const o = (typeof w === 'object' && w !== null) ? (w as Record<string, unknown>) : {}
      return {
        summary:     typeof o.summary     === 'string' ? o.summary     : '',
        keyRisk:     typeof o.keyRisk     === 'string' ? o.keyRisk     : '',
        probability: typeof o.probability === 'number' ? Math.max(0, Math.min(100, Math.round(o.probability))) : 50,
      }
    }

    return {
      generatedAt:      new Date().toISOString(),
      conflictDay,
      window24h:        safeWindow(p.window24h),
      window72h:        safeWindow(p.window72h),
      ceasefire30d:     typeof p.ceasefire30d   === 'number' ? Math.max(0, Math.min(100, Math.round(p.ceasefire30d)))   : 10,
      escalation30d:    typeof p.escalation30d  === 'number' ? Math.max(0, Math.min(100, Math.round(p.escalation30d)))  : 25,
      keyUncertainties: Array.isArray(p.keyUncertainties) ? p.keyUncertainties.slice(0, 3).map(String) : [],
      modelConfidence:  (['HIGH','MEDIUM','LOW'] as const).includes(p.modelConfidence)
        ? p.modelConfidence : 'MEDIUM',
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 10. Self-Healing Neural Recovery Assessment
// ---------------------------------------------------------------------------
// Called by /api/platform/heal to get AI-driven adaptive recovery ordering.
// Returns the optimal sequence in which to restart subsystems, plus a risk
// assessment of cascading failures if a particular subsystem stays OPEN.
// ---------------------------------------------------------------------------

export interface NeuralRecoveryAssessment {
  summary:       string     // 2-sentence triage narrative
  recoveryOrder: string[]   // ordered list of subsystem labels to restart
  risks:         string[]   // cascade failure risks if OPEN nodes stay offline
  skipIds:       string[]   // subsystems the AI recommends NOT touching (e.g. DB)
}

export async function assessNeuralRecovery(params: {
  neuronStates:      { id: string; label: string; circuit: string; consecutiveFailures: number }[]
  healActions:       string[]     // labels of proposed heal actions
  neuralHealthScore: number       // 0-100
}): Promise<NeuralRecoveryAssessment | null> {
  const { neuronStates, healActions, neuralHealthScore } = params

  const stateList = neuronStates
    .map(s => `${s.label}: ${s.circuit} (${s.consecutiveFailures} failures)`)
    .join('\n')

  const actionList = healActions.join(', ') || 'none'

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-HEAL, an autonomous platform recovery system. Context: ${getSystemDate()}.
Your mission: analyze which subsystems of an AI-driven war intelligence platform are failing,
and prescribe the optimal recovery order to restore full neural health with minimum cascading risk.
Key dependency graph: RSS Pipeline → HERALD-3 Ingest → NEXUS Batch → Intel Database → ORACLE-9 + COMPASS
RULES: dependencies must be restored bottom-up (upstream first), avoid thundering herd,
       only recommend healing if the subsystem has a healPath (skip Intel Database and NEXUS-AI Engine).
RESPOND WITH VALID JSON ONLY.
Schema: {"summary":"2-sentence triage assessment","recoveryOrder":["label1","label2"],"risks":["cascade risk 1","risk 2"],"skipIds":["database","nexus-ai"]}`,
      },
      {
        role: 'user',
        content: `Neural Health Score: ${neuralHealthScore}/100

Subsystem States:
${sanitize(stateList, 600)}

Proposed Heal Actions: ${sanitize(actionList, 300)}

Provide optimal recovery order and cascade risk assessment.`,
      },
    ],
    'gpt-4o-mini',
    500,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    return {
      summary:       typeof p.summary       === 'string' ? p.summary : `Neural health at ${neuralHealthScore}/100. Initiating autonomous recovery sequence.`,
      recoveryOrder: Array.isArray(p.recoveryOrder) ? p.recoveryOrder.slice(0, 6).map(String) : [],
      risks:         Array.isArray(p.risks)         ? p.risks.slice(0, 4).map(String)         : [],
      skipIds:       Array.isArray(p.skipIds)       ? p.skipIds.slice(0, 4).map(String)       : ['database', 'nexus-ai'],
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 11. Situational Pulse — per-theater 15-minute "what's happening right now"
// ---------------------------------------------------------------------------
// Called by /api/intel/pulse cron every 15 minutes.
// Groups recent intel by theater and produces a compact "consciousness" snapshot
// so the dashboard always knows the live situation without full sitrep overhead.
// ---------------------------------------------------------------------------

export interface TheaterPulse {
  theater:         string
  itemCount:       number
  headline:        string        // 1-sentence "what's happening now"
  keyDevelopments: string[]      // 2-3 bullets
  urgency:         'CRITICAL' | 'HIGH' | 'NORMAL'
  trend:           'ESCALATING' | 'STABLE' | 'DE-ESCALATING'
}

export interface SituationalPulse {
  generatedAt:    string
  conflictDay:    number
  overallUrgency: 'CRITICAL' | 'HIGH' | 'NORMAL'
  leadHeadline:   string        // top 1-sentence overall situation
  theaterPulses:  TheaterPulse[]
}

export async function generatePulse(params: {
  conflictDay: number
  recentIntel:  { theater: string; title: string; confidence: number; verified: boolean }[]
}): Promise<SituationalPulse | null> {
  const { conflictDay, recentIntel } = params
  if (recentIntel.length === 0) return null

  // Group by theater and build compact intel list for the prompt
  const byTheater = recentIntel.reduce<Record<string, typeof recentIntel>>((acc, item) => {
    const t = item.theater || 'Unknown'
    ;(acc[t] ??= []).push(item)
    return acc
  }, {})

  const theaterLines = Object.entries(byTheater)
    .slice(0, 8)
    .map(([theater, items]) => {
      const topItems = items
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, 3)
        .map(i => `  - [${i.verified ? 'VER' : 'UNV'}|${i.confidence}%] ${sanitize(i.title, 100)}`)
        .join('\n')
      return `${theater} (${items.length} items):\n${topItems}`
    })
    .join('\n\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-PULSE, an autonomous situational awareness system. Context: ${getSystemDate()}.
Your mission: synthesize recent intelligence into a compact, actionable situational pulse.
Analyze each theater and produce a crisp "what is happening right now" assessment — military brevity style.
RULES: be specific, cite real locations/units/events, one sentence per theater headline, no hedging language.
RESPOND WITH VALID JSON ONLY.
Schema:
{
  "overallUrgency": "CRITICAL|HIGH|NORMAL",
  "leadHeadline": "1-sentence overall situation right now",
  "theaters": [
    {
      "theater": "Persian Gulf / Hormuz",
      "headline": "1-sentence what's happening",
      "keyDevelopments": ["bullet 1", "bullet 2"],
      "urgency": "CRITICAL|HIGH|NORMAL",
      "trend": "ESCALATING|STABLE|DE-ESCALATING"
    }
  ]
}`,
      },
      {
        role: 'user',
        content: `Day ${conflictDay} — Situational Pulse Request
Recent intelligence (last 2 hours):

${theaterLines}

Produce a compact situational pulse for all active theaters.`,
      },
    ],
    'gpt-4o-mini',
    800,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const VALID_URGENCY = ['CRITICAL', 'HIGH', 'NORMAL'] as const
    const VALID_TREND   = ['ESCALATING', 'STABLE', 'DE-ESCALATING'] as const

    const theaterPulses: TheaterPulse[] = []
    for (const t of (Array.isArray(p.theaters) ? p.theaters : [])) {
      if (typeof t !== 'object' || t === null) continue
      const theater = typeof t.theater === 'string' ? t.theater : 'Unknown'
      const items   = byTheater[theater] ?? []
      theaterPulses.push({
        theater,
        itemCount:       items.length,
        headline:        typeof t.headline === 'string' ? t.headline : '',
        keyDevelopments: Array.isArray(t.keyDevelopments) ? t.keyDevelopments.slice(0, 3).map(String) : [],
        urgency:         VALID_URGENCY.includes(t.urgency) ? t.urgency : 'NORMAL',
        trend:           VALID_TREND.includes(t.trend)     ? t.trend   : 'STABLE',
      })
    }

    return {
      generatedAt:    new Date().toISOString(),
      conflictDay,
      overallUrgency: VALID_URGENCY.includes(p.overallUrgency) ? p.overallUrgency : 'NORMAL',
      leadHeadline:   typeof p.leadHeadline === 'string' ? p.leadHeadline : '',
      theaterPulses,
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 12. Contradiction Detector — find mutually exclusive claims in a batch
// ---------------------------------------------------------------------------

export interface ContradictionPair {
  indexA:      number
  indexB:      number
  explanation: string     // why these contradict
  severity:    'HARD' | 'SOFT'  // HARD = mutually exclusive facts; SOFT = differing framing
}

export async function detectContradictions(
  items: { index: number; title: string; source: string }[],
): Promise<ContradictionPair[] | null> {
  if (items.length < 2) return []

  const itemList = items
    .slice(0, 20)
    .map(it => `${it.index}|[${sanitize(it.source, 40)}]|${sanitize(it.title, 140)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-CONTRADICT, an intelligence contradiction detection system. Context: ${getSystemDate()}.
Your mission: identify pairs of headlines that contain CONTRADICTORY CLAIMS.
Types:
  HARD = directly mutually exclusive facts (e.g. "ceasefire signed" vs "bombardment intensifies")
  SOFT = same event, different framing that creates contradictory impressions
RULES:
- Only flag GENUINE contradictions. Two stories about different events are NOT contradictions.
- Focus on factual claims, not editorial tone.
- Return empty array if no contradictions found.
RESPOND WITH VALID JSON ONLY.
Schema: {"contradictions":[{"indexA":0,"indexB":3,"explanation":"1 sentence why these contradict","severity":"HARD|SOFT"}]}`,
      },
      {
        role: 'user',
        content: `Analyze ${items.length} headlines for contradictions (format: index|[source]|title):\n${itemList}`,
      },
    ],
    'gpt-4o-mini',
    600,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const arr: unknown[] = Array.isArray(p.contradictions) ? p.contradictions : Array.isArray(p) ? p : []
    return arr
      .map(e => (typeof e === 'object' && e !== null ? (e as Record<string, unknown>) : {}))
      .filter(e => typeof e.indexA === 'number' && typeof e.indexB === 'number')
      .map(e => ({
        indexA:      e.indexA as number,
        indexB:      e.indexB as number,
        explanation: typeof e.explanation === 'string' ? e.explanation : '',
        severity:    e.severity === 'HARD' || e.severity === 'SOFT' ? e.severity : 'SOFT',
      }))
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 13. Source Disagreement Detector — find T1 sources that disagree
// ---------------------------------------------------------------------------

export interface SourceDisagreement {
  indexA:      number
  indexB:      number
  sourceA:     string
  sourceB:     string
  topic:       string       // what the disagreement is about
  resolution:  string       // which source is more credible in this case
}

export async function detectSourceDisagreements(
  items: { index: number; title: string; source: string; tier: number; confidence: number }[],
): Promise<SourceDisagreement[] | null> {
  // Only worthwhile with multiple T1/T2 sources
  const credible = items.filter(i => i.tier <= 2)
  if (credible.length < 2) return []

  const itemList = credible
    .slice(0, 15)
    .map(it => `${it.index}|T${it.tier}|${it.confidence}%|[${sanitize(it.source, 40)}]|${sanitize(it.title, 140)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-DISAGREE, an intelligence source disagreement analyzer. Context: ${getSystemDate()}.
Find cases where credible sources (T1 wire/official, T2 established media) report CONFLICTING INFORMATION about the same topic.
RULES:
- Only flag items from DIFFERENT sources about the SAME event/topic
- "Reuters says X, AP says not-X" = disagreement
- Two stories about different events = NOT a disagreement
- Suggest which source is likely more accurate based on tier + specificity
- Return empty array if no disagreements
RESPOND WITH VALID JSON ONLY.
Schema: {"disagreements":[{"indexA":0,"indexB":3,"sourceA":"Reuters","sourceB":"AP","topic":"1-sentence topic","resolution":"1-sentence which is more credible"}]}`,
      },
      {
        role: 'user',
        content: `Analyze ${credible.length} credible-source headlines for disagreements:\n${itemList}`,
      },
    ],
    'gpt-4o-mini',
    600,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    const arr: unknown[] = Array.isArray(p.disagreements) ? p.disagreements : Array.isArray(p) ? p : []
    return arr
      .map(e => (typeof e === 'object' && e !== null ? (e as Record<string, unknown>) : {}))
      .filter(e => typeof e.indexA === 'number' && typeof e.indexB === 'number')
      .map(e => ({
        indexA:      e.indexA as number,
        indexB:      e.indexB as number,
        sourceA:     typeof e.sourceA === 'string' ? e.sourceA : '',
        sourceB:     typeof e.sourceB === 'string' ? e.sourceB : '',
        topic:       typeof e.topic === 'string' ? e.topic : '',
        resolution:  typeof e.resolution === 'string' ? e.resolution : '',
      }))
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 14. Ground Truth Builder — compile verified facts for AI context
// ---------------------------------------------------------------------------

export async function buildGroundTruthDigest(
  verifiedItems: { title: string; theater: string; confidence: number }[],
): Promise<string | null> {
  if (verifiedItems.length === 0) return null

  const itemList = verifiedItems
    .slice(0, 25)
    .map((it, i) => `${i + 1}. [${it.theater}|${it.confidence}%] ${sanitize(it.title, 120)}`)
    .join('\n')

  const raw = await callAI(
    [
      {
        role: 'system',
        content: `You are NEXUS-TRUTH, a verified intelligence compiler. Context: ${getSystemDate()}.
Compress the verified intel items into a concise ground truth digest (max 500 words).
Format: bullet-point list of confirmed facts organized by theater.
RULES: only include facts present in the verified items — do NOT fabricate. Be precise with names, locations, numbers.
RESPOND WITH VALID JSON ONLY.
Schema: {"digest":"bullet-point ground truth digest"}`,
      },
      {
        role: 'user',
        content: `Compile ${verifiedItems.length} verified intel items into ground truth digest:\n${itemList}`,
      },
    ],
    'gpt-4o-mini',
    800,
  )

  if (!raw) return null
  try {
    const p = JSON.parse(raw)
    return typeof p.digest === 'string' ? p.digest : null
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 15. Semantic Similarity — deterministic headline dedup (no embeddings API)
// ---------------------------------------------------------------------------
// Uses Jaccard similarity on 3-gram character sets for fast approximate matching.
// No external API call — runs instantly in-process.
// ---------------------------------------------------------------------------

function triGrams(text: string): Set<string> {
  const t = text.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim()
  const grams = new Set<string>()
  for (let i = 0; i <= t.length - 3; i++) grams.add(t.slice(i, i + 3))
  return grams
}

export function semanticSimilarity(a: string, b: string): number {
  const ga = triGrams(a)
  const gb = triGrams(b)
  if (ga.size === 0 || gb.size === 0) return 0
  let intersection = 0
  for (const g of ga) { if (gb.has(g)) intersection++ }
  return intersection / (ga.size + gb.size - intersection) // Jaccard index
}

export interface DedupResult {
  /** Indices of items to KEEP (first occurrence in each cluster) */
  keepIndices:  number[]
  /** Pairs that are near-duplicates */
  duplicates:   { indexA: number; indexB: number; similarity: number }[]
}

/**
 * Cluster headlines by semantic similarity and return dedup decisions.
 * threshold: Jaccard similarity above which two headlines are considered duplicates.
 * Default 0.55 = ~55% trigram overlap (catches paraphrased AP rewrites).
 */
export function deduplicateHeadlines(
  headlines: string[],
  threshold = 0.55,
): DedupResult {
  const duplicates: DedupResult['duplicates'] = []
  const dropped = new Set<number>()

  for (let i = 0; i < headlines.length; i++) {
    if (dropped.has(i)) continue
    for (let j = i + 1; j < headlines.length; j++) {
      if (dropped.has(j)) continue
      const sim = semanticSimilarity(headlines[i], headlines[j])
      if (sim >= threshold) {
        duplicates.push({ indexA: i, indexB: j, similarity: sim })
        dropped.add(j) // keep i (first occurrence), drop j
      }
    }
  }

  const keepIndices = headlines.map((_, i) => i).filter(i => !dropped.has(i))
  return { keepIndices, duplicates }
}
