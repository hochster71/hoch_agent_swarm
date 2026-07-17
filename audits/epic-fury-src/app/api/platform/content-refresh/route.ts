/**
 * GET /api/platform/content-refresh
 *
 * Autonomous content freshness cron. Runs every 6 hours to ensure all
 * dashboard fallback content stays current as CONFLICT_DAY advances.
 *
 * Actions performed:
 * 1. Probes all content sources and computes freshness status
 * 2. Triggers newsroom script regeneration if stale (> 6h or wrong day)
 * 3. Triggers digest refresh if stale (> 30min)
 * 4. Logs freshness report to platform_config for monitoring
 *
 * Schedule: every 6 hours (see vercel.json)
 */

import { NextRequest, NextResponse } from 'next/server'
import { getConflictDay, toDTG } from '@/lib/conflict-day'
import { buildFreshnessReport } from '@/lib/freshness-engine'
import { requireCronAuth } from '@/lib/api-auth'
import { logAgentRun } from '@/lib/agent-run-logger'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0
export const maxDuration = 60

export async function GET(req: NextRequest) {
  const startedAtIso = new Date().toISOString()
  const startedAtMs = Date.now()
  const deny = requireCronAuth(req)
  if (deny) {
    void logAgentRun({
      agentName: 'CONTENT_REFRESH',
      route: '/api/platform/content-refresh',
      trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
      status: 'FAILED',
      errorMessage: 'Unauthorized',
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return deny
  }

  const day = getConflictDay()
  const cronSecret = process.env.CRON_SECRET?.trim() ?? ''

  // ── 1. Probe content sources ──────────────────────────────────────────────

  const probes: Record<string, { lastUpdatedAt: string | number | null; authoredDay?: number }> = {}

  // Probe platform status (for ingest freshness)
  try {
    const base = req.nextUrl.origin || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
    const statusRes = await fetch(`${base}/api/platform/status`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })
    if (statusRes.ok) {
      const status = await statusRes.json()
      probes.ingest = { lastUpdatedAt: status.generatedAt, authoredDay: status.conflictDay }
    }
  } catch { /* skip */ }

  // Probe intel digest
  try {
    const base = req.nextUrl.origin || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
    const digestRes = await fetch(`${base}/api/intel/digest`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(12_000),
    })
    if (digestRes.ok) {
      const digest = await digestRes.json()
      probes.digest = { lastUpdatedAt: digest.generatedAt, authoredDay: digest.conflictDay }
    }
  } catch { /* skip */ }

  // Probe newsroom freshness (check if scripts exist for current day)
  let newsroomStale = false
  try {
    const base = req.nextUrl.origin || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
    const newsRes = await fetch(`${base}/api/newsroom/generate`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })
    if (newsRes.ok) {
      const newsData = await newsRes.json()
      probes.newsroom = {
        lastUpdatedAt: newsData.generatedAt ?? newsData.cachedAt ?? null,
        authoredDay: newsData.conflictDay ?? undefined,
      }
      // Mark stale if scripts are for wrong day or > 6h old
      if (newsData.conflictDay !== day) newsroomStale = true
    } else {
      newsroomStale = true
    }
  } catch {
    newsroomStale = true
  }

  // ── 2. Build freshness report ─────────────────────────────────────────────

  const report = buildFreshnessReport(probes)

  // ── 3. Trigger regeneration for stale content ─────────────────────────────

  const actions: string[] = []

  // Regenerate newsroom scripts if stale or wrong day
  if (newsroomStale || report.contentTypes.newsroom?.level === 'STALE') {
    try {
      const base = req.nextUrl.origin || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
      const regen = await fetch(`${base}/api/newsroom/generate`, {
        method: 'POST',
        cache: 'no-store',
        signal: AbortSignal.timeout(30_000),
        headers: {
          'content-type': 'application/json',
          ...(cronSecret ? { authorization: `Bearer ${cronSecret}` } : {}),
        },
        body: JSON.stringify({ force: true, conflictDay: day }),
      })
      if (regen.ok) {
        actions.push(`Newsroom scripts regenerated for Day ${day}`)
      } else {
        actions.push(`Newsroom regeneration failed: ${regen.status}`)
      }
    } catch (err) {
      actions.push(`Newsroom regeneration error: ${err instanceof Error ? err.message : 'unknown'}`)
    }
  } else {
    actions.push('Newsroom scripts current — no regeneration needed')
  }

  // Trigger digest refresh if stale
  if (report.contentTypes.digest?.level === 'STALE') {
    try {
      const base = req.nextUrl.origin || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
      await fetch(`${base}/api/intel/digest`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(15_000),
      })
      actions.push('Intel digest refreshed')
    } catch {
      actions.push('Intel digest refresh failed')
    }
  }

  // ── 4. Persist freshness report for monitoring ────────────────────────────

  try {
    const { createClient } = await import('@supabase/supabase-js')
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY
    if (url && key) {
      const sb = createClient(url, key)
      await sb.from('platform_config').upsert({
        key: 'content_freshness_report',
        value: JSON.stringify({
          ...report,
          actions,
          lastRunAt: new Date().toISOString(),
          dtg: toDTG(day),
        }),
        updated_at: new Date().toISOString(),
      }, { onConflict: 'key' })
    }
  } catch { /* non-critical — report persistence is best-effort */ }

  // ── 5. Response ───────────────────────────────────────────────────────────

  void logAgentRun({
    agentName: 'CONTENT_REFRESH',
    route: '/api/platform/content-refresh',
    trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
    status: 'SUCCESS',
    conflictDay: day,
    durationMs: Date.now() - startedAtMs,
    detail: {
      actions,
      freshnessSummary: {
        overall: report.overallLevel,
        staleCount: report.staleCount,
      },
    },
    startedAt: startedAtIso,
    finishedAt: new Date().toISOString(),
  })

  return NextResponse.json({
    ok: true,
    conflictDay: day,
    dtg: toDTG(day),
    runAt: new Date().toISOString(),
    freshnessReport: report,
    actions,
    nextRunIn: '6h',
  }, {
    headers: { 'Cache-Control': 'no-store' },
  })
}
