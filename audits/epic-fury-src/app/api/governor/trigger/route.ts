/**
 * POST /api/governor/trigger
 *
 * Operator-UI trigger for a manual governor cycle.  This route is intentionally
 * NOT gated by CRON_SECRET so the GovernorPanel client component can fire it
 * without baking the cron secret into the public JS bundle.
 *
 * CRON_SECRET is kept on the main /api/governor route which is only called by
 * Vercel Cron — never from client-side code.
 *
 * Middleware-level rate limiting (10 req/min per IP) prevents abuse.
 */

import { NextResponse }           from 'next/server'
import { runGovernorCycle }       from '@/lib/governor'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const maxDuration = 120   // governor cycle needs up to 2 min

export async function POST() {
  try {
    const report = await runGovernorCycle('manual')
    return NextResponse.json(report)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('[governor/trigger] cycle failed:', msg)
    return NextResponse.json({ ok: false, error: msg }, { status: 500 })
  }
}
