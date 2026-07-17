/**
 * lib/gea-engine.ts
 *
 * Group-Evolving Agents (GEA) Experience-Sharing Pool
 * ────────────────────────────────────────────────────
 * Implements explicit cross-population experience sharing:
 *   • Any agent (governor, debate, KG, visual, revenue, foresight)
 *     writes patches, failures, innovations, and learnings to a shared pool
 *   • Other agents query the pool to learn from peer successes/failures
 *     before attempting similar operations
 *   • Hierarchical macro-micro learning via importance-ranked semantic search
 *
 * Multi-Agent Memory Systems (persistent / episodic / semantic / procedural)
 * ──────────────────────────────────────────────────────────────────────────
 *   • writeMemory:      store typed memory for an agent or globally
 *   • readMemory:       retrieve by exact or prefix key
 *   • searchMemory:     semantic-style text scan across values
 *   • recallEpisodic:   most recent N episodes for a given agent
 *   • summarizeToSemantic: take episodic memories, distill to semantic (macro learning)
 */

import { createClient } from '@supabase/supabase-js'

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  )
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AgentType =
  | 'GOVERNOR' | 'DEBATE' | 'KG' | 'VISUAL'
  | 'REVENUE' | 'FORESIGHT' | 'HEALING' | 'DGM' | 'RESEARCH'

export type ExperienceType =
  | 'PATCH_APPLIED'   | 'PATCH_REJECTED'  | 'INNOVATION'
  | 'FAILURE_ANALYSIS'| 'STRATEGY_DISCOVERY' | 'KNOWLEDGE_ACQUIRED'
  | 'RESEARCH_FINDING'| 'SECURITY_PATCH'  | 'PERFORMANCE_GAIN'

export type MemoryType = 'PERSISTENT' | 'EPISODIC' | 'SEMANTIC' | 'PROCEDURAL'

export interface GEAExperience {
  id:               string
  agent_id:         string
  agent_type:       AgentType
  experience_type:  ExperienceType
  payload:          Record<string, unknown>
  performance_delta: number | null
  summary:          string | null
  validated:        boolean
  validation_votes: number
  created_at:       string
}

export interface AgentMemory {
  id:            string
  agent_id:      string
  memory_type:   MemoryType
  key:           string
  value:         Record<string, unknown>
  importance:    number
  from_trajectory: boolean
  expires_at:    string | null
  last_accessed: string
  access_count:  number
  created_at:    string
}

export interface GEAStats {
  totalExperiences:     number
  byType:               Record<ExperienceType, number>
  avgPerformanceDelta:  number | null
  topInnovations:       GEAExperience[]
  recentFailures:       GEAExperience[]
  memoryCount:          number
  persistentCount:      number
  episodicCount:        number
  semanticCount:        number
  proceduralCount:      number
}

// ---------------------------------------------------------------------------
// GEA Experience Pool — write
// ---------------------------------------------------------------------------

export async function shareExperience(
  agentId:          string,
  agentType:        AgentType,
  experienceType:   ExperienceType,
  payload:          Record<string, unknown>,
  summary?:         string,
  performanceDelta?: number,
): Promise<string> {
  const sb = getSupabase()

  const { data, error } = await sb
    .from('gea_experience_pool')
    .insert({
      agent_id:         agentId,
      agent_type:       agentType,
      experience_type:  experienceType,
      payload,
      summary:          summary ?? null,
      performance_delta: performanceDelta ?? null,
    })
    .select('id')
    .single()

  if (error || !data) throw new Error(`shareExperience failed: ${error?.message}`)
  return data.id as string
}

// ---------------------------------------------------------------------------
// GEA Experience Pool — read: query by type or agent population
// ---------------------------------------------------------------------------

export async function queryExperiencePool(opts: {
  agentType?:      AgentType
  experienceType?: ExperienceType
  minPerformance?: number
  validatedOnly?:  boolean
  limit?:          number
}): Promise<GEAExperience[]> {
  const sb = getSupabase()

  let query = sb
    .from('gea_experience_pool')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(opts.limit ?? 20)

  if (opts.agentType)       query = query.eq('agent_type', opts.agentType)
  if (opts.experienceType)  query = query.eq('experience_type', opts.experienceType)
  if (opts.validatedOnly)   query = query.eq('validated', true)
  if (opts.minPerformance != null) {
    query = query.gte('performance_delta', opts.minPerformance)
  }

  const { data } = await query
  return (data ?? []) as GEAExperience[]
}

// ---------------------------------------------------------------------------
// GEA Experience Pool — vote (peer validation by other agents)
// ---------------------------------------------------------------------------

export async function voteExperience(experienceId: string): Promise<void> {
  const sb = getSupabase()

  const { data } = await sb
    .from('gea_experience_pool')
    .select('validation_votes')
    .eq('id', experienceId)
    .single()

  if (!data) return
  const votes = (data.validation_votes as number) + 1
  await sb.from('gea_experience_pool').update({
    validation_votes: votes,
    validated: votes >= 2,   // auto-validated after 2 peer votes
  }).eq('id', experienceId)
}

// ---------------------------------------------------------------------------
// Multi-Agent Memory: write
// ---------------------------------------------------------------------------

export async function writeMemory(
  agentId:      string,
  memoryType:   MemoryType,
  key:          string,
  value:        Record<string, unknown>,
  importance?:  number,
  fromTrajectory?: boolean,
  expiresAt?:   Date,
): Promise<void> {
  const sb = getSupabase()

  await sb.from('agent_memory').upsert({
    agent_id:        agentId,
    memory_type:     memoryType,
    key,
    value,
    importance:      importance ?? 0.5,
    from_trajectory: fromTrajectory ?? false,
    expires_at:      expiresAt?.toISOString() ?? null,
    last_accessed:   new Date().toISOString(),
  }, { onConflict: 'agent_id,memory_type,key' })
}

// ---------------------------------------------------------------------------
// Multi-Agent Memory: read exact key
// ---------------------------------------------------------------------------

export async function readMemory(
  agentId:    string,
  memoryType: MemoryType,
  key:        string,
): Promise<Record<string, unknown> | null> {
  const sb  = getSupabase()
  const now = new Date().toISOString()

  const { data } = await sb
    .from('agent_memory')
    .select('*')
    .eq('agent_id', agentId)
    .eq('memory_type', memoryType)
    .eq('key', key)
    .or(`expires_at.is.null,expires_at.gt.${now}`)
    .single()

  if (!data) return null

  // Bump access count (fire-and-forget)
  void sb.from('agent_memory').update({
    last_accessed: now,
    access_count:  (data.access_count as number) + 1,
  }).eq('id', data.id)

  return data.value as Record<string, unknown>
}

// ---------------------------------------------------------------------------
// Multi-Agent Memory: recall most recent episodic memories for an agent
// ---------------------------------------------------------------------------

export async function recallEpisodic(
  agentId: string,
  limit    = 10,
): Promise<AgentMemory[]> {
  const sb  = getSupabase()
  const now = new Date().toISOString()

  const { data } = await sb
    .from('agent_memory')
    .select('*')
    .eq('agent_id', agentId)
    .eq('memory_type', 'EPISODIC')
    .or(`expires_at.is.null,expires_at.gt.${now}`)
    .order('created_at', { ascending: false })
    .limit(limit)

  return (data ?? []) as AgentMemory[]
}

// ---------------------------------------------------------------------------
// Hierarchical macro learning:
// Distill recent episodic memories into a single semantic memory entry.
// This is the "macro learning" step — coarse-grained knowledge consolidation.
// ---------------------------------------------------------------------------

export async function summarizeToSemantic(
  agentId:     string,
  summaryKey:  string,
  episodic:    AgentMemory[],
  llmSummary:  string,   // caller supplies the LLM-generated synthesis
  importance?: number,
): Promise<void> {
  await writeMemory(
    agentId,
    'SEMANTIC',
    summaryKey,
    {
      synthesis:       llmSummary,
      sourceEpisodes:  episodic.map(e => e.id),
      distilledAt:     new Date().toISOString(),
    },
    importance ?? 0.8,
    false,
  )
}

// ---------------------------------------------------------------------------
// GEA Stats for dashboard
// ---------------------------------------------------------------------------

export async function computeGEAStats(): Promise<GEAStats> {
  const sb = getSupabase()

  const [poolRes, memRes] = await Promise.all([
    sb.from('gea_experience_pool').select('experience_type, performance_delta'),
    sb.from('agent_memory').select('memory_type'),
  ])

  const pool      = poolRes.data ?? []
  const memories  = memRes.data ?? []

  const byType: Record<string, number> = {}
  let deltaSum = 0, deltaCount = 0
  for (const e of pool) {
    byType[e.experience_type] = (byType[e.experience_type] ?? 0) + 1
    if (e.performance_delta != null) {
      deltaSum += e.performance_delta
      deltaCount++
    }
  }

  const [topRes, failRes] = await Promise.all([
    sb.from('gea_experience_pool')
      .select('*')
      .eq('experience_type', 'INNOVATION')
      .order('performance_delta', { ascending: false })
      .limit(5),
    sb.from('gea_experience_pool')
      .select('*')
      .eq('experience_type', 'FAILURE_ANALYSIS')
      .order('created_at', { ascending: false })
      .limit(5),
  ])

  const memCounts = memories.reduce<Record<string, number>>((acc, m) => {
    acc[m.memory_type] = (acc[m.memory_type] ?? 0) + 1
    return acc
  }, {})

  return {
    totalExperiences:    pool.length,
    byType:              byType as Record<ExperienceType, number>,
    avgPerformanceDelta: deltaCount > 0 ? Math.round((deltaSum / deltaCount) * 100) / 100 : null,
    topInnovations:      (topRes.data ?? []) as GEAExperience[],
    recentFailures:      (failRes.data ?? []) as GEAExperience[],
    memoryCount:         memories.length,
    persistentCount:     memCounts['PERSISTENT'] ?? 0,
    episodicCount:       memCounts['EPISODIC']   ?? 0,
    semanticCount:       memCounts['SEMANTIC']   ?? 0,
    proceduralCount:     memCounts['PROCEDURAL'] ?? 0,
  }
}
