/**
 * GET /api/intel/calibration-cron
 *
 * Cron-safe ORACLE-9 prediction calibration runner.
 *
 * Vercel crons can only invoke GET endpoints. This route:
 *   1. Fetches the current ORACLE-9 threat probability distribution
 *   2. Snapshots active threats as new calibration predictions (via logOraclePrediction)
 *   3. Evaluates any expired, unevaluated predictions (via evaluateExpiredPredictions)
 *
 * Over time this builds a calibration dataset that measures ORACLE-9 accuracy
 * and surfaces in the ORACLE-9 dashboard's accuracy / Brier score panel.
 *
 * Schedule: every 30 minutes (see vercel.json)
 * Auth: same CRON_SECRET as all other cron routes
 */

import { NextRequest, NextResponse } from 'next/server'
import { computeAllThreats }           from '@/lib/oracle-engine'
import { getConflictDay }              from '@/lib/conflict-day'
import { logOraclePrediction, evaluateExpiredPredictions } from '@/lib/synthesis-engine'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0
export const maxDuration = 120

function isAuthorized(req: NextRequest): boolean {
  if (req.headers.get('x-vercel-cron') === '1') return true
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true
  }
  const auth = req.headers.get('Authorization') ?? ''
  return auth === `Bearer ${secret}`
}

export async function GET(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const day     = getConflictDay()
  const snapped: string[] = []
  let   evaluated = 0
  let   snapshotOk = true
  let   evalOk     = true

  // ── 1. Snapshot current Oracle threats ────────────────────────────────────
  try {
    const threats = computeAllThreats(day)
    for (const threat of threats) {
      // Deterministic dedup key: slug + day + window
      const slug       = threat.label.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 40)
      const windowHours = threat.severity === 'CRITICAL' ? 24
                        : threat.severity === 'HIGH'     ? 48
                        : threat.severity === 'MODERATE' ? 72
                        : 168  // LOW → 1 week
      const key        = `${slug}_day${day}_${windowHours}h`

      // probability in oracle is 0-1; logOraclePrediction expects 0-100
      const prob100 = Math.round(threat.probability * 1000) / 10

      await logOraclePrediction(key, day, threat.label, prob100, windowHours)
      snapped.push(key)
    }
  } catch (err) {
    snapshotOk = false
    console.error('[calibration-cron] snapshot error:', err)
  }

  // ── 2. Evaluate expired predictions ───────────────────────────────────────
  try {
    evaluated = await evaluateExpiredPredictions()
  } catch (err) {
    evalOk = false
    console.error('[calibration-cron] evaluation error:', err)
  }

  return NextResponse.json({
    ok:          snapshotOk && evalOk,
    conflictDay: day,
    generatedAt: new Date().toISOString(),
    snapshotOk,
    evalOk,
    snapped:     snapped.length,
    snapKeys:    snapped,
    evaluated,
  })
}
