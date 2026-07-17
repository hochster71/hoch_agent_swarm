/**
 * /api/governor — EPIC FURY 2026 Platform Governor API
 *
 * POST /api/governor          — trigger a full 7-layer governor cycle
 * GET  /api/governor          — fetch last N governor cycles (audit log)
 * GET  /api/governor?live=1   — trigger a readonly state snapshot (no mutations)
 *
 * Auth: Bearer CRON_SECRET (same pattern as heal + ingest routes)
 * If CRON_SECRET is unset, the route is open (dev mode)
 *
 * The governor is designed to run in ≤ 2 minutes within serverless limits.
 * For production durable execution, wrap in a Temporal workflow or Vercel Cron.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'
import { runGovernorCycle, type GovernorTrigger } from '@/lib/governor'
import { computeKGStats }            from '@/lib/kg-engine'
import { computeVisualStats }        from '@/lib/visual-engine'
import { computeRevenueStats }       from '@/lib/revenue-engine'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const maxDuration = 120  // Vercel Pro: 2-minute max duration

// ---------------------------------------------------------------------------
// Auth helper
// ---------------------------------------------------------------------------
function isAuthorized(req: NextRequest): boolean {
  if (req.headers.get('x-vercel-cron') === '1') return true
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true  // dev mode
  }
  const auth = req.headers.get('Authorization') ?? ''
  return auth === `Bearer ${secret}`
}

// ---------------------------------------------------------------------------
// POST — run full governor cycle
// ---------------------------------------------------------------------------
export async function POST(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Parse optional trigger override
  let trigger: GovernorTrigger = 'manual'
  try {
    const body = await req.json() as { trigger?: string }
    if (['heartbeat', 'manual', 'heal_escalation', 'error_escalation', 'boot'].includes(body.trigger ?? '')) {
      trigger = body.trigger as GovernorTrigger
    }
  } catch { /* no body — use default */ }

  try {
    const report = await runGovernorCycle(trigger)
    return NextResponse.json(report)
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

// ---------------------------------------------------------------------------
// GET — audit log + live KG stats (read-only, open for operator dashboard)
// ---------------------------------------------------------------------------
export async function GET(req: NextRequest) {

  const url   = new URL(req.url)
  const limit = Math.min(50, parseInt(url.searchParams.get('limit') ?? '10', 10))

  const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supaKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!supaUrl || !supaKey) {
    return NextResponse.json({ error: 'Supabase credentials not configured' }, { status: 500 })
  }

  const sb = createClient(supaUrl, supaKey, { auth: { persistSession: false } })

  const [
    { data: cycles, error: cyclesErr },
    kgStats,
    visualStats,
    revenueStats,
  ] = await Promise.all([
    sb.from('governor_cycles')
      .select('id, conflict_day, trigger, layer_reached, entities_extracted, claims_verified, mutations_proposed, mutations_applied, neural_health_before, neural_health_after, duration_ms, error, created_at')
      .order('created_at', { ascending: false })
      .limit(limit),
    computeKGStats(),
    computeVisualStats(),
    computeRevenueStats(),
  ])

  if (cyclesErr) {
    console.warn('[governor] governor_cycles table unavailable:', cyclesErr.message)
    // table may not exist yet — fall through with empty cycles
  }

  // Aggregate totals
  const rows = (cycles ?? []) as {
    layer_reached: number
    entities_extracted: number
    claims_verified: number
    mutations_applied: number
    duration_ms: number
  }[]

  const n = rows.length || 1  // guard division-by-zero when table is empty
  const totals = rows.reduce(
    (acc, r) => ({
      avgLayers:        acc.avgLayers + r.layer_reached / n,
      totalEntities:    acc.totalEntities + r.entities_extracted,
      totalClaims:      acc.totalClaims + r.claims_verified,
      totalMutations:   acc.totalMutations + r.mutations_applied,
      avgDurationMs:    acc.avgDurationMs + r.duration_ms / n,
    }),
    { avgLayers: 0, totalEntities: 0, totalClaims: 0, totalMutations: 0, avgDurationMs: 0 },
  )

  return NextResponse.json({
    cycles:     cycles ?? [],
    kgStats,
    visualStats,
    revenueStats,
    summary: {
      cyclesReturned: rows.length,
      avgLayersCompleted: Math.round(totals.avgLayers * 10) / 10,
      totalEntitiesExtracted: totals.totalEntities,
      totalClaimsVerified: totals.totalClaims,
      totalMutationsApplied: totals.totalMutations,
      avgDurationMs: Math.round(totals.avgDurationMs),
    },
    generatedAt: new Date().toISOString(),
  })
}
