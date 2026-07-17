/**
 * GET /api/intel/forecast
 *
 * NEXUS-FORECAST — AI-generated 24h / 72h / 30-day conflict trajectory.
 *
 * Uses:
 *  - ORACLE-9 top threats (Bayesian probabilities)
 *  - Last 24h key developments from Supabase
 *  - COMPASS economic cascade metrics
 *  - GPT-4o for strategic synthesis
 *
 * ISR: 900s (15 min).  Also called by Vercel Cron every 30 min.
 * Static fallback guaranteed — never returns error body.
 */

import { NextRequest, NextResponse } from 'next/server'
import { requireSubscriber, requireCronAuth } from '@/lib/api-auth'
import { createServerClient }        from '@/lib/supabase-server'
import { computeAllThreats }      from '@/lib/oracle-engine'
import { computeEconomicCascade } from '@/lib/compass-engine'
import { getConflictDay }         from '@/lib/conflict-day'
import { getWarStats }            from '@/lib/war-stats'
import { AI_AVAILABLE, generateConflictForecast } from '@/lib/ai-engine'
import type { ConflictForecast }  from '@/lib/ai-engine'

/* eslint-disable @typescript-eslint/no-explicit-any */

export const runtime     = 'nodejs'
export const revalidate  = 900   // 15-minute ISR cache
export const maxDuration = 120   // GPT-4o strategic forecast synthesis

// ── Static fallback ──────────────────────────────────────────────────────────
// Shown only when OPENAI_API_KEY is absent. Uses actual conflictDay so the
// day reference is never stale. Content is deliberately generic — no
// hardcoded battle events that become fiction as the conflict evolves.
function staticForecast(conflictDay: number, brentUsd: number): ConflictForecast {
  const ws = getWarStats(conflictDay)
  return {
    generatedAt:   new Date().toISOString(),
    conflictDay,
    window24h: {
      summary:     `Day ${conflictDay + 1} outlook (AI offline — static model): ORACLE-9 Bayesian threat matrix active. COMPASS economic cascade: Brent ~$${Math.round(brentUsd)}/bbl. CENTCOM operational posture maintained. Enable OPENAI_API_KEY for live AI synthesis.`,
      keyRisk:     'AI synthesis offline — threat probabilities derived from ORACLE-9 static model only. Live corroboration unavailable.',
      probability: 35,
    },
    window72h: {
      summary:     `72-hour window (Day ${conflictDay} static model): Conflict trajectory extrapolated from ORACLE-9 Bayesian priors. Diplomatic and escalation signals require live intel synthesis for accurate assessment.`,
      keyRisk:     'AI engine offline — enable OPENAI_API_KEY for real-time strategic forecast synthesis.',
      probability: 50,
    },
    ceasefire30d:     ws.compassCeasefire,
    escalation30d:    Math.max(5, 100 - ws.compassCeasefire - 10),
    keyUncertainties: [
      'AI forecast engine offline — set OPENAI_API_KEY in Vercel environment variables to activate',
      'Theater escalation dynamics require live AI synthesis for calibrated probability estimates',
      'Economic pressure trajectory depends on Hormuz transit status — live data feed required',
    ],
    modelConfidence: 'LOW',
  }
}

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
    const cascade     = computeEconomicCascade(conflictDay, 'CONTESTED')
    const brentUsd    = cascade.brentUsd
    const threats     = computeAllThreats(conflictDay)

    // ── Fetch key developments (verified, last 24h) ───────────────────────
    let keyDevelopments: string[] = []

    try {
      const supabase = await createServerClient()
      const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()

      const { data } = await (supabase as any)
        .from('intel')
        .select('title, theater, confidence, verified')
        .gte('created_at', since)
        .gte('confidence', 70)
        .order('verified',   { ascending: false })
        .order('confidence', { ascending: false })
        .limit(8)

      keyDevelopments = (data ?? []).map((r: any) => r.title as string).filter(Boolean)
    } catch {
      // Supabase unavailable — AI will work from ORACLE data only
    }

    // ── AI forecast ────────────────────────────────────────────────────────
    let forecast: ConflictForecast | null = null

    if (AI_AVAILABLE) {
      forecast = await generateConflictForecast({
        conflictDay,
        topThreats: threats
          .sort((a, b) => b.probability - a.probability)
          .slice(0, 5)
          .map(t => ({
            label:       t.label,
            probability: Math.round(t.probability * 100),
            domain:      t.domain,
          })),
        keyDevelopments,
        brentUsd,
        hormuzStatus: 'CONTESTED — partial closure enforced, MCM corridor ZB-Alpha 51% cleared',
        verifiedCount: keyDevelopments.length,
      })
    }

    const result = forecast ?? staticForecast(conflictDay, brentUsd)

    return NextResponse.json(
      {
        ok:          true,
        aiGenerated: !!forecast,
        forecast:    result,
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=900, stale-while-revalidate=1800',
        },
      },
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Forecast error'
    console.error('[/api/intel/forecast]', message)

    const conflictDay = getConflictDay()
    return NextResponse.json(
      { ok: false, aiGenerated: false, forecast: staticForecast(conflictDay, 118) },
      { status: 200 },
    )
  }
}
