/**
 * GET /api/oracle/enhance
 *
 * AI-enhanced threat probability layer — runs ORACLE-9 Bayesian model, then
 * feeds the results + latest high-confidence intel headlines into GPT-4o-mini
 * to produce AI-adjusted probability overlays.
 *
 * When AI is unavailable, returns raw ORACLE-9 Bayesian output unchanged.
 *
 * ISR: 300s (5 min).  Also called by Vercel Cron every 15 min.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient }        from '@/lib/supabase-server'
import { computeAllThreats }         from '@/lib/oracle-engine'
import { getConflictDay }            from '@/lib/conflict-day'
import { AI_AVAILABLE, generateThreatAssessment } from '@/lib/ai-engine'
import { requireSubscriber, requireCronAuth } from '@/lib/api-auth'

/* eslint-disable @typescript-eslint/no-explicit-any */

export const runtime     = 'nodejs'
export const revalidate  = 300   // 5-minute ISR cache
export const maxDuration = 60    // GPT-4o-mini threat assessment overlay

export async function GET(req: NextRequest) {
  // Vercel cron calls have no session — bypass subscriber gate
  const cronDeny = requireCronAuth(req)
  if (cronDeny !== null) {
    // Not a cron call — require subscriber session
    const deny = await requireSubscriber(req)
    if (deny) return deny
  }

  try {
    const conflictDay = getConflictDay()
    const basThreats  = computeAllThreats(conflictDay)

    // ── Fetch recent high-confidence intel headlines ──────────────────────
    let recentHeadlines: string[] = []
    let activeTheaters:  string[] = []

    try {
      const supabase = await createServerClient()
      const since = new Date(Date.now() - 45 * 60 * 1000).toISOString()

      const { data } = await (supabase as any)
        .from('intel')
        .select('title, theater, confidence, verified')
        .gte('created_at', since)
        .gte('confidence', 65)
        .order('confidence', { ascending: false })
        .limit(20)

      recentHeadlines = (data ?? []).map((r: any) => r.title as string).filter(Boolean)
      activeTheaters  = ([...new Set((data ?? []).map((r: any) => String(r.theater)))] as string[]).filter(Boolean)
    } catch {
      // Supabase unavailable — proceed with base threats, no AI headlines
    }

    // ── AI overlay ─────────────────────────────────────────────────────────
    let overlays: Awaited<ReturnType<typeof generateThreatAssessment>> = null

    if (AI_AVAILABLE && recentHeadlines.length > 0) {
      overlays = await generateThreatAssessment({
        threats: basThreats.map(t => ({
          id:          t.id,
          label:       t.label,
          domain:      t.domain,
          probability: Math.round(t.probability * 100),
          windowHours: t.windowHours,
        })),
        recentHeadlines,
        conflictDay,
        activeTheaters,
      })
    }

    // ── Merge: overlay AI adjustment onto Bayesian base if available ───────
    const overlayMap = new Map((overlays ?? []).map(o => [o.threatId, o]))

    const enhanced = basThreats.map(t => {
      const ov = overlayMap.get(t.id)
      return {
        ...t,
        // Bayesian probability (0-1 from engine)
        probability: t.probability,
        // AI-enhanced probability (0-100); null if AI unavailable
        aiProbability:    ov ? ov.aiProbabilityAdj / 100 : null,
        aiConfidence:     ov?.aiConfidence   ?? null,
        aiKeySignal:      ov?.keySignal      ?? null,
        aiReasoning:      ov?.reasoning      ?? null,
        aiTrend:          ov?.trend          ?? null,
      }
    })

    return NextResponse.json(
      {
        ok:           true,
        conflictDay,
        generatedAt:  new Date().toISOString(),
        modelVersion: 'ORACLE-9.3+AI',
        aiAvailable:  AI_AVAILABLE && recentHeadlines.length > 0,
        threats:      enhanced,
        intelWindow:  recentHeadlines.length,
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
        },
      },
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Oracle enhance error'
    return NextResponse.json({ ok: false, error: message, threats: [] }, { status: 500 })
  }
}
