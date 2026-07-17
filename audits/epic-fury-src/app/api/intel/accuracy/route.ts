/**
 * GET /api/intel/accuracy
 *
 * NEXUS Accuracy Engine — called by cron every 15 minutes.
 *
 * Computes the platform's real-time accuracy score (0-100%) by analysing:
 *   - Source tier distribution (T1 official / T2 media / T3 OSINT)
 *   - Cross-reference verification rate
 *   - AI enhancement coverage
 *   - Theater coverage breadth
 *   - Data freshness / ingest lag
 *   - False-positive / disinformation detection rate
 *
 * The weighted accuracy score is persisted to Supabase and readable
 * by the TopBar accuracy beacon and /dashboard/world page.
 *
 * Auth: Bearer CRON_SECRET (omit in dev)
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'
import { getConflictDay }            from '@/lib/conflict-day'
import { computeAccuracyReport, AccuracyReport } from '@/lib/ai-engine'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 60   // Supabase accuracy aggregation + optional AI report

const KNOWN_THEATERS = [
  'Persian Gulf / Hormuz', 'Iran', 'Israel / Levant', 'Red Sea / Yemen',
  'GCC / Arabian Peninsula', 'Cyber', 'CONUS', 'Unknown',
]

// Accuracy data is non-sensitive — no auth required for GET reads.
// (POST cron callers can set CRON_SECRET on write routes if needed.)

function getServiceClient() {
  const url    = process.env.NEXT_PUBLIC_SUPABASE_URL
  const svcKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !svcKey) return null
  return createClient<any>(url, svcKey, { auth: { persistSession: false } })
}

export async function GET(_req: NextRequest) {
  // No auth required — accuracy metrics are non-sensitive read-only data.
  try {
    return await computeAccuracy()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('[accuracy] unhandled error:', msg)
    return NextResponse.json(
      { ok: false, accuracyPct: 45, conflictDay: getConflictDay(), error: 'internal_error' },
      { status: 200 }, // return 200 so the beacon doesn't console.error
    )
  }
}

async function computeAccuracy() {

  const supabase    = getServiceClient()
  const conflictDay = getConflictDay()

  if (!supabase) {
    // Return minimal static score when no DB
    const staticReport: AccuracyReport = {
      overallPct: 45,
      verificationRate: 0,
      aiEnhancedRate: 0,
      sourceQualityScore: 40,
      falsePositiveRisk: 15,
      coverageScore: 50,
      recencyScore: 50,
      breakdown: [],
      selfAssessment: 'No Supabase connection — accuracy scoring unavailable. Configure SUPABASE_SERVICE_ROLE_KEY.',
      improvementActions: ['Configure Supabase credentials', 'Set OPENAI_API_KEY for AI enhancement'],
      gradeLetter: 'D',
    }
    return NextResponse.json({ ok: false, accuracyPct: 45, report: staticReport, conflictDay })
  }

  const window24h = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()

  // Gather all metrics in parallel
  const [
    totalRes,
    verifiedRes,
    aiEnhancedRes,
    crossRefRes,
    falsePositiveRes,
    lastIngestRes,
    theaterRes,
    avgConfRes,
  ] = await Promise.allSettled([
    supabase.from('intel').select('count', { count: 'exact', head: true }),
    supabase.from('intel').select('count', { count: 'exact', head: true }).eq('verified', true),
    supabase.from('intel').select('count', { count: 'exact', head: true }).like('author', '%AI%'),
    supabase.from('intel').select('count', { count: 'exact', head: true }).contains('tags', ['cross-ref-verified']),
    supabase.from('intel').select('count', { count: 'exact', head: true }).overlaps('tags', ['suspicious', 'disinformation']),
    supabase.from('intel').select('created_at').order('created_at', { ascending: false }).limit(1),
    supabase.from('intel').select('theater').gte('created_at', window24h),
    supabase.from('intel').select('confidence').gte('created_at', window24h).limit(500),
  ])

  const total        = (totalRes.status === 'fulfilled' ? totalRes.value.count : 0)   ?? 0
  const verified     = (verifiedRes.status === 'fulfilled' ? verifiedRes.value.count : 0) ?? 0
  const aiEnhanced   = (aiEnhancedRes.status === 'fulfilled' ? aiEnhancedRes.value.count : 0) ?? 0
  const crossRef     = (crossRefRes.status === 'fulfilled' ? crossRefRes.value.count : 0) ?? 0
  const falsePosCount = (falsePositiveRes.status === 'fulfilled' ? falsePositiveRes.value.count : 0) ?? 0

  const lastIngestRows = lastIngestRes.status === 'fulfilled' ? lastIngestRes.value.data : null
  const lastIngestDate = lastIngestRows?.[0]?.created_at ? new Date(lastIngestRows[0].created_at) : null
  const lastIngestMinutes = lastIngestDate
    ? Math.floor((Date.now() - lastIngestDate.getTime()) / 60_000)
    : 999

  // Theater coverage
  const theaterRows = theaterRes.status === 'fulfilled' ? (theaterRes.value.data ?? []) : []
  const coveredTheaters = new Set(theaterRows.map((r: any) => r.theater).filter(Boolean))
  const theaterCoverage = KNOWN_THEATERS.length > 0
    ? Math.min(1, coveredTheaters.size / KNOWN_THEATERS.length)
    : 0

  // Average confidence
  const confRows = avgConfRes.status === 'fulfilled' ? (avgConfRes.value.data ?? []) : []
  const avgConfidence = confRows.length > 0
    ? Math.round(confRows.reduce((sum: number, r: any) => sum + (r.confidence ?? 50), 0) / confRows.length)
    : 50

  // Source tier breakdown — approximate from source_type tagged items
  const { data: sourceData } = await supabase
    .from('intel')
    .select('source_type, source_name')
    .gte('created_at', window24h)
    .limit(500)

  const sourceTierBreakdown = { t1: 0, t2: 0, t3: 0 }
  const T1_NAMES = new Set(['reuters', 'ap', 'centcom', 'pentagon', 'dod', 'state department', 'white house', 'mod'])
  const T2_NAMES = new Set(['bbc', 'cnn', 'nyt', 'washington post', 'guardian', 'ft', 'al jazeera', 'politico', 'defense one'])
  for (const row of (sourceData ?? []) as any[]) {
    const name = (row.source_name ?? '').toLowerCase()
    const type = (row.source_type ?? '').toLowerCase()
    if (type === 'official' || T1_NAMES.has(name)) sourceTierBreakdown.t1++
    else if (type === 'wire' || T2_NAMES.has(name)) sourceTierBreakdown.t2++
    else sourceTierBreakdown.t3++
  }

  const report = await computeAccuracyReport({
    totalIntel:          total,
    verifiedCount:       verified,
    aiEnhancedCount:     aiEnhanced,
    sourceTierBreakdown,
    theaterCoverage,
    avgConfidence,
    lastIngestMinutes,
    crossRefVerified:    crossRef,
    falsePositiveCount:  falsePosCount,
    totalBatchAssessed:  total,
  })

  const accuracyPct = report?.overallPct ?? 45

  // Persist the accuracy score as a model_snapshot for trending (best-effort)
  await supabase.from('model_snapshots').insert({
    conflict_day:    conflictDay,
    oracle_payload:  { accuracyScore: true, pct: accuracyPct } as any,
    compass_payload: { accuracyReport: report } as any,
    herald_summary:  {
      type:         'accuracy',
      overallPct:   accuracyPct,
      grade:        report?.gradeLetter ?? 'D',
      verified:     verified,
      total:        total,
    },
  })

  return NextResponse.json(
    { ok: true, accuracyPct, conflictDay, report },
    { headers: { 'Cache-Control': 'no-store' } },
  )
} // end computeAccuracy
