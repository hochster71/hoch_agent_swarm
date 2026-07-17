/**
 * /api/governor/heartbeat — Temporal-style scheduled self-review
 *
 * Called by Vercel Cron to force a periodic governor cycle even during
 * low-activity periods. This is the "Temporal heartbeat" analogue.
 *
 * Recommended cron schedule: every 15 minutes (vercel.json already configured)
 *
 * GET  /api/governor/heartbeat  — run a heartbeat governor cycle
 * POST /api/governor/heartbeat  — same (for Vercel Cron compatibility)
 *
 * Auth: Bearer CRON_SECRET
 */

import { NextRequest, NextResponse }        from 'next/server'
import { runGovernorCycle }                 from '@/lib/governor'
import { runAutonomousEnhancementCycle }    from '@/lib/autonomous-engine'
import { createClient }                     from '@supabase/supabase-js'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const maxDuration = 300   // AEC needs extra headroom

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET?.trim()
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true  // dev mode
  }
  if (req.headers.get('x-vercel-cron') === '1') return true
  const auth = req.headers.get('Authorization') ?? ''
  if (auth === `Bearer ${secret}`) return true
  // Fallback: custom header used by the platform/heartbeat proxy (Vercel strips
  // the Authorization header on same-deployment server-to-server fetch calls).
  const internalToken = req.headers.get('X-Nexus-Internal-Token') ?? ''
  return internalToken === secret
}

/** Returns true every aec_every_n_heartbeats heartbeats (default 5) */
async function shouldRunAEC(): Promise<boolean> {
  try {
    const sb = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
    )
    const [cycleRes, intervalRes] = await Promise.all([
      sb.from('platform_config').select('value').eq('key', 'autonomous_cycle_count').single(),
      sb.from('platform_config').select('value').eq('key', 'aec_every_n_heartbeats').single(),
    ])
    const cycleCount = parseInt(cycleRes.data?.value ?? '0', 10)
    // Default 3 heartbeats = AEC fires every 45 min (was 5 = 75 min)
    const interval   = parseInt(intervalRes.data?.value ?? '3', 10)
    // Also count total governor cycles for the modulo
    const { count } = await sb.from('governor_cycles').select('id', { count: 'exact' }).limit(1)
    return ((count ?? 0) % interval === 0) || (cycleCount === 0)
  } catch {
    return false
  }
}

async function handleHeartbeat(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    // ── Main 9-layer Governor cycle ───────────────────────────────────────────
    const report = await runGovernorCycle('heartbeat')

    // ── Autonomous Enhancement Cycle (AEC) — fires every N heartbeats ─────────
    let aecResult = null
    if (await shouldRunAEC()) {
      // Run in background — non-blocking relative to response so Vercel 300s is enough
      aecResult = await runAutonomousEnhancementCycle(report.conflictDay)
    }

    return NextResponse.json({
      ok:                true,
      cycleId:           report.cycleId,
      conflictDay:       report.conflictDay,
      layersCompleted:   report.layersCompleted,
      entitiesExtracted: report.entitiesExtracted,
      claimsVerified:    report.claimsVerified,
      urgentEscalations: report.urgentEscalations.length,
      shouldLoop:        report.shouldLoop,
      durationMs:        report.totalDurationMs,
      kgStats:           report.kgStats,
      synthesis: report.synthesisReport ? {
        threatLevel:      report.synthesisReport.threatLevel,
        headline:         report.synthesisReport.headline,
        confidenceScore:  report.synthesisReport.confidenceScore,
        actionsCount:     report.synthesisReport.recommendedActions?.length ?? 0,
      } : null,
      aec: aecResult ? {
        cycleNumber:      aecResult.cycleNumber,
        enhancementType:  aecResult.enhancement.type,
        enhancementTitle: aecResult.enhancement.title,
        deploymentStatus: aecResult.deploymentStatus,
        prUrl:            aecResult.prUrl ?? null,
        autoMerged:       aecResult.autoMerged,
        durationMs:       aecResult.durationMs,
      } : null,
      generatedAt: new Date().toISOString(),
    })
  } catch (err) {
    return NextResponse.json({ ok: false, error: String(err) }, { status: 500 })
  }
}

export async function GET(req: NextRequest) {
  return handleHeartbeat(req)
}

export async function POST(req: NextRequest) {
  return handleHeartbeat(req)
}
