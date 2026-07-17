/**
 * GET /api/intel/world
 *
 * NEXUS World Intelligence Brief — called by cron every 20 minutes.
 * Also callable manually.
 *
 * Produces a deep multi-industry global impact analysis using GPT-4o.
 * Covers all 14 world industries affected by Operation Epic Fury.
 *
 * The result is:
 *   1. Returned as JSON for the dashboard
 *   2. Written as a model_snapshot row for historical tracking
 *
 * Auth: Bearer CRON_SECRET (omit in dev)
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'
import { getConflictDay }            from '@/lib/conflict-day'
import { computeEconomicCascade }    from '@/lib/compass-engine'
import {
  AI_AVAILABLE,
  generateWorldIntelBrief,
  WorldIntelBrief,
} from '@/lib/ai-engine'

export const runtime    = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 120  // GPT-4o synthesis across 14 industries

function getServiceClient() {
  const url    = process.env.NEXT_PUBLIC_SUPABASE_URL
  const svcKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !svcKey) return null
  return createClient<any>(url, svcKey, { auth: { persistSession: false } })
}

// In-process brief cache — prevents redundant GPT-4o calls within same Lambda instance
let _worldBriefCache:    WorldIntelBrief | null = null
let _worldBriefCacheAge  = 0
const WORLD_BRIEF_TTL_MS = 20 * 60_000  // match CDN s-maxage

// Per-IP rate limiter — max 15 GET requests/min to block cost-drain DoS
const _worldIpLimiter = new Map<string, { count: number; resetAt: number }>()

// Fallback static brief when AI is unavailable
function staticWorldBrief(conflictDay: number, brentUsd: number): WorldIntelBrief {
  return {
    generatedAt:     new Date().toISOString(),
    conflictDay,
    globalRiskScore: 82,
    macroNarrative: `Operation Epic Fury (Day ${conflictDay}) — Hormuz PARTIAL TRANSIT: ZB-α 78% cleared, 7 VLCC transits D24–D27. Brent $${brentUsd}/bbl declining on ceasefire optimism (COMPASS 68% / 72h, Abu Dhabi Framework / UNSCR 2731). G7 emergency consultations ongoing. ZULU-14 reconstituting — 6th barrage risk 41% / 72h.`,
    industries: [
      { industry: 'Energy & Oil Markets',              riskLevel: 'CRITICAL', impactScore: 95, headline: 'Hormuz PARTIAL TRANSIT: Brent $94/bbl declining on ceasefire optimism', details: `Brent crude at $${brentUsd}/bbl declining from $132 peak. ZB-α 78% cleared — 7 VLCC transits D24–D27 under MCM escort. UNSCR 2731 ceasefire momentum reducing risk premium. Emergency SPR releases ongoing.`, keyMetric: `$${brentUsd}/bbl Brent`, trend: 'IMPROVING', citations: ['IEA Emergency Update', 'Bloomberg Commodities'] },
      { industry: 'Shipping & Logistics',              riskLevel: 'CRITICAL', impactScore: 92, headline: 'Container rerouting via Cape of Good Hope adds 14 days', details: 'Gulf-bound vessels diverting to Cape route adding $800K per voyage. Lloyd\'s war risk premium at 5.2% of hull value. Suez baseline traffic down 68%.', keyMetric: '+$800K/voyage rerouting cost', trend: 'WORSENING', citations: ["Lloyd's Market", 'Freightos Baltic Index'] },
      { industry: 'Financial Markets',                 riskLevel: 'HIGH',     impactScore: 78, headline: 'VIX at 42; safe-haven flows into USD, gold, CHF', details: 'S&P 500 down 14% from Feb peak. Gold at $2,850/oz. 10Y Treasury yield inverted as recession fears rise. Emerging market currencies under severe pressure.', keyMetric: 'VIX 42 / Gold $2,850', trend: 'WORSENING', citations: ['CME Group', 'Bloomberg Finance'] },
      { industry: 'Defense & Aerospace',               riskLevel: 'HIGH',     impactScore: 85, headline: 'Allied defense orders surge; munitions stockpile strain', details: 'Raytheon, Lockheed backorders up 380%. NATO Article 5 planning underway for escalation scenarios. Patriot PAC-3 MSE demand outstripping 18-month production capacity.', keyMetric: '+380% defense backorders', trend: 'WORSENING', citations: ['SIPRI', 'Pentagon Procurement'] },
      { industry: 'Technology & Semiconductors',       riskLevel: 'HIGH',     impactScore: 72, headline: 'Cyber operations targeting critical infrastructure escalate', details: 'APT groups linked to IRGC have targeted US power grid SCADA systems. TSMC Taiwan diversion routes under increased scrutiny. Starlink providing critical comms continuity.', keyMetric: '18 SCADA incidents/week', trend: 'WORSENING', citations: ['CISA Advisory', 'CrowdStrike Intel'] },
      { industry: 'Food & Agriculture',                riskLevel: 'HIGH',     impactScore: 68, headline: 'Fertilizer disruption threatens next planting season', details: 'Iran supplies 8% of world urea. Gulf port closures delaying grain shipments to MENA. WFP warns of acute food insecurity for 12M people in Yemen, Iraq.', keyMetric: 'Urea +62% since Feb', trend: 'WORSENING', citations: ['FAO Emergency', 'WFP Alert'] },
      { industry: 'Insurance & Risk',                  riskLevel: 'HIGH',     impactScore: 80, headline: "Lloyd's war risk premium at wartime highs", details: 'Persian Gulf hull war risk at 5.2% — highest since 1980s tanker wars. Kidnap & ransom policies suspended for Gulf region. Total additional insurance burden $2.1B/month.', keyMetric: '5.2% hull war risk premium', trend: 'WORSENING', citations: ["Lloyd's of London", 'Marsh Risk'] },
      { industry: 'Diplomacy & Geopolitics',           riskLevel: 'CRITICAL', impactScore: 90, headline: 'UN Security Council deadlocked; regional actors escalate', details: 'Russia and China vetoing UNSC resolution. Arab League split on condemning Iran. Turkey mediating back-channel talks. Pakistan nuclear posture review underway.', keyMetric: '3rd consecutive UNSC veto', trend: 'STABLE', citations: ['UN Press', 'Reuters Diplomatic'] },
      { industry: 'Healthcare & Humanitarian',         riskLevel: 'HIGH',     impactScore: 65, headline: 'Field hospitals overwhelmed in Iran; 340K+ displaced', details: 'US/Allied strikes on Iranian military infrastructure causing civilian displacement. ICRC access severely restricted. Medical supply chains disrupted by port closures.', keyMetric: '340,000+ internally displaced', trend: 'WORSENING', citations: ['ICRC Situation Report', 'UNHCR'] },
      { industry: 'Telecommunications & Cyber',        riskLevel: 'HIGH',     impactScore: 75, headline: 'Undersea cable sabotage attempts detected in Gulf', details: 'Three attempted cable-cutting incidents in Persian Gulf detected by sonar monitoring. Iran-linked hackers targeting US telecom exchanges. 5G supply chain review accelerated.', keyMetric: '3 cable sabotage attempts', trend: 'WORSENING', citations: ['CISA', 'Submarine Cable Networks'] },
      { industry: 'Aviation & Air Transport',          riskLevel: 'CRITICAL', impactScore: 88, headline: 'Persian Gulf airspace closed; 1,200 daily flights rerouted', details: 'UAE, Qatar, Kuwait airspace restricted. Emirates routing via Pakistan corridor. IATA estimates $3.2B/month additional fuel burn. 1,200 daily flights affected.', keyMetric: '$3.2B/month fuel surcharge', trend: 'STABLE', citations: ['IATA Safety', 'FlightRadar24'] },
      { industry: 'Manufacturing & Supply Chain',      riskLevel: 'HIGH',     impactScore: 70, headline: 'Just-in-time manufacturing disrupted across Asia-Pacific', details: 'Toyota halting two Japanese plants citing parts shortages from Gulf region. Apple diversifying away from Gulf-dependent components. Global PMI fell to 47.2 in March 2026.', keyMetric: 'Global PMI 47.2 (contraction)', trend: 'WORSENING', citations: ['S&P Global PMI', 'Reuters Supply'] },
      { industry: 'Currency & Trade',                  riskLevel: 'HIGH',     impactScore: 73, headline: 'Dollar surging; Gulf currencies under pressure despite pegs', details: 'DXY index at 112 — 18-month high. Saudi riyal peg straining FX reserves. GCC sovereign wealth funds selling equities to support currencies. Yuan-oil settlement gaining traction.', keyMetric: 'DXY 112 / SAR peg under strain', trend: 'WORSENING', citations: ['BIS FX', 'IMF World Economic Outlook'] },
      { industry: 'Nuclear & WMD Non-Proliferation',   riskLevel: 'CRITICAL', impactScore: 93, headline: 'IAEA inspectors expelled; Fordow enrichment status unknown', details: 'Iran expelled all IAEA inspectors on Day 8. Fordow and Natanz enrichment status unverified since March 8. CTBTO seismic monitoring elevated. US strategic forces at DEFCON 3.', keyMetric: 'DEFCON 3 / IAEA access denied', trend: 'WORSENING', citations: ['IAEA Emergency', 'US NRC', 'SIPRI'] },
    ],
    topUrgent: [
      'Restore IAEA inspector access to Fordow/Natanz immediately — nuclear status opaque',
      'Activate emergency strategic petroleum reserves coordination (IEA 60-day protocol)',
      'Establish humanitarian corridor via Oman for ICRC medical access to conflict zones',
    ],
    accuracyNote: 'Static fallback — AI unavailable. Scores are Day-22 calibrated estimates. Activate OPENAI_API_KEY for live analysis.',
  }
}

export async function GET(req: NextRequest) {
  // Rate limit: max 15 requests/min per IP — prevents GPT-4o cost-drain DoS
  const ip  = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? 'unknown'
  const now = Date.now()
  const rl  = _worldIpLimiter.get(ip) ?? { count: 0, resetAt: now + 60_000 }
  if (now > rl.resetAt) { rl.count = 0; rl.resetAt = now + 60_000 }
  rl.count++
  _worldIpLimiter.set(ip, rl)
  if (rl.count > 15) {
    return NextResponse.json({ error: 'Rate limited' }, { status: 429, headers: { 'Retry-After': '60' } })
  }

  // Serve from in-process cache if fresh (< 20 min) — avoids duplicate AI calls within same instance
  if (_worldBriefCache && now - _worldBriefCacheAge < WORLD_BRIEF_TTL_MS) {
    return NextResponse.json(_worldBriefCache, {
      headers: { 'Cache-Control': 'public, s-maxage=1200, stale-while-revalidate=600' },
    })
  }

  // World intel is public-read — no auth required for GET.
  try {
    return await buildWorldBrief()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('[world] unhandled error:', msg)
    const conflictDay = getConflictDay()
    const cascade     = computeEconomicCascade(conflictDay, 'CONTESTED')
    return NextResponse.json(staticWorldBrief(conflictDay, cascade.brentUsd), {
      headers: { 'Cache-Control': 'no-store' },
    })
  }
}

async function buildWorldBrief() {
  const conflictDay = getConflictDay()
  const supabase    = getServiceClient()

  // Pull recent high-confidence intel headlines
  let topHeadlines: string[] = []
  let verifiedCount = 0
  const theaterActivity: Record<string, number> = {}

  if (supabase) {
    const { data: recentIntel } = await supabase
      .from('intel')
      .select('title, theater, confidence, verified')
      .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
      .order('confidence', { ascending: false })
      .limit(40)

    if (recentIntel) {
      topHeadlines  = recentIntel.filter((r: any) => r.confidence >= 65).slice(0, 10).map((r: any) => r.title)
      verifiedCount = recentIntel.filter((r: any) => r.verified).length
      for (const row of recentIntel as any[]) {
        if (row.theater) theaterActivity[row.theater] = (theaterActivity[row.theater] ?? 0) + 1
      }
    }
  }

  // Get economic data
  const cascade = computeEconomicCascade(conflictDay, 'CONTESTED')
  const brentUsd = cascade.brentUsd

  let brief: WorldIntelBrief

  if (AI_AVAILABLE) {
    const result = await generateWorldIntelBrief({
      conflictDay,
      topHeadlines,
      brentUsd,
      hormuzStatus: 'CONTESTED — partial closure enforced',
      verifiedCount,
      theaterActivity,
    })
    brief = result ?? staticWorldBrief(conflictDay, brentUsd)
  } else {
    brief = staticWorldBrief(conflictDay, brentUsd)
  }

  // Persist to model_snapshots for historical trending
  if (supabase) {
    await supabase.from('model_snapshots').insert({
      conflict_day:    conflictDay,
      oracle_payload:  { worldBrief: true, globalRiskScore: brief.globalRiskScore } as any,
      compass_payload: { worldIntelBrief: brief } as any,
      herald_summary:  {
        type:    'world_intel',
        industries: brief.industries.length,
        globalRiskScore: brief.globalRiskScore,
        aiGenerated: AI_AVAILABLE,
      },
    })
  }

  _worldBriefCache    = brief
  _worldBriefCacheAge = Date.now()
  return NextResponse.json(brief, {
    headers: {
      'Cache-Control': 'public, s-maxage=1200, stale-while-revalidate=600',
    },
  })
} // end buildWorldBrief
