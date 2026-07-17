/**
 * GET /api/platform/orchestrate
 *
 * Master pipeline orchestrator — runs every 3 minutes.
 *
 * Unlike individual crons (which fire on blind timers), this route checks
 * ACTUAL data freshness before deciding what to re-run. It also handles
 * the conflict-day advance event that occurs at midnight UTC each day.
 *
 * Pipeline dependency order:
 *   ingest → analyze-batch → [cross-ref, extract, digest, oracle, foresight]
 *
 * Staleness thresholds (tuned to be slightly looser than cron intervals):
 *   ingest:        > 6 min  (cron fires every 5 min)
 *   analyze-batch: > 18 min (cron fires every 15 min)
 *
 * Day-advance cascade (fires on midnight UTC conflict-day increment):
 *   newsroom/seed, analyze-batch, intel/digest, oracle/enhance, intel/foresight,
 *   intel/forecast, intel/world
 *
 * Schedule: every 3 minutes (see vercel.json)
 * Auth: Bearer CRON_SECRET  or  x-vercel-cron: 1
 */

import { NextRequest, NextResponse, after } from 'next/server'
import { createClient }   from '@supabase/supabase-js'
import { getConflictDay } from '@/lib/conflict-day'
import { logAgentRun }    from '@/lib/agent-run-logger'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0
export const maxDuration = 60

// How long (ms) a stage must be stale before orchestrate re-fires it
const SLA = {
  ingest: 6   * 60_000,
  batch:  18  * 60_000,
}
// Minimum gap between orchestrate runs (anti-stampede)
const THROTTLE_MS = 2.5 * 60_000

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET?.trim()
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true
  }
  if (req.headers.get('x-vercel-cron') === '1') return true
  const auth = req.headers.get('authorization') ?? ''
  return auth === `Bearer ${secret}`
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------
export async function GET(req: NextRequest) {
  const startedAtIso = new Date().toISOString()
  const startedAtMs = Date.now()

  if (!isAuthorized(req)) {
    void logAgentRun({
      agentName: 'ORCHESTRATE',
      route: '/api/platform/orchestrate',
      trigger: req.headers.get('x-vercel-cron') === '1' ? 'cron' : 'manual',
      status: 'FAILED',
      errorMessage: 'Unauthorized',
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!supaUrl || !supaKey) {
    void logAgentRun({
      agentName: 'ORCHESTRATE',
      route: '/api/platform/orchestrate',
      trigger: req.headers.get('x-vercel-cron') === '1' ? 'cron' : 'manual',
      status: 'FAILED',
      errorMessage: 'Supabase not configured',
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({ ok: false, error: 'Supabase not configured' }, { status: 503 })
  }

  const sb          = createClient(supaUrl, supaKey)
  const now         = Date.now()
  const conflictDay = getConflictDay()
  const baseUrl     = process.env.NEXT_PUBLIC_SITE_URL
    ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3003')
  const secret = process.env.CRON_SECRET ?? ''

  // ── 1. Read freshness data + throttle state ──────────────────────────────
  const [intelRes, batchRes, cfgRes] = await Promise.allSettled([
    sb.from('intel')
      .select('created_at')
      .order('created_at', { ascending: false })
      .limit(1),
    sb.from('model_snapshots')
      .select('created_at')
      .order('created_at', { ascending: false })
      .limit(1),
    sb.from('platform_config')
      .select('key, value')
      .in('key', ['orchestrate_last_run', 'last_known_conflict_day']),
  ])

  const lastIntelMs = intelRes.status === 'fulfilled' && intelRes.value.data?.[0]?.created_at
    ? new Date(intelRes.value.data[0].created_at as string).getTime()
    : 0

  const lastBatchMs = batchRes.status === 'fulfilled' && batchRes.value.data?.[0]?.created_at
    ? new Date(batchRes.value.data[0].created_at as string).getTime()
    : 0

  const cfg: Record<string, string> = {}
  if (cfgRes.status === 'fulfilled') {
    for (const r of (cfgRes.value.data ?? [])) cfg[r.key as string] = r.value as string
  }

  const lastOrchMs   = cfg['orchestrate_last_run'] ? new Date(cfg['orchestrate_last_run']).getTime() : 0
  const lastKnownDay = parseInt(cfg['last_known_conflict_day'] ?? '0', 10)

  // ── 2. Anti-stampede throttle ────────────────────────────────────────────
  if (now - lastOrchMs < THROTTLE_MS) {
    void logAgentRun({
      agentName: 'ORCHESTRATE',
      route: '/api/platform/orchestrate',
      trigger: req.headers.get('x-vercel-cron') === '1' ? 'cron' : 'manual',
      status: 'SKIPPED',
      conflictDay: conflictDay,
      durationMs: Date.now() - startedAtMs,
      detail: {
        reason: 'throttled',
      },
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({
      ok:             true,
      skipped:        true,
      reason:         'throttled',
      nextEligibleMs: Math.round(THROTTLE_MS - (now - lastOrchMs)),
      generatedAt:    new Date().toISOString(),
    })
  }

  // Stamp this run immediately so concurrent invocations throttle out
  void sb.from('platform_config').upsert({
    key:        'orchestrate_last_run',
    value:      new Date().toISOString(),
    updated_at: new Date().toISOString(),
    updated_by: 'ORCHESTRATE_CRON',
  })

  // ── 3. Staleness + day-advance detection ─────────────────────────────────
  const ingestStale = now - lastIntelMs > SLA.ingest
  const batchStale  = now - lastBatchMs > SLA.batch
  const dayAdvanced = lastKnownDay > 0 && conflictDay > lastKnownDay
  const isFirstRun  = lastKnownDay === 0

  const actionsQueued: string[] = []
  if (ingestStale || dayAdvanced)                  actionsQueued.push('ingest')
  if (batchStale  || dayAdvanced)                  actionsQueued.push('analyze-batch')
  if (dayAdvanced || isFirstRun)                   actionsQueued.push('newsroom-seed', 'digest', 'oracle', 'foresight', 'forecast', 'world')

  // Persist new conflict day if advanced
  if (dayAdvanced || isFirstRun) {
    void sb.from('platform_config').upsert({
      key:        'last_known_conflict_day',
      value:      String(conflictDay),
      updated_at: new Date().toISOString(),
      updated_by: 'ORCHESTRATE_CRON',
    })
  }

  // ── 4. Fire recovery actions post-response (non-blocking) ────────────────
  if (actionsQueued.length > 0) {
    after(async () => {
      const h: HeadersInit = secret
        ? { Authorization: `Bearer ${secret}`, 'Cache-Control': 'no-store' }
        : { 'Cache-Control': 'no-store' }

      const fire = (path: string, method = 'GET') =>
        fetch(`${baseUrl}${path}`, { method, headers: h, signal: AbortSignal.timeout(55_000) })
          .catch(() => null)

      if (ingestStale || dayAdvanced) await fire('/api/ingest')
      if (batchStale  || dayAdvanced) await fire('/api/analyze-batch', 'POST')

      if (dayAdvanced || isFirstRun) {
        // Fire day-sensitive pipelines in parallel (they're independent of each other)
        await Promise.allSettled([
          fire('/api/newsroom/seed'),
          fire('/api/intel/digest'),
          fire('/api/oracle/enhance'),
          fire('/api/intel/foresight'),
          fire('/api/intel/forecast'),
          fire('/api/intel/world'),
        ])

        // Log day advance event
        try {
          await sb.from('platform_config').upsert({
            key:        `day_advance_${conflictDay}`,
            value:      new Date().toISOString(),
            updated_at: new Date().toISOString(),
            updated_by: 'ORCHESTRATE_CRON',
          })
        } catch { /* non-blocking */ }
      }
    })
  }

  void logAgentRun({
    agentName: 'ORCHESTRATE',
    route: '/api/platform/orchestrate',
    trigger: req.headers.get('x-vercel-cron') === '1' ? 'cron' : 'manual',
    status: 'SUCCESS',
    conflictDay: conflictDay,
    durationMs: Date.now() - startedAtMs,
    detail: {
      actionsQueued,
      dayAdvanced,
      isFirstRun,
    },
    startedAt: startedAtIso,
    finishedAt: new Date().toISOString(),
  })

  return NextResponse.json({
    ok:           true,
    conflictDay,
    dayAdvanced,
    isFirstRun,
    stale: {
      ingest: ingestStale,
      batch:  batchStale,
    },
    actionsQueued,
    msSinceLastIntel: lastIntelMs > 0 ? now - lastIntelMs : null,
    msSinceLastBatch: lastBatchMs > 0 ? now - lastBatchMs : null,
    generatedAt: new Date().toISOString(),
  })
}
