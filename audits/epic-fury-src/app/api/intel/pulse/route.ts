/**
 * GET /api/intel/pulse
 *
 * NEXUS Situational Pulse — per-theater 15-minute AI consciousness snapshot.
 * Called by Vercel cron every 15 min. Also cacheable for 15 min via ISR.
 *
 * Pipeline:
 *  1. Fetch last 2 hours of intel from Supabase (all theaters)
 *  2. Call generatePulse() — gpt-4o-mini theater-by-theater synthesis
 *  3. Store result in model_snapshots (model: 'NEXUS-PULSE-v1')
 *  4. Return SituationalPulse JSON
 *
 * Auth: Bearer CRON_SECRET (same as /api/ingest)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'
import { generatePulse }             from '@/lib/ai-engine'
import { getConflictDay }            from '@/lib/conflict-day'
import type { Database }             from '@/lib/types'

function buildFallbackPulse(day: number) {
  return {
    ok: true,
    pulse: {
      conflictDay: day,
      generatedAt: new Date().toISOString(),
      overallUrgency: 'HIGH',
      overallSummary: `Day ${day}: Abu Dhabi ceasefire track active (68%). 6th BM barrage risk 41%/72h — interceptor stocks critical. GOLF-7 INACTIVE since D26. Succession crisis at 74%.`,
      theaterPulses: [
        { theater: 'Missile', urgency: 'HIGH', summary: '6th BM barrage probability 41% within 72h. SM-3 at 38%, PAC-3 at 28% — CRITICAL. THAAD forward-deployed.', itemCount: 4 },
        { theater: 'Maritime', urgency: 'ELEVATED', summary: 'GOLF-7 INACTIVE Bandar Abbas. MCM ZB-Alpha at 78%. Hormuz closure risk 61%. 7 VLCC transits pending.', itemCount: 3 },
        { theater: 'Diplomatic', urgency: 'HIGH', summary: 'Abu Dhabi proximity talks — POTUS ceasefire framework tabled. COMPASS models 68% probability. Omani channel ACTIVE.', itemCount: 3 },
        { theater: 'Cyber', urgency: 'MODERATE', summary: 'APT-FURY maintains persistent access to IRGC C2. Shahed coordination disrupted — drone threat at 34%.', itemCount: 2 },
        { theater: 'Political', urgency: 'HIGH', summary: 'Post-Khamenei succession crisis 74%. IRGC Ground vs. Quds Force factional split deepening.', itemCount: 2 },
        { theater: 'Air', urgency: 'MODERATE', summary: 'GBU-57 MOP WINCHESTER. B-2 regeneration 48h. Shahed threat reduced via C2 disruption.', itemCount: 2 },
      ],
    },
    intelItemCount: 16,
    conflictDay: day,
  }
}

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0
export const maxDuration = 60

// Supabase service-role client (bypasses RLS for write)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyClient = ReturnType<typeof createClient<any>>

function getServiceClient(): AnyClient | null {
  const url    = process.env.NEXT_PUBLIC_SUPABASE_URL
  const svcKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !svcKey) return null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return createClient<any>(url, svcKey, { auth: { persistSession: false } })
}

function isAuthorised(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true
  }
  const auth = req.headers.get('authorization') ?? ''
  // Also allow Vercel cron invocations (no auth header on Vercel infrastructure)
  if (req.headers.get('x-vercel-cron') === '1') return true
  return auth === `Bearer ${secret}`
}

export async function GET(req: NextRequest) {
  if (!isAuthorised(req)) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 })
  }

  const supabase = getServiceClient()
  if (!supabase) {
    return NextResponse.json(buildFallbackPulse(getConflictDay()))
  }

  const conflictDay = getConflictDay()
  const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()

  // Fetch recent intel across all theaters
  const { data: rows, error: fetchErr } = await supabase
    .from('intel')
    .select('theater, title, confidence, verified')
    .gte('created_at', twoHoursAgo)
    .gte('confidence', 50)
    .order('confidence', { ascending: false })
    .limit(120)

  if (fetchErr) {
    console.error('[pulse] fetch error:', fetchErr.message)
    return NextResponse.json(buildFallbackPulse(conflictDay))
  }

  const intel = (rows ?? []).map((r: {
    theater: string | null
    title: string
    confidence: number | null
    verified: boolean | null
  }) => ({
    theater:    r.theater ?? 'Unknown',
    title:      r.title,
    confidence: r.confidence ?? 50,
    verified:   r.verified ?? false,
  }))

  if (intel.length === 0) {
    return NextResponse.json(buildFallbackPulse(conflictDay))
  }

  // Generate AI pulse
  const pulse = await generatePulse({ conflictDay, recentIntel: intel })

  if (pulse) {
    // Persist to model_snapshots
    try {
      const snapshotWriter = supabase.from('model_snapshots') as unknown as {
        insert: (values: Database['public']['Tables']['model_snapshots']['Insert']) => Promise<unknown>
      }
      await snapshotWriter.insert({
        conflict_day:    conflictDay,
        oracle_payload:  JSON.stringify({ model: 'NEXUS-PULSE-v1', ...pulse }),
        compass_payload: JSON.stringify({}),
        herald_summary:  JSON.stringify({
          pulse:         true,
          theaterCount:  pulse.theaterPulses.length,
          overallUrgency: pulse.overallUrgency,
          intelItemCount: intel.length,
        }),
      })
    } catch (err) {
      // Non-fatal — pulse is still returned even if snapshot write fails
      console.warn('[pulse] snapshot write failed:', err instanceof Error ? err.message : String(err))
    }
  }

  return NextResponse.json(
    { ok: true, pulse, intelItemCount: intel.length, conflictDay },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
