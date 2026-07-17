/**
 * /api/platform/status
 *
 * Aggregated health readout for the entire Epic Fury autonomous platform.
 * Queries all subsystems in parallel and returns a single structured summary.
 *
 * Systems monitored:
 *   - HERALD-3 IO Engine (ingest cron)
 *   - NEXUS Batch Analysis (analyze-batch cron)
 *   - Oracle-9 Threat Model
 *   - COMPASS Economic Model
 *   - Intel Database (row count, last write)
 *   - RSS News Pipeline (source count, item count)
 *
 * Response: PlatformStatus
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@/lib/supabase-server'
import { getConflictDay }     from '@/lib/conflict-day'
import { computeAllThreats }  from '@/lib/oracle-engine'
import { computeEconomicCascade } from '@/lib/compass-engine'
import { AI_AVAILABLE } from '@/lib/ai-engine'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0

export interface SystemStatus {
  name:       string
  status:     'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'
  lastSeen:   string | null   // ISO
  detail:     string
  metric?:    string          // optional key KPI
}

export interface PlatformStatus {
  ok:              boolean
  conflictDay:     number
  generatedAt:     string
  systems:         SystemStatus[]
  // tallies
  intelTotal:      number
  intelHerald:     number        // HERALD-3 authored
  ingestRuns:      number
  batchRuns:       number
  newsItems:       number
  topThreat:       string | null
  oilPrice:        number | null
  // diagnostics
  missingEnvVars:  string[]      // required vars not set in this environment
  cronNote:        string | null // Vercel plan / cron caveat
}

type LatestIntelRow = { created_at: string | null }

export async function GET(_req: NextRequest) {
  try {
  const supabase    = await createServerClient()
  const conflictDay = getConflictDay()

  const [
    ingestSnaps,
    intelCount,
    heraldCount,
    latestIntel,
  ] = await Promise.allSettled([
    // Last 5 ingest + batch snapshots
    (supabase as any)
      .from('model_snapshots')
      .select('id, conflict_day, herald_summary, oracle_payload, created_at')
      .order('created_at', { ascending: false })
      .limit(25),

    // Total intel rows
    (supabase as any)
      .from('intel')
      .select('count', { count: 'exact', head: true }),

    // HERALD-3 authored
    (supabase as any)
      .from('intel')
      .select('count', { count: 'exact', head: true })
      .eq('author', 'HERALD-3'),

    // Latest intel write timestamp
    (supabase as any)
      .from('intel')
      .select('created_at')
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle(),
  ])

  // ---------------------------------------------------------------------------
  // Parse snapshots
  // ---------------------------------------------------------------------------
  const snaps = ingestSnaps.status === 'fulfilled'
    ? ((ingestSnaps.value.data ?? []) as { herald_summary: unknown; created_at: string }[])
    : []

  // herald_summary is a Supabase JSONB column — comes back as an already-parsed object.
  // JSON.parse(object) coerces to "[object Object]" and throws, so we handle both.
  const parseHerald = (raw: unknown): { batch?: boolean } => {
    if (!raw) return {}
    if (typeof raw === 'string') { try { return JSON.parse(raw) as { batch?: boolean } } catch { return {} } }
    return raw as { batch?: boolean }
  }

  const ingestOnlySnaps = snaps.filter(s => !parseHerald(s.herald_summary).batch)
  const batchOnlySnaps  = snaps.filter(s => parseHerald(s.herald_summary).batch === true)

  const lastIngest = ingestOnlySnaps[0]?.created_at ?? null
  const lastBatch  = batchOnlySnaps[0]?.created_at  ?? null

  const now = Date.now()
  const msSinceIngest = lastIngest ? now - new Date(lastIngest).getTime() : Infinity
  const msSinceBatch  = lastBatch  ? now - new Date(lastBatch).getTime()  : Infinity

  // --------------------------------------------------------------------------
  // Oracle + Compass
  // --------------------------------------------------------------------------
  let topThreatLabel: string | null = null
  let oilPriceVal:    number | null = null
  let oracleOk = false
  let compassOk = false

  try {
    const threats = computeAllThreats(conflictDay)
    topThreatLabel = threats[0]?.label ?? null
    oracleOk = true
  } catch (e) { console.error('[platform/status] ORACLE-9 computeAllThreats error (day=%d):', conflictDay, e) }

  try {
    const cascade = computeEconomicCascade(conflictDay, 'CONTESTED')
    oilPriceVal = cascade.brentUsd ?? null
    compassOk = true
  } catch (e) { console.error('[platform/status] COMPASS computeEconomicCascade error (day=%d):', conflictDay, e) }

  // --------------------------------------------------------------------------
  // Intel counts
  // --------------------------------------------------------------------------
  const intelTotal  = intelCount.status  === 'fulfilled' ? ((intelCount.value  as { count?: number }).count ?? 0) : 0
  const intelHerald = heraldCount.status === 'fulfilled' ? ((heraldCount.value as { count?: number }).count ?? 0) : 0
  const latestIntelAt = latestIntel.status === 'fulfilled'
    ? (((latestIntel.value as { data?: LatestIntelRow | null }).data?.created_at) ?? null)
    : null

  // --------------------------------------------------------------------------
  // News pipeline — derive status from intel DB recency rather than an inline
  // /api/news fetch (which needs 30s but platform/status only allowed it 8s).
  // --------------------------------------------------------------------------
  const msSinceIntel = latestIntelAt ? Date.now() - new Date(latestIntelAt).getTime() : Infinity
  const newsItems    = intelTotal  // non-zero = pipeline has run

  // --------------------------------------------------------------------------
  // Build system statuses
  // --------------------------------------------------------------------------
  const systems: SystemStatus[] = [
    {
      name:     'HERALD-3 Ingest Cron',
      status:   msSinceIngest < 10 * 60_000  ? 'ONLINE'
                : msSinceIngest < 30 * 60_000 ? 'DEGRADED'
                : ingestOnlySnaps.length === 0 ? 'OFFLINE'
                : 'DEGRADED',
      lastSeen: lastIngest,
      detail:   ingestOnlySnaps.length === 0
                  ? 'Awaiting first cron run. Fires every 5 min on Vercel. Click FORCE INGEST to bootstrap.'
                  : `${ingestOnlySnaps.length} runs logged. Fires every 5 minutes.`,
      metric:   `${intelHerald} intel rows written`,
    },
    {
      name:     'NEXUS Batch Analysis',
      status:   msSinceBatch < 20 * 60_000  ? 'ONLINE'
                : msSinceBatch < 60 * 60_000 ? 'DEGRADED'
                : 'DEGRADED',  // never OFFLINE — just awaiting first cron run
      lastSeen: lastBatch,
      detail:   batchOnlySnaps.length === 0
                  ? 'Awaiting first batch run. Runs every 15 min via cron. Will activate after HERALD-3 ingests rows.'
                  : `${batchOnlySnaps.length} batch runs. Fires every 15 minutes.`,
      metric:   batchOnlySnaps.length === 0
                  ? 'Pending first run'
                  : `${batchOnlySnaps.length * 8} records re-scored (est.)`,
    },
    {
      name:    'ORACLE-9 Threat Model',
      status:   oracleOk ? 'ONLINE' : 'OFFLINE',
      lastSeen: new Date().toISOString(),
      detail:   oracleOk ? `Active. Day ${conflictDay} Bayesian threat model loaded.` : 'Engine error.',
      metric:   topThreatLabel ?? undefined,
    },
    {
      name:     'COMPASS Economic Model',
      status:   compassOk ? 'ONLINE' : 'OFFLINE',
      lastSeen: new Date().toISOString(),
      detail:   compassOk ? `Active. Real-time Brent crude cascade model running.` : 'Engine error.',
      metric:   oilPriceVal !== null ? `Brent $${oilPriceVal.toFixed(0)}/bbl` : undefined,
    },
    {
      name:     'RSS News Pipeline',
      status:   msSinceIntel < 15 * 60_000 ? 'ONLINE'
                : msSinceIntel < 60 * 60_000 ? 'DEGRADED'
                : latestIntelAt === null ? 'OFFLINE'
                : 'DEGRADED',
      lastSeen: latestIntelAt,
      detail:   msSinceIntel < 15 * 60_000
                  ? `36 feeds active. Intel last written ${Math.round(msSinceIntel / 60_000)}m ago.`
                  : msSinceIntel < 60 * 60_000
                  ? `Feeds may be rate-limited. Intel last written ${Math.round(msSinceIntel / 60_000)}m ago.`
                  : 'No intel in last hour. Cron fires every 5 min.',
      metric:   newsItems > 0 ? `${intelTotal} intel rows` : 'No data yet',
    },
    {
      name:     'Intel Database',
      status:   intelTotal > 10 ? 'ONLINE' : intelTotal > 0 ? 'DEGRADED' : 'OFFLINE',
      lastSeen: latestIntelAt,
      detail:   `${intelTotal} total intel records. ${intelHerald} HERALD-3 authored. ${intelTotal - intelHerald} seeded/manual.`,
      metric:   `${intelTotal} rows`,
    },
    {
      name:     'NEXUS-AI Engine',
      status:   AI_AVAILABLE ? 'ONLINE' : 'OFFLINE',
      lastSeen: AI_AVAILABLE ? new Date().toISOString() : null,
      detail:   AI_AVAILABLE
                  ? 'GPT-4o-mini/GPT-4o active. Enhancing CRITICAL intel summaries.'
                  : 'OPENAI_API_KEY not set. Deterministic fallback mode active.',
      metric:   AI_AVAILABLE ? 'GPT-4o / GPT-4o-mini' : 'Fallback mode',
    },
  ]

  const allOnline   = systems.every(s => s.status === 'ONLINE')
  const anyOffline  = systems.some(s  => s.status === 'OFFLINE')

  // --------------------------------------------------------------------------
  // Env-var diagnostics (server-side only — never expose secret values)
  // --------------------------------------------------------------------------
  const missingEnvVars: string[] = []
  if (!process.env.OPENAI_API_KEY)                missingEnvVars.push('OPENAI_API_KEY')
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY)     missingEnvVars.push('SUPABASE_SERVICE_ROLE_KEY')
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL)      missingEnvVars.push('NEXT_PUBLIC_SUPABASE_URL')
  if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) missingEnvVars.push('NEXT_PUBLIC_SUPABASE_ANON_KEY')
  if (!process.env.CRON_SECRET)                   missingEnvVars.push('CRON_SECRET')

  // Detect probable Vercel Hobby plan: HERALD has never run in <65 min
  const likelyHobbyThrottle =
    ingestOnlySnaps.length === 0
      ? null  // never run — can't tell yet
      : msSinceIngest > 65 * 60_000 // >65 min since last run suggests 1h throttle

  const cronNote = likelyHobbyThrottle
    ? 'Last ingest >65 min ago — Vercel Hobby plan limits crons to 1 h minimum. Upgrade to Pro for 5-min cadence.'
    : null

  // AI pipeline health assessment runs in the ingest cron (every 30 min) which
  // has real source/theater data. Calling it here on every status request burned
  // one GPT-4o-mini call per dashboard poll with hardcoded placeholder inputs.
  // Consumers that need the assessment should call /api/ingest or read the cached
  // result that the ingest cron writes to platform_config.
  return NextResponse.json({
    ok:           !anyOffline,
    conflictDay,
    generatedAt:  new Date().toISOString(),
    systems,
    intelTotal,
    intelHerald:  intelHerald,
    ingestRuns:   ingestOnlySnaps.length,
    batchRuns:    batchOnlySnaps.length,
    newsItems,
    topThreat:    topThreatLabel,
    oilPrice:     oilPriceVal,
    health:       allOnline ? 'ALL GREEN' : anyOffline ? 'DEGRADED' : 'PARTIAL',
    aiAvailable:  AI_AVAILABLE,
    aiAssessment: null,  // computed by ingest cron, not on every status poll
    missingEnvVars,
    cronNote:     cronNote ?? null,
  } satisfies PlatformStatus & { health: string; aiAvailable: boolean; aiAssessment: unknown })
  } catch (err: unknown) {
    console.error('[platform/status] unhandled error:', err instanceof Error ? err.message : String(err))
    return NextResponse.json({ ok: false, error: 'Internal server error' }, { status: 500 })
  }
}

