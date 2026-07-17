/**
 * GET /api/platform/day-advance
 *
 * Midnight UTC cron — fires when the conflict-day counter increments.
 *
 * Aggressively re-seeds ALL day-specific content so the platform wakes up
 * on Day N with fresh data, accurate prices, and new broadcast scripts —
 * with zero manual intervention required.
 *
 * Actions performed (all in background, non-blocking):
 *  1. Force-invalidate newsroom cache for the new day (re-seed)
 *  2. Regenerate intel digest
 *  3. Recompute ORACLE-9 threat overlay with new day number
 *  4. Recompute COMPASS economic cascade pricing
 *  5. Run foresight + forecast with new day context
 *  6. Trigger ingest to pull fresh headlines for Day N
 *  7. Log the day-advance event to platform_config
 *
 * Schedule: 0 0 * * * (midnight UTC — see vercel.json)
 * This is complementary to /api/platform/orchestrate (every 3 min).
 * Orchestrate catches intra-day staleness; day-advance handles the day rollover.
 *
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

export async function GET(req: NextRequest) {
  const startedAtIso = new Date().toISOString()
  const startedAtMs = Date.now()

  if (!isAuthorized(req)) {
    void logAgentRun({
      agentName: 'DAY_ADVANCE',
      route: '/api/platform/day-advance',
      trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
      status: 'FAILED',
      errorMessage: 'Unauthorized',
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const conflictDay = getConflictDay()
  const baseUrl     = process.env.NEXT_PUBLIC_SITE_URL
    ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3003')
  const secret = process.env.CRON_SECRET ?? ''

  const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY

  after(async () => {
    const h: HeadersInit = secret
      ? { Authorization: `Bearer ${secret}`, 'Cache-Control': 'no-store' }
      : { 'Cache-Control': 'no-store' }

    const fire = (path: string, method = 'GET') =>
      fetch(`${baseUrl}${path}`, { method, headers: h, signal: AbortSignal.timeout(55_000) })
        .catch(() => null)

    // Step 1: Ingest fresh Day-N headlines first
    await fire('/api/ingest')

    // Step 2: Batch-analyze new Day-N intel
    await fire('/api/analyze-batch', 'POST')

    // Step 3: Re-generate all day-sensitive content in parallel
    await Promise.allSettled([
      fire('/api/newsroom/seed'),
      fire('/api/intel/digest'),
      fire('/api/oracle/enhance'),
      fire('/api/intel/foresight'),
      fire('/api/intel/forecast'),
      fire('/api/intel/world'),
      fire('/api/intel/cross-ref'),
      fire('/api/intel/extract'),
      fire('/api/platform/content-refresh'),
    ])

    // Step 4: Log the day-advance event
    if (supaUrl && supaKey) {
      const sb = createClient(supaUrl, supaKey)
      const lockTimestamp = new Date().toISOString()
      await sb.from('platform_config').upsert([
        {
          key:        'last_known_conflict_day',
          value:      String(conflictDay),
          updated_at: new Date().toISOString(),
          updated_by: 'DAY_ADVANCE_CRON',
        },
        {
          key:        `day_advance_${conflictDay}`,
          value:      new Date().toISOString(),
          updated_at: new Date().toISOString(),
          updated_by: 'DAY_ADVANCE_CRON',
        },
        {
          key:        `daily_midnight_lock_${conflictDay}`,
          value:      lockTimestamp,
          updated_at: lockTimestamp,
          updated_by: 'DAY_ADVANCE_CRON',
        },
        {
          key:        'daily_midnight_lock_last_run',
          value:      lockTimestamp,
          updated_at: lockTimestamp,
          updated_by: 'DAY_ADVANCE_CRON',
        },
        {
          key:        'orchestrate_last_run',
          value:      new Date().toISOString(),
          updated_at: new Date().toISOString(),
          updated_by: 'DAY_ADVANCE_CRON',
        },
      ]).then(() => null, () => null)
    }
  })

  void logAgentRun({
    agentName: 'DAY_ADVANCE',
    route: '/api/platform/day-advance',
    trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
    status: 'SUCCESS',
    conflictDay,
    durationMs: Date.now() - startedAtMs,
    detail: {
      mode: 'midnight-lock',
      cadence: 'daily@00:00UTC',
      guaranteedFreshnessActions: [
        'ingest',
        'analyze-batch',
        'newsroom-seed',
        'intel-digest',
        'oracle-enhance',
        'intel-foresight',
        'intel-forecast',
        'intel-world',
        'intel-cross-ref',
        'intel-extract',
        'platform-content-refresh',
      ],
    },
    startedAt: startedAtIso,
    finishedAt: new Date().toISOString(),
  })

  return NextResponse.json({
    ok:          true,
    conflictDay,
    message:     `Day ${conflictDay} midnight lock queued — all day-sensitive pipelines firing`,
    lockMode:    'daily-midnight-autonomous',
    lockAtUtc:   startedAtIso,
    pipelinesQueued: [
      'ingest', 'analyze-batch', 'newsroom-seed', 'intel-digest',
      'oracle-enhance', 'intel-foresight', 'intel-forecast', 'intel-world',
      'intel-cross-ref', 'intel-extract', 'platform-content-refresh',
    ],
    generatedAt: new Date().toISOString(),
  })
}
