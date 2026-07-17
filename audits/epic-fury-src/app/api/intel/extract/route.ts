/**
 * POST /api/intel/extract
 *
 * Autonomous AI extraction pipeline — called by /api/ingest after writing new intel.
 * Runs 5 GPT-4o-mini extraction tasks in parallel on recent high-confidence intel:
 *
 *   1. Scenario events    → scenario_events table
 *   2. BDA assessments    → bda_strikes table
 *   3. ORBAT updates      → orbat_updates table
 *   4. Logistics events   → logistics_events table
 *   5. Intel reports      → intel_reports table (SIGINT/HUMINT/IMINT)
 *
 * Auth: CRON_SECRET (same as /api/ingest)
 * Gracefully returns 200 with no-op if OPENAI_API_KEY is unset.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'
import {
  extractScenarioEvents,
  extractBdaStrikes,
  extractOrbatUpdates,
  extractLogisticsEvents,
  generateIntelReports,
  AI_AVAILABLE,
  type IntelRow,
} from '@/lib/ai-extraction'
import { getConflictDay } from '@/lib/conflict-day'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyClient = ReturnType<typeof createClient<any>>

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const maxDuration = 120  // 5 parallel GPT-4o-mini extraction tasks

function getServiceClient(): AnyClient | null {
  const url    = process.env.NEXT_PUBLIC_SUPABASE_URL
  const svcKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !svcKey) return null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return createClient<any>(url, svcKey, { auth: { persistSession: false } })
}

function isAuthorised(req: NextRequest): boolean {
  if (req.headers.get('x-vercel-cron') === '1') return true
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true
  }
  const auth = req.headers.get('authorization') ?? ''
  return auth === `Bearer ${secret}`
}

// Vercel cron sends GET — delegate to same pipeline
export async function GET(req: NextRequest) {
  if (!isAuthorised(req)) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 })
  }
  try {
    return await _handleExtract()
  } catch (err) {
    console.error('[extract] unhandled error', err)
    return NextResponse.json({ ok: false, error: 'Extraction pipeline error' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  if (!isAuthorised(req)) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 })
  }
  try {
    return await _handleExtract()
  } catch (err) {
    console.error('[extract] unhandled error', err)
    return NextResponse.json({ ok: false, error: 'Extraction pipeline error' }, { status: 500 })
  }
}

async function _handleExtract() {

  if (!AI_AVAILABLE) {
    return NextResponse.json({ ok: true, message: 'AI key not set — extraction skipped', day: getConflictDay() })
  }

  const supabase = getServiceClient()
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 503 })
  }

  const day = getConflictDay()

  // Fetch last 4h of high-confidence intel (skip if already extracted recently)
  const { data: recentIntel } = await supabase
    .from('intel')
    .select('id, title, summary, theater, confidence, tags')
    .gte('created_at', new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString())
    .gte('confidence', 62)
    .order('created_at', { ascending: false })
    .limit(20)

  const intel: IntelRow[] = (recentIntel ?? []).map((r: {
    id: string; title: string; summary: string | null;
    theater: string | null; confidence: number | null; tags: string[] | null;
  }) => ({
    id:         r.id,
    title:      r.title,
    summary:    r.summary  ?? '',
    theater:    r.theater  ?? 'Unknown',
    confidence: r.confidence ?? 50,
    tags:       r.tags     ?? [],
  }))

  if (intel.length === 0) {
    return NextResponse.json({ ok: true, message: 'No recent qualifying intel', day })
  }

  // Run all 5 extraction tasks in parallel
  const [eventsResult, strikesResult, orbatResult, logisticsResult, reportsResult] =
    await Promise.allSettled([
      extractScenarioEvents(intel),
      extractBdaStrikes(intel),
      extractOrbatUpdates(intel),
      extractLogisticsEvents(intel),
      generateIntelReports(intel),
    ])

  const results = {
    intel_processed:  intel.length,
    scenario_events:  0,
    bda_strikes:      0,
    orbat_updates:    0,
    logistics_events: 0,
    intel_reports:    0,
    errors:           [] as string[],
  }

  // Write scenario events (upsert by event_id to avoid duplicates)
  if (eventsResult.status === 'fulfilled') {
    for (const ev of eventsResult.value) {
      const { error } = await supabase
        .from('scenario_events')
        .upsert(ev, { onConflict: 'event_id' })
      if (!error) results.scenario_events++
      else results.errors.push(`se: ${error.message.slice(0, 60)}`)
    }
  }

  // Write BDA strikes (insert; duplicates will naturally stack as new assessments)
  if (strikesResult.status === 'fulfilled' && strikesResult.value.length > 0) {
    const { error } = await supabase.from('bda_strikes').insert(strikesResult.value)
    if (!error) results.bda_strikes = strikesResult.value.length
    else results.errors.push(`bda: ${error.message.slice(0, 60)}`)
  }

  // Write ORBAT updates
  if (orbatResult.status === 'fulfilled' && orbatResult.value.length > 0) {
    const { error } = await supabase.from('orbat_updates').insert(orbatResult.value)
    if (!error) results.orbat_updates = orbatResult.value.length
    else results.errors.push(`orbat: ${error.message.slice(0, 60)}`)
  }

  // Write logistics events
  if (logisticsResult.status === 'fulfilled' && logisticsResult.value.length > 0) {
    const { error } = await supabase.from('logistics_events').insert(logisticsResult.value)
    if (!error) results.logistics_events = logisticsResult.value.length
    else results.errors.push(`log: ${error.message.slice(0, 60)}`)
  }

  // Write intel reports (upsert by report_id)
  if (reportsResult.status === 'fulfilled') {
    for (const rpt of reportsResult.value) {
      const { error } = await supabase
        .from('intel_reports')
        .upsert(rpt, { onConflict: 'report_id' })
      if (!error) results.intel_reports++
      else results.errors.push(`rpt: ${error.message.slice(0, 60)}`)
    }
  }

  return NextResponse.json(
    { ok: true, day, ...results, ts: new Date().toISOString() },
    { headers: { 'Cache-Control': 'no-store' } },
  )
}
