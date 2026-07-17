/**
 * /dashboard/world — NEXUS World Intel Dashboard
 *
 * Live 14-industry global impact analysis.
 * Fetches from /api/intel/world and renders in full dark HUD aesthetic.
 */

import { Globe, TrendingUp, TrendingDown, Minus,
         Activity, Zap, Shield, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { WorldIntelBrief, IndustryImpact } from '@/lib/ai-engine'
import { AI_AVAILABLE, generateWorldIntelBrief } from '@/lib/ai-engine'
import { computeEconomicCascade } from '@/lib/compass-engine'
import { getConflictDay } from '@/lib/conflict-day'
import { createServerClient } from '@/lib/supabase-server'

export const metadata = { title: 'World Intel — Epic Fury' }
export const revalidate = 1200   // 20 min ISR

// ── Data (call functions directly — no loopback HTTP) ─────────────────────────
async function getWorldBrief(): Promise<WorldIntelBrief> {
  const conflictDay = getConflictDay()
  const cascade     = computeEconomicCascade(conflictDay, 'CONTESTED')
  const brentUsd    = cascade.brentUsd

  // Pull live intel headlines from Supabase to feed the AI
  let topHeadlines: string[] = []
  let verifiedCount = 0
  const theaterActivity: Record<string, number> = {}
  try {
    const sb = await createServerClient()
    if (sb) {
      const { data: recentIntel } = await sb
        .from('intel')
        .select('title, theater, confidence, verified')
        .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
        .order('confidence', { ascending: false })
        .limit(40)
      if (recentIntel) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        topHeadlines  = recentIntel.filter((r: any) => r.confidence >= 65).slice(0, 10).map((r: any) => r.title)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        verifiedCount = recentIntel.filter((r: any) => r.verified).length
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        for (const row of recentIntel as any[]) {
          if (row.theater) theaterActivity[row.theater] = (theaterActivity[row.theater] ?? 0) + 1
        }
      }
    }
  } catch { /* non-fatal, proceeds with empty intel */ }

  if (AI_AVAILABLE) {
    try {
      const result = await generateWorldIntelBrief({
        conflictDay,
        topHeadlines,
        brentUsd,
        hormuzStatus: 'CONTESTED — partial closure enforced',
        verifiedCount,
        theaterActivity,
      })
      if (result) return result
    } catch { /* fall through to static */ }
  }

  // Static fallback — always renders data even without AI/DB
  return {
    generatedAt:     new Date().toISOString(),
    conflictDay,
    globalRiskScore: 82,
    macroNarrative: `Operation Epic Fury (Day ${conflictDay}) — Hormuz PARTIAL TRANSIT: ZB-α 78% cleared, 7 VLCC transits D24–D27. Brent $${brentUsd}/bbl declining on ceasefire optimism (COMPASS 68% / 72h, Abu Dhabi Framework / UNSCR 2731). G7 emergency consultations ongoing. ZULU-14 reconstituting — 6th barrage risk 41% / 72h.`,
    industries: [
      { industry: 'Energy & Oil Markets',              riskLevel: 'CRITICAL', impactScore: 95, headline: 'Hormuz PARTIAL TRANSIT: Brent $94/bbl declining on ceasefire optimism',                details: `Brent crude at $${brentUsd}/bbl declining from $132 peak. ZB-α 78% cleared — 7 VLCC transits D24–D27 under MCM escort. UNSCR 2731 ceasefire momentum reducing risk premium.`,                 keyMetric: `$${brentUsd}/bbl Brent`,            trend: 'IMPROVING', citations: ['IEA Emergency Update', 'Bloomberg Commodities'] },
      { industry: 'Nuclear & WMD Non-Proliferation',   riskLevel: 'CRITICAL', impactScore: 93, headline: 'IAEA inspectors expelled; Fordow enrichment status unknown',         details: 'Iran expelled all IAEA inspectors on Day 8. Fordow and Natanz enrichment status unverified. CTBTO seismic monitoring elevated. US strategic forces at DEFCON 3.',                          keyMetric: 'DEFCON 3 / IAEA access denied',     trend: 'WORSENING', citations: ['IAEA Emergency', 'SIPRI'] },
      { industry: 'Diplomacy & Geopolitics',           riskLevel: 'CRITICAL', impactScore: 90, headline: 'UN Security Council deadlocked; regional actors escalate',            details: 'Russia and China vetoing UNSC resolution. Arab League split on condemning Iran. Turkey mediating back-channel talks. Pakistan nuclear posture review underway.',                             keyMetric: '3rd consecutive UNSC veto',         trend: 'STABLE',    citations: ['UN Press', 'Reuters Diplomatic'] },
      { industry: 'Shipping & Logistics',              riskLevel: 'CRITICAL', impactScore: 92, headline: 'Container rerouting via Cape of Good Hope adds 14 days',              details: "Gulf-bound vessels diverting to Cape route adding $800K per voyage. Lloyd's war risk premium at 5.2%. Suez baseline traffic down 68%.",                                                  keyMetric: '+$800K/voyage rerouting cost',      trend: 'WORSENING', citations: ["Lloyd's Market", 'Freightos Baltic Index'] },
      { industry: 'Aviation & Air Transport',          riskLevel: 'CRITICAL', impactScore: 88, headline: 'Persian Gulf airspace closed; 1,200 daily flights rerouted',          details: 'UAE, Qatar, Kuwait airspace restricted. Emirates routing via Pakistan corridor. IATA estimates $3.2B/month additional fuel burn.',                                                           keyMetric: '$3.2B/month fuel surcharge',        trend: 'STABLE',    citations: ['IATA Safety', 'FlightRadar24'] },
      { industry: 'Defense & Aerospace',               riskLevel: 'HIGH',     impactScore: 85, headline: 'Allied defense orders surge; munitions stockpile strain',             details: 'Raytheon, Lockheed backorders up 380%. NATO Article 5 planning underway. Patriot PAC-3 MSE demand outstripping 18-month production capacity.',                                            keyMetric: '+380% defense backorders',          trend: 'WORSENING', citations: ['SIPRI', 'Pentagon Procurement'] },
      { industry: 'Insurance & Risk',                  riskLevel: 'HIGH',     impactScore: 80, headline: "Lloyd's war risk premium at wartime highs",                            details: 'Persian Gulf hull war risk at 5.2% — highest since 1980s tanker wars. K&R policies suspended for Gulf region. Total additional burden $2.1B/month.',                                    keyMetric: '5.2% hull war risk premium',        trend: 'WORSENING', citations: ["Lloyd's of London", 'Marsh Risk'] },
      { industry: 'Financial Markets',                 riskLevel: 'HIGH',     impactScore: 78, headline: 'VIX at 42; safe-haven flows into USD, gold, CHF',                    details: 'S&P 500 down 14% from Feb peak. Gold at $2,850/oz. 10Y Treasury yield inverted as recession fears rise. EM currencies under severe pressure.',                                          keyMetric: 'VIX 42 / Gold $2,850',             trend: 'WORSENING', citations: ['CME Group', 'Bloomberg Finance'] },
      { industry: 'Telecommunications & Cyber',        riskLevel: 'HIGH',     impactScore: 75, headline: 'Undersea cable sabotage attempts detected in Gulf',                   details: 'Three attempted cable-cutting incidents detected by sonar monitoring. Iran-linked hackers targeting US telecom exchanges. 5G supply chain review accelerated.',                             keyMetric: '3 cable sabotage attempts',         trend: 'WORSENING', citations: ['CISA', 'Submarine Cable Networks'] },
      { industry: 'Technology & Semiconductors',       riskLevel: 'HIGH',     impactScore: 72, headline: 'Cyber operations targeting critical infrastructure escalate',         details: 'APT groups linked to IRGC have targeted US power grid SCADA systems. TSMC Taiwan diversion routes under increased scrutiny.',                                                             keyMetric: '18 SCADA incidents/week',           trend: 'WORSENING', citations: ['CISA Advisory', 'CrowdStrike Intel'] },
      { industry: 'Currency & Trade',                  riskLevel: 'HIGH',     impactScore: 73, headline: 'Dollar surging; Gulf currencies under pressure despite pegs',        details: 'DXY index at 112 — 18-month high. Saudi riyal peg straining FX reserves. GCC sovereign wealth funds selling equities to support currencies.',                                              keyMetric: 'DXY 112 / SAR peg under strain',   trend: 'WORSENING', citations: ['BIS FX', 'IMF World Economic Outlook'] },
      { industry: 'Manufacturing & Supply Chain',      riskLevel: 'HIGH',     impactScore: 70, headline: 'Just-in-time manufacturing disrupted across Asia-Pacific',            details: 'Toyota halting two Japanese plants citing parts shortages. Apple diversifying away from Gulf-dependent components. Global PMI fell to 47.2 in March 2026.',                                keyMetric: 'Global PMI 47.2 (contraction)',     trend: 'WORSENING', citations: ['S&P Global PMI', 'Reuters Supply'] },
      { industry: 'Food & Agriculture',                riskLevel: 'HIGH',     impactScore: 68, headline: 'Fertilizer disruption threatens next planting season',               details: 'Iran supplies 8% of world urea. Gulf port closures delaying grain shipments to MENA. WFP warns of acute food insecurity for 12M in Yemen, Iraq.',                                         keyMetric: 'Urea +62% since Feb',              trend: 'WORSENING', citations: ['FAO Emergency', 'WFP Alert'] },
      { industry: 'Healthcare & Humanitarian',         riskLevel: 'HIGH',     impactScore: 65, headline: 'Field hospitals overwhelmed in Iran; 340K+ displaced',               details: 'US/Allied strikes on Iranian military infrastructure causing civilian displacement. ICRC access severely restricted. Medical supply chains disrupted.',                                      keyMetric: '340,000+ internally displaced',    trend: 'WORSENING', citations: ['ICRC Situation Report', 'UNHCR'] },
    ],
    topUrgent: [
      'Restore IAEA inspector access to Fordow/Natanz — nuclear status opaque',
      'Activate IEA 60-day emergency strategic petroleum reserve protocol',
      'Establish humanitarian corridor via Oman for ICRC medical access',
    ],
    accuracyNote: 'Static calibrated brief — activate OPENAI_API_KEY for live AI-generated analysis.',
  }
}

// ── Risk colour mapping ───────────────────────────────────────────────────────
const RISK_CONFIG = {
  CRITICAL: { bg: 'bg-red-950/60',    border: 'border-red-700',    text: 'text-red-300',    glow: 'glow-red',    badge: 'bg-red-900/80 text-red-200'   },
  HIGH:     { bg: 'bg-amber-950/40',  border: 'border-amber-700',  text: 'text-amber-300',  glow: 'glow-amber',  badge: 'bg-amber-900/70 text-amber-200' },
  MODERATE: { bg: 'bg-zinc-900/60',   border: 'border-zinc-700',   text: 'text-zinc-300',   glow: '',            badge: 'bg-zinc-800 text-zinc-300'      },
  LOW:      { bg: 'bg-zinc-900/40',   border: 'border-zinc-800',   text: 'text-zinc-400',   glow: '',            badge: 'bg-zinc-900 text-zinc-400'      },
} as const

// ── Industry icon map ─────────────────────────────────────────────────────────
const INDUSTRY_ICONS: Record<string, string> = {
  'Energy & Oil Markets':               '⛽',
  'Shipping & Logistics':               '🚢',
  'Financial Markets':                  '📊',
  'Defense & Aerospace':                '🛡️',
  'Technology & Semiconductors':        '💻',
  'Food & Agriculture':                 '🌾',
  'Insurance & Risk':                   '📋',
  'Diplomacy & Geopolitics':            '🌐',
  'Healthcare & Humanitarian':          '🏥',
  'Telecommunications & Cyber':         '📡',
  'Aviation & Air Transport':           '✈️',
  'Manufacturing & Supply Chain':       '🏭',
  'Currency & Trade':                   '💱',
  'Nuclear & WMD Non-Proliferation':    '☢️',
}

// ── Sub-components ────────────────────────────────────────────────────────────
function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'WORSENING') return <TrendingDown size={12} className="text-red-400" />
  if (trend === 'IMPROVING') return <TrendingUp size={12} className="text-emerald-400" />
  return <Minus size={12} className="text-zinc-500" />
}

function ScoreBar({ score, riskLevel }: { score: number; riskLevel: IndustryImpact['riskLevel'] }) {
  const color =
    riskLevel === 'CRITICAL' ? 'bg-red-500'   :
    riskLevel === 'HIGH'     ? 'bg-amber-500'  :
    riskLevel === 'MODERATE' ? 'bg-zinc-400'   : 'bg-zinc-600'
  return (
    <div className="h-1 w-full bg-zinc-800 rounded-full overflow-hidden">
      <div
        className={cn('h-full rounded-full transition-all duration-700', color)}
        style={{ width: `${score}%` }}
      />
    </div>
  )
}

function IndustryCard({ item }: { item: IndustryImpact }) {
  const cfg = RISK_CONFIG[item.riskLevel]
  const icon = INDUSTRY_ICONS[item.industry] ?? '📌'
  return (
    <div className={cn(
      'rounded border p-4 flex flex-col gap-2 transition-all hover:brightness-110',
      cfg.bg, cfg.border,
    )}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base shrink-0">{icon}</span>
          <span className="text-xs font-bold tracking-wider text-zinc-200 leading-tight truncate">
            {item.industry}
          </span>
        </div>
        <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0', cfg.badge)}>
          {item.riskLevel}
        </span>
      </div>

      {/* Score bar */}
      <div className="flex items-center gap-2">
        <ScoreBar score={item.impactScore} riskLevel={item.riskLevel} />
        <span className={cn('text-[10px] font-mono tabular-nums shrink-0', cfg.text)}>
          {item.impactScore}%
        </span>
        <TrendIcon trend={item.trend} />
      </div>

      {/* Headline */}
      <p className="text-[11px] text-zinc-300 leading-snug font-medium">{item.headline}</p>

      {/* Key metric */}
      {item.keyMetric && (
        <div className={cn('text-[10px] font-mono px-2 py-1 rounded bg-zinc-900 border', cfg.border, cfg.text)}>
          {item.keyMetric}
        </div>
      )}

      {/* Details */}
      <p className="text-[10px] text-zinc-500 leading-relaxed">{item.details}</p>

      {/* Citations */}
      {item.citations.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {item.citations.map((c, i) => (
            <span key={i} className="text-[9px] bg-zinc-900 border border-zinc-800 text-zinc-600 px-1.5 py-0.5 rounded">
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function GlobalRiskGauge({ score }: { score: number }) {
  const color =
    score >= 85 ? 'text-red-400 glow-red'    :
    score >= 65 ? 'text-amber-400 glow-amber' :
    score >= 45 ? 'text-yellow-400'           : 'text-emerald-400 glow-green'
  const label =
    score >= 85 ? 'EXTREME RISK'  :
    score >= 65 ? 'HIGH RISK'     :
    score >= 45 ? 'ELEVATED RISK' : 'GUARDED'

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={cn('text-6xl font-black tabular-nums tracking-tighter font-mono', color)}>
        {score}
      </div>
      <div className={cn('text-xs font-bold tracking-widest uppercase', color)}>{label}</div>
      <div className="text-[10px] text-zinc-600">GLOBAL RISK INDEX</div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default async function WorldPage() {
  const brief = await getWorldBrief()  // always returns data (static fallback guaranteed)

  // Sort: CRITICAL first, then by impactScore desc
  const sortedIndustries = [...brief.industries].sort((a, b) => {
        const riskOrder = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3 }
        const ro = (riskOrder[a.riskLevel] ?? 3) - (riskOrder[b.riskLevel] ?? 3)
        return ro !== 0 ? ro : b.impactScore - a.impactScore
      })

  const criticalCount  = sortedIndustries.filter(i => i.riskLevel === 'CRITICAL').length
  const highCount      = sortedIndustries.filter(i => i.riskLevel === 'HIGH').length
  const worseningCount = sortedIndustries.filter(i => i.trend === 'WORSENING').length

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-4 md:p-6 font-mono space-y-6">

      {/* ── Header ── */}
      <div className="border border-emerald-900 rounded bg-zinc-950/80 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Globe size={22} className="text-emerald-400 glow-green shrink-0" />
          <div>
            <h1 className="text-sm font-black tracking-widest text-emerald-300 glow-green uppercase">
              NEXUS World Intel — Global Impact Monitor
            </h1>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Operation Epic Fury Day {brief.conflictDay} · 14-industry deep analysis
              <span className="ml-2 text-zinc-700">·</span>
              <span className="ml-2">{new Date(brief.generatedAt).toLocaleTimeString('en-US', { hour12: false, timeZone: 'UTC' })} UTC</span>
            </p>
          </div>
        </div>

        {/* Stat pills */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-[10px] bg-red-950 border border-red-800 text-red-300 px-2 py-1 rounded">
            {criticalCount} CRITICAL
          </span>
          <span className="text-[10px] bg-amber-950 border border-amber-800 text-amber-300 px-2 py-1 rounded">
            {highCount} HIGH
          </span>
          <span className="text-[10px] bg-zinc-900 border border-zinc-700 text-zinc-400 px-2 py-1 rounded">
            {worseningCount} WORSENING
          </span>

        </div>
      </div>

      <>
          {/* ── Risk Score + Macro ── */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Global risk gauge */}
            <div className="border border-zinc-800 rounded bg-zinc-900/60 p-6 flex items-center justify-center">
              <GlobalRiskGauge score={brief.globalRiskScore} />
            </div>

            {/* Macro narrative */}
            <div className="md:col-span-2 border border-zinc-800 rounded bg-zinc-900/40 p-4 flex flex-col gap-3">
              <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-widest">
                <Activity size={11} /> MACRO SITUATION ASSESSMENT
              </div>
              <p className="text-sm text-zinc-200 leading-relaxed">{brief.macroNarrative}</p>

              {/* Top urgent actions */}
              {brief.topUrgent.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  <div className="text-[10px] text-zinc-600 uppercase tracking-wider">Urgent Actions Required</div>
                  {brief.topUrgent.map((action, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <ChevronRight size={11} className="text-amber-500 shrink-0 mt-0.5" />
                      <span className="text-[11px] text-amber-200">{action}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Industry Grid ── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Shield size={13} className="text-emerald-500" />
              <span className="text-[11px] text-zinc-500 uppercase tracking-widest">
                14-Industry Global Impact Analysis
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {sortedIndustries.map((item) => (
                <IndustryCard key={item.industry} item={item} />
              ))}
            </div>
          </div>

          {/* ── AI Accuracy note ── */}
          {brief.accuracyNote && (
            <div className="border border-zinc-800 rounded bg-zinc-900/30 p-3 flex items-start gap-2">
              <Zap size={11} className="text-zinc-600 shrink-0 mt-0.5" />
              <span className="text-[10px] text-zinc-600">{brief.accuracyNote}</span>
            </div>
          )}
      </>
    </div>
  )
}
