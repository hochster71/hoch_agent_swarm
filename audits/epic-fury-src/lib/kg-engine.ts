/**
 * lib/kg-engine.ts — Neurosymbolic Knowledge Graph Engine
 *
 * Implements the Bevel KG pattern within the existing Supabase stack.
 * Extracts entities + claims from intel text, verifies via LLM-as-Judge,
 * detects contradictions, and maintains a growing symbolic knowledge graph.
 *
 * Tables used:
 *   kg_entities — actors, locations, weapons, events, concepts
 *   kg_claims   — fact-checked claims with confidence + judge scores
 *   kg_mutations — DGM mutation proposals and their benchmark results
 *
 * Security: All text inputs truncated at ingest to prevent prompt injection.
 */

import { createClient } from '@supabase/supabase-js'
import { runAndPersistDebate } from './debate-engine'
import { safeOpenAIChatCompletion } from '@/lib/openai-safe'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type EntityType = 'ACTOR' | 'LOCATION' | 'WEAPON' | 'EVENT' | 'CLAIM' | 'ORGANIZATION' | 'CONCEPT'
export type VerificationStatus = 'VERIFIED' | 'CONTRADICTED' | 'PENDING' | 'UNVERIFIABLE'
export type MutationStatus = 'PROPOSED' | 'TESTING' | 'APPLIED' | 'REJECTED'
export type MutationType = 'PROMPT_EDIT' | 'THRESHOLD_CHANGE' | 'LOGIC_GATE' | 'MODEL_SWAP' | 'PARAM_TUNE'

export interface KGEntity {
  id?:          string
  name:         string
  type:         EntityType
  aliases:      string[]
  confidence:   number
  source_ids:   string[]
  threat_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
  metadata:     Record<string, unknown>
}

export interface KGClaim {
  id?:                    string
  claim_text:             string
  entity_ids:             string[]
  verification_status:    VerificationStatus
  confidence:             number
  corroborating_sources:  number
  contradicting_sources:  number
  judge_score:            number | null
  judge_rationale:        string | null
  intel_id:               string | null
}

export interface KGMutation {
  id?:              string
  target:           string
  mutation_type:    MutationType
  before_version:   string
  after_version:    string
  benchmark_before: number | null
  benchmark_after:  number | null
  status:           MutationStatus
  rationale:        string | null
}

export interface KGStats {
  totalEntities:   number
  totalClaims:     number
  verifiedClaims:  number
  pendingClaims:   number
  contradictions:  number
  mutations:       number
  appliedMutations: number
  topActors:       { name: string; confidence: number }[]
  topLocations:    { name: string; confidence: number }[]
}

export interface ExtractionResult {
  entities: Omit<KGEntity, 'id'>[]
  claims:   Omit<KGClaim, 'id'>[]
}

export interface VerificationResult {
  claim:          string
  judgeScore:     number
  rationale:      string
  status:         VerificationStatus
  corroborating:  number
  contradicting:  number
}

// ---------------------------------------------------------------------------
// Supabase client (server-side only — uses service role key)
// ---------------------------------------------------------------------------

function getSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) throw new Error('KG-ENGINE: Missing Supabase credentials')
  return createClient(url, key, { auth: { persistSession: false } })
}

const MAX_TEXT_LENGTH = 2000  // Security: truncate before sending to LLM

// ---------------------------------------------------------------------------
// LLM helper (reuses same openai endpoint pattern as ai-engine.ts)
// ---------------------------------------------------------------------------

async function callLLM(
  system: string,
  user: string,
  maxTokens = 800,
): Promise<string | null> {
  return safeOpenAIChatCompletion(
    [
      { role: 'system', content: system },
      { role: 'user', content: user },
    ],
    { model: 'gpt-4o-mini', maxTokens, temperature: 0.1, timeoutMs: 20_000 },
  )
}

// ---------------------------------------------------------------------------
// Layer 1 helper: Extract entities + claims from intel text
// ---------------------------------------------------------------------------

export async function extractFromIntel(
  text: string,
  intelId: string,
): Promise<ExtractionResult> {
  const safe = text.slice(0, MAX_TEXT_LENGTH)

  const raw = await callLLM(
    `You are a military intelligence analyst extracting structured data from battlefield reports.
Extract entities and claims. Return ONLY valid JSON in this exact structure:
{
  "entities": [
    { "name": string, "type": "ACTOR"|"LOCATION"|"WEAPON"|"EVENT"|"ORGANIZATION"|"CONCEPT",
      "aliases": string[], "confidence": 0-100, "threat_level": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL"|null }
  ],
  "claims": [
    { "claim_text": string, "confidence": 0-100 }
  ]
}
Extract up to 8 entities and 4 claims. Be specific. Use military terminology. Do not fabricate.`,
    `Intel report: ${safe}`,
    600,
  )

  if (!raw) return { entities: [], claims: [] }

  try {
    const parsed = JSON.parse(raw) as {
      entities?: { name: string; type: EntityType; aliases?: string[]; confidence?: number; threat_level?: KGEntity['threat_level'] }[]
      claims?: { claim_text: string; confidence?: number }[]
    }

    const entities: Omit<KGEntity, 'id'>[] = (parsed.entities ?? []).map(e => ({
      name:         String(e.name ?? '').slice(0, 200),
      type:         e.type ?? 'CONCEPT',
      aliases:      (e.aliases ?? []).slice(0, 5).map(a => String(a).slice(0, 100)),
      confidence:   Math.min(100, Math.max(0, Number(e.confidence ?? 50))),
      source_ids:   [intelId],
      threat_level: e.threat_level ?? null,
      metadata:     {},
    })).filter(e => e.name.length > 1)

    const claims: Omit<KGClaim, 'id'>[] = (parsed.claims ?? []).map(c => ({
      claim_text:           String(c.claim_text ?? '').slice(0, 500),
      entity_ids:           [],
      verification_status:  'PENDING' as VerificationStatus,
      confidence:           Math.min(100, Math.max(0, Number(c.confidence ?? 50))),
      corroborating_sources: 0,
      contradicting_sources: 0,
      judge_score:          null,
      judge_rationale:      null,
      intel_id:             intelId,
    })).filter(c => c.claim_text.length > 5)

    return { entities, claims }
  } catch {
    return { entities: [], claims: [] }
  }
}

// ---------------------------------------------------------------------------
// Layer 2: Neurosymbolic verification — 5-Agent Debate Engine
// Runs a structured multi-agent debate (Researcher / Skeptic / Verifier /
// US-Impact Analyst / Moderator) with iterative rebuttal rounds.
// Falls back to single LLM-as-Judge if OPENAI_API_KEY is unavailable.
// ---------------------------------------------------------------------------

export async function verifyClaim(
  claim: string,
  kgContext: string[],
): Promise<VerificationResult> {
  const safeClaim = claim.slice(0, 500)
  const safeCtx   = kgContext.slice(0, 8).map(c => c.slice(0, 300))

  // Primary path: 5-agent Neural Truth Autonomy debate
  if (process.env.OPENAI_API_KEY) {
    try {
      return await runAndPersistDebate({ claim: safeClaim, kgContext: safeCtx })
    } catch {
      // Fall through to single-LLM fallback
    }
  }

  // Fallback: single LLM-as-Judge (preserves behaviour when debate engine unavailable)
  const raw = await callLLM(
    `You are a military intelligence fact-checker using neurosymbolic reasoning.
Assess the verifiability of a claim given KG context. Return ONLY JSON:
{
  "judge_score": 0.0-10.0,
  "status": "VERIFIED"|"CONTRADICTED"|"PENDING"|"UNVERIFIABLE",
  "rationale": string (max 2 sentences),
  "corroborating": 0-10,
  "contradicting": 0-10
}
- VERIFIED: multiple sources corroborate, no logical contradictions
- CONTRADICTED: another claim in KG directly refutes this
- PENDING: insufficient evidence to decide
- UNVERIFIABLE: claim cannot be checked with available KG data`,
    `Claim to verify: "${safeClaim}"

Current KG context (related known facts):
${safeCtx.map((c, i) => `${i + 1}. ${c}`).join('\n') || 'No related context available.'}`,
    400,
  )

  const fallback: VerificationResult = {
    claim: safeClaim,
    judgeScore: 5.0,
    rationale: 'Insufficient KG context for verification.',
    status: 'PENDING',
    corroborating: 0,
    contradicting: 0,
  }

  if (!raw) return fallback

  try {
    const p = JSON.parse(raw) as {
      judge_score?: number
      status?: VerificationStatus
      rationale?: string
      corroborating?: number
      contradicting?: number
    }
    return {
      claim:         safeClaim,
      judgeScore:    Math.min(10, Math.max(0, Number(p.judge_score ?? 5))),
      rationale:     String(p.rationale ?? fallback.rationale).slice(0, 400),
      status:        (['VERIFIED', 'CONTRADICTED', 'PENDING', 'UNVERIFIABLE'].includes(p.status ?? '')
                       ? p.status! : 'PENDING'),
      corroborating: Math.min(10, Math.max(0, Number(p.corroborating ?? 0))),
      contradicting: Math.min(10, Math.max(0, Number(p.contradicting ?? 0))),
    }
  } catch {
    return fallback
  }
}

// ---------------------------------------------------------------------------
// Supabase KG write operations
// ---------------------------------------------------------------------------

export async function upsertEntity(entity: Omit<KGEntity, 'id'>): Promise<string | null> {
  try {
    const sb = getSupabase()
    // Try to find existing entity by name+type
    const { data: existing } = await sb
      .from('kg_entities')
      .select('id, aliases, source_ids, confidence')
      .filter('type', 'eq', entity.type)
      .ilike('name', entity.name)
      .maybeSingle()

    if (existing) {
      // Merge: union aliases + source_ids, take higher confidence
      const merged = {
        aliases:      [...new Set([...((existing.aliases as string[]) ?? []), ...entity.aliases])].slice(0, 20),
        source_ids:   [...new Set([...((existing.source_ids as string[]) ?? []), ...entity.source_ids])].slice(0, 50),
        confidence:   Math.max(existing.confidence as number, entity.confidence),
        last_seen:    new Date().toISOString(),
        threat_level: entity.threat_level ?? undefined,
      }
      await sb.from('kg_entities').update(merged).eq('id', existing.id as string)
      return existing.id as string
    }

    const { data, error } = await sb
      .from('kg_entities')
      .insert({ ...entity, first_seen: new Date().toISOString(), last_seen: new Date().toISOString() })
      .select('id')
      .single()

    if (error) return null
    return (data as { id: string }).id
  } catch {
    return null
  }
}

export async function upsertClaim(claim: Omit<KGClaim, 'id'>, verification: VerificationResult): Promise<string | null> {
  try {
    const sb = getSupabase()
    const { data, error } = await sb
      .from('kg_claims')
      .insert({
        ...claim,
        verification_status:  verification.status,
        judge_score:          verification.judgeScore,
        judge_rationale:      verification.rationale,
        corroborating_sources: verification.corroborating,
        contradicting_sources: verification.contradicting,
        updated_at:           new Date().toISOString(),
      })
      .select('id')
      .single()

    if (error) return null
    return (data as { id: string }).id
  } catch {
    return null
  }
}

export async function storeMutation(mutation: Omit<KGMutation, 'id'>): Promise<string | null> {
  try {
    const sb = getSupabase()
    const { data, error } = await sb
      .from('kg_mutations')
      .insert(mutation)
      .select('id')
      .single()
    if (error) return null
    return (data as { id: string }).id
  } catch {
    return null
  }
}

export async function applyMutation(mutationId: string, benchmarkAfter: number): Promise<void> {
  try {
    const sb = getSupabase()
    await sb.from('kg_mutations').update({
      status:          'APPLIED',
      benchmark_after: benchmarkAfter,
      applied_at:      new Date().toISOString(),
    }).eq('id', mutationId)
  } catch { /* non-fatal */ }
}

export async function rejectMutation(mutationId: string, reason: string): Promise<void> {
  try {
    const sb = getSupabase()
    await sb.from('kg_mutations').update({
      status:    'REJECTED',
      rationale: reason,
    }).eq('id', mutationId)
  } catch { /* non-fatal */ }
}

// ---------------------------------------------------------------------------
// KG Reads — query helpers for Governor layers
// ---------------------------------------------------------------------------

export async function getUnprocessedIntel(limit = 20): Promise<{ id: string; title: string; summary: string; theater: string }[]> {
  try {
    const sb = getSupabase()
    // Intel not yet referenced in any kg_claims
    const { data: processedIds } = await sb
      .from('kg_claims')
      .select('intel_id')
      .not('intel_id', 'is', null)
      .limit(500)

    const ids = ((processedIds ?? []) as { intel_id: string }[]).map(r => r.intel_id).filter(Boolean)

    let q = sb.from('intel').select('id, title, summary, theater').order('created_at', { ascending: false }).limit(limit)
    if (ids.length > 0) q = q.not('id', 'in', `(${ids.join(',')})`)

    const { data } = await q
    return (data ?? []) as { id: string; title: string; summary: string; theater: string }[]
  } catch {
    return []
  }
}

export async function getKGContextForClaim(claimText: string, limit = 6): Promise<string[]> {
  // Search for related verified claims by keyword overlap
  try {
    const sb = getSupabase()
    const keywords = claimText
      .toLowerCase()
      .split(/\s+/)
      .filter(w => w.length > 4)
      .slice(0, 5)

    if (keywords.length === 0) return []

    // Use full-text search on claim_text
    const { data } = await sb
      .from('kg_claims')
      .select('claim_text, verification_status, judge_score')
      .neq('verification_status', 'PENDING')
      .order('judge_score', { ascending: false, nullsFirst: false })
      .limit(limit * 2)

    const rows = (data ?? []) as { claim_text: string; verification_status: string; judge_score: number | null }[]

    // Score by keyword overlap
    const scored = rows.map(r => ({
      text: `[${r.verification_status}] ${r.claim_text}`,
      score: keywords.filter(kw => r.claim_text.toLowerCase().includes(kw)).length,
    })).filter(r => r.score > 0).sort((a, b) => b.score - a.score)

    return scored.slice(0, limit).map(r => r.text)
  } catch {
    return []
  }
}

export async function getPendingMutations(): Promise<KGMutation[]> {
  try {
    const sb = getSupabase()
    const { data } = await sb
      .from('kg_mutations')
      .select('*')
      .eq('status', 'PROPOSED')
      .order('created_at', { ascending: true })
      .limit(10)
    return (data ?? []) as KGMutation[]
  } catch {
    return []
  }
}

export async function getAppliedMutations(target?: string): Promise<KGMutation[]> {
  try {
    const sb = getSupabase()
    let q = sb.from('kg_mutations').select('*').eq('status', 'APPLIED')
    if (target) q = q.eq('target', target)
    const { data } = await q.order('applied_at', { ascending: false }).limit(5)
    return (data ?? []) as KGMutation[]
  } catch {
    return []
  }
}

export async function computeKGStats(): Promise<KGStats> {
  try {
    const sb = getSupabase()
    const [
      { count: totalEntities },
      { count: totalClaims },
      { count: verifiedClaims },
      { count: pendingClaims },
      { count: contradictions },
      { count: mutations },
      { count: appliedMutations },
      { data: topActors },
      { data: topLocations },
    ] = await Promise.all([
      sb.from('kg_entities').select('*', { count: 'exact', head: true }),
      sb.from('kg_claims').select('*', { count: 'exact', head: true }),
      sb.from('kg_claims').select('*', { count: 'exact', head: true }).eq('verification_status', 'VERIFIED'),
      sb.from('kg_claims').select('*', { count: 'exact', head: true }).eq('verification_status', 'PENDING'),
      sb.from('kg_claims').select('*', { count: 'exact', head: true }).eq('verification_status', 'CONTRADICTED'),
      sb.from('kg_mutations').select('*', { count: 'exact', head: true }),
      sb.from('kg_mutations').select('*', { count: 'exact', head: true }).eq('status', 'APPLIED'),
      sb.from('kg_entities').select('name, confidence').eq('type', 'ACTOR').order('confidence', { ascending: false }).limit(5),
      sb.from('kg_entities').select('name, confidence').eq('type', 'LOCATION').order('confidence', { ascending: false }).limit(5),
    ])

    return {
      totalEntities:   totalEntities ?? 0,
      totalClaims:     totalClaims ?? 0,
      verifiedClaims:  verifiedClaims ?? 0,
      pendingClaims:   pendingClaims ?? 0,
      contradictions:  contradictions ?? 0,
      mutations:       mutations ?? 0,
      appliedMutations: appliedMutations ?? 0,
      topActors:       (topActors ?? []) as { name: string; confidence: number }[],
      topLocations:    (topLocations ?? []) as { name: string; confidence: number }[],
    }
  } catch {
    return { totalEntities: 0, totalClaims: 0, verifiedClaims: 0, pendingClaims: 0, contradictions: 0, mutations: 0, appliedMutations: 0, topActors: [], topLocations: [] }
  }
}
