/**
 * GET /api/platform/adaptive-schedule
 * POST /api/platform/adaptive-schedule
 *
 * Dynamic pipeline scheduler — adjusts cron aggressiveness based on:
 *   - Active intel volume (high volume → tighter ingest interval)
 *   - AI provider health (degraded → skip enhancement steps)
 *   - Conflict escalation level (HIGH/CRITICAL → faster cycles)
 *   - Platform error rate (high errors → throttle)
 *
 * Called by: orchestrate cron (every 3 min) and directly (every 3 min)
 * Auth: CRON_SECRET
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 30

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET?.trim()
  if (req.headers.get('x-vercel-cron') === '1') return true
  if (!secret) return process.env.NODE_ENV !== 'production'
  const auth = req.headers.get('authorization') ?? ''
  return auth === `Bearer ${secret}`
}

interface ScheduleConfig {
  ingestIntervalMin:    number
  batchIntervalMin:     number
  enhancementEnabled:   boolean
  aiTier:               'full' | 'mini' | 'disabled'
  conflictLevel:        string
  reasoning:            string[]
}

async function computeAdaptiveSchedule(): Promise<ScheduleConfig> {
  const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  const reasoning: string[] = []

  const defaults: ScheduleConfig = {
    ingestIntervalMin:  5,
    batchIntervalMin:   15,
    enhancementEnabled: true,
    aiTier:             'full',
    conflictLevel:      'ACTIVE',
    reasoning,
  }

  if (!supaUrl || !supaKey) {
    reasoning.push('Supabase unconfigured — using defaults')
    return defaults
  }

  const sb = createClient(supaUrl, supaKey, { auth: { persistSession: false } })

  // Fetch recent metrics in parallel
  const [intelRes, cycleRes, snapshotRes] = await Promise.allSettled([
    sb.from('intel').select('id', { count: 'exact' }).gte(
      'created_at',
      new Date(Date.now() - 30 * 60_000).toISOString()
    ).limit(1),
    sb.from('governor_cycles').select('error, escalations').order('created_at', { ascending: false }).limit(10),
    sb.from('model_snapshots').select('threat_level').order('created_at', { ascending: false }).limit(1).single(),
  ])

  const recentIntelCount = intelRes.status === 'fulfilled' ? (intelRes.value.count ?? 0) : 0
  const threatLevel = snapshotRes.status === 'fulfilled'
    ? (snapshotRes.value.data?.threat_level ?? 'ELEVATED')
    : 'ELEVATED'

  let errorRate = 0
  if (cycleRes.status === 'fulfilled' && cycleRes.value.data?.length) {
    errorRate = cycleRes.value.data.filter((c: { error: unknown }) => c.error).length / cycleRes.value.data.length
  }

  // Adapt based on threat level
  if (threatLevel === 'CRITICAL' || threatLevel === 'SEVERE') {
    defaults.ingestIntervalMin = 3
    defaults.batchIntervalMin  = 10
    reasoning.push(`Threat level ${threatLevel} → accelerated pipeline`)
  } else if (threatLevel === 'LOW') {
    defaults.ingestIntervalMin = 10
    defaults.batchIntervalMin  = 20
    reasoning.push('Low threat → relaxed pipeline')
  }

  // Adapt based on intel volume
  if (recentIntelCount > 20) {
    defaults.ingestIntervalMin = Math.min(defaults.ingestIntervalMin, 3)
    reasoning.push(`High intel volume (${recentIntelCount} in 30m) → faster ingest`)
  }

  // Adapt based on error rate
  if (errorRate > 0.4) {
    defaults.enhancementEnabled = false
    defaults.aiTier = 'mini'
    reasoning.push(`High error rate (${Math.round(errorRate * 100)}%) → throttling AI enhancement`)
  }

  defaults.conflictLevel = threatLevel

  // Persist schedule config for other services to read
  await sb.from('platform_config').upsert([
    { key: 'adaptive_ingest_interval_min', value: String(defaults.ingestIntervalMin), updated_at: new Date().toISOString(), updated_by: 'ADAPTIVE_SCHEDULE' },
    { key: 'adaptive_batch_interval_min',  value: String(defaults.batchIntervalMin),  updated_at: new Date().toISOString(), updated_by: 'ADAPTIVE_SCHEDULE' },
    { key: 'adaptive_ai_tier',             value: defaults.aiTier,                    updated_at: new Date().toISOString(), updated_by: 'ADAPTIVE_SCHEDULE' },
    { key: 'adaptive_enhancement_enabled', value: String(defaults.enhancementEnabled), updated_at: new Date().toISOString(), updated_by: 'ADAPTIVE_SCHEDULE' },
    { key: 'adaptive_schedule_updated_at', value: new Date().toISOString(),            updated_at: new Date().toISOString(), updated_by: 'ADAPTIVE_SCHEDULE' },
  ])

  return defaults
}

export async function GET(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  try {
    const config = await computeAdaptiveSchedule()
    return NextResponse.json({ ok: true, config, computedAt: new Date().toISOString() })
  } catch (err) {
    return NextResponse.json({ ok: false, error: String(err) }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  return GET(req)
}
