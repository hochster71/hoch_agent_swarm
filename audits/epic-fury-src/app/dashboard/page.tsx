import { createServerClient } from '@/lib/supabase-server'
import { IntelCard } from '@/components/IntelCard'
import { ThreatMeter } from '@/components/ThreatMeter'
import { NewsTicker } from '@/components/NewsTicker'
import type { TickerItem } from '@/components/NewsTicker'
import { STATIC_INTEL } from '@/lib/static-intel'
import { OraclePanel } from '@/components/OraclePanel'
import { HeraldFeed } from '@/components/HeraldFeed'
import { PlatformHealth } from '@/components/PlatformHealth'
import { IntelStatsBanner } from '@/components/IntelStatsBanner'
import GovernorPanel from '@/components/GovernorPanel'
import RevenuePanel from '@/components/RevenuePanel'
import DebatePanel from '@/components/DebatePanel'
import WorkflowPanel from '@/components/WorkflowPanel'
import ForesightPanel    from '@/components/ForesightPanel'
import AutonomousPanel  from '@/components/AutonomousPanel'
import SynthesisPanel   from '@/components/SynthesisPanel'
import { NexusDoctrinePanel } from '@/components/NexusDoctrinePanel'
import { ProvenancePulsePanel } from '@/components/ProvenancePulsePanel'
import { BmdBattlePanel } from '@/components/BmdBattlePanel'
import { AccessGate } from '@/components/AccessGate'
import Link from 'next/link'
import {
  FileText,
  Target,
  Clock,
  Activity,
  Newspaper,
  Cpu,
  Map,
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  Globe,
  Globe2,
  BarChart3,
  ShieldAlert,
  Home,
  Skull,
  Scale,
  Satellite,
  Package,
} from 'lucide-react'
import type { Intel } from '@/lib/types'

import { getConflictDay, CONFLICT_EPOCH } from '@/lib/conflict-day'
import { getWarStats } from '@/lib/war-stats'

export const revalidate = 0

function buildTickerItems(): TickerItem[] {
  const ws = getWarStats()
  const d = ws.day
  return [
  { id: 't1',  label: 'BREAKING',  text: `CEASEFIRE TRIAL EXTENDED 48H — POTUS DAY ${d}: all theaters confirmed silent — Iran fully compliant — armistice negotiations begin`, urgent: true },
  { id: 't2',  label: 'CENTCOM',   text: `${ws.sortiesLabel} coalition combat sorties total — all offensive operations paused under ceasefire protocol OPORD 2026-43 — DEFCON 3 maintained` },
  { id: 't3',  label: 'ORACLE-9',  text: `6th barrage risk: ≤2% — ZULU-14 TEL destroyed D38 pre-launch by B-1B strike — Iran BM inventory combat-exhausted at ~${ws.bmStockPct}% — model locked Day ${d}` },
  { id: 't4',  label: 'BREAKING',  text: `Strait of Hormuz 100% OPEN — ZB-Alpha MCM mission COMPLETE Day ${d} — first fully unrestricted VLCC transit D43 — 47 vessels staged`, urgent: true },
  { id: 't5',  label: 'NAVCENT',   text: `ZB-Alpha MCM mission COMPLETE D${d} — Hormuz 100% cleared — unrestricted commercial transit restored — USS Chief & USS Gladiator released from MCM tasking` },
  { id: 't6',  label: 'CERBERUS',  text: `APT34 offensive operations CEASED since ceasefire trial 06:00Z D43 — no new hostile cyber activity detected — watch state reduced to ELEVATED` },
  { id: 't7',  label: 'IAEA',      text: `IAEA inspectors at Natanz FEP D41 — Day 3 report: centrifuge halls A-D confirmed inoperative — nuclear infrastructure ${ws.nuclearDegradedPct}% degraded — radiological status GREEN` },
  { id: 't8',  label: 'BREAKING',  text: `CEASEFIRE: Iran formal declaration D42 — effective 06:00Z D43 — POTUS extends 48h D${d} — COMPASS ${ws.compassCeasefire}% confidence — all parties compliant`, urgent: true },
  { id: 't9',  label: 'UNSC',      text: `UNSCR 2732 passed 15-0 UNANIMOUS D40 — first UNSC unanimity on Iran conflict — Abu Dhabi Ceasefire Framework legally endorsed — IAEA access mandatory` },
  { id: 't10', label: 'IAEA',      text: `DG Grossi: "Iran enrichment capability as of D${d} is effectively zero" — Fordow inspection team staged in Muscat — entry expected D45` },
  { id: 't11', label: 'NEXUS',     text: `All-domain COP D${d}: all theaters silent — ceasefire compliance 100% — IRGCAF/IRGCN/proxy activity: NONE — COMPASS ${ws.compassCeasefire}%` },
  { id: 't12', label: 'BLOOMBERG', text: `Brent $${ws.brentUsd}/bbl — GCC tankers resume full Hormuz routing — Cape of Good Hope diversion CANCELLED — pre-conflict price range in sight` },
  { id: 't13', label: 'CISA',      text: `ED 26-01: No new Iranian APT offensive operations since ceasefire commencement — threat level under review for downgrade — patch compliance mandated` },
  { id: 't14', label: 'DHS',       text: `NTAS ELEVATED status under review for downgrade — threat level declining with ceasefire compliance — IRGC domestic threat: monitoring continues` },
  { id: 't15', label: 'FBI',       text: `IRGC-linked operatives arrested Houston/NY/Boston prosecution ongoing — no new domestic threat activity since D43 ceasefire commencement` },
  { id: 't16', label: 'DOE',       text: `SPR release active — 50M barrels deployed Day 14 — Brent $${ws.brentUsd}/bbl declining — GCC Aramco Ras Tanura FULLY RESTORED D44` },
  { id: 't17', label: 'NEXUS',     text: `Cross-domain D${d}: ceasefire holding — Abu Dhabi 14-point framework signed D39 — UNSCR 2732 D40 — Iran declaration D42 — POTUS extension D${d}`, urgent: true },
  { id: 't18', label: 'AP',        text: `French Navy CDG (R91) repositioning from Arabian Sea — combat operations ceased — ceasefire posture shift — Rafale M sorties: SUSPENDED` },
  { id: 't19', label: 'CONGRESS',  text: `AUMF-2026 operational review underway — 90-day reporting to Congress — post-conflict authorization scope under NSC review` },
  { id: 't20', label: 'ORACLE-9',  text: `Day ${d}: Iran BM stock ~${ws.bmStockPct}% remaining — combat-exhausted — 6-12 months minimum reconstitution — no credible barrage capability` },
  { id: 't21', label: 'UN',        text: `UNSCR 2732 D40 unanimous — UNSCR 2731 corridor active — IAEA access granted D41 — DG Grossi on-site Natanz — Fordow inspection pending D45` },
  { id: 't22', label: 'MANTIS',    text: `GOLF-7 INACTIVE since D26 Bandar Abbas — GOLF-8 ZB-Bravo INACTIVE — Hormuz mine threat: RESOLVED — MCM complete — all ZB corridors CLOSED OUT` },
  { id: 't23', label: 'ISW',       text: `D${d} post-conflict assessment: Iran expended ~${100 - ws.bmStockPct}% pre-conflict BM inventory — no credible large-barrage reconstitution for 6-12 months` },
  { id: 't24', label: 'CENTCOM',   text: `Day ${d} SITREP: ${ws.sortiesLabel} sorties — ceasefire trial EXTENDED — all five theaters confirming compliance — FPCON ${ws.fpconLevel} — post-conflict review initiated` },
  { id: 't25', label: 'ARMISTICE', text: `Abu Dhabi Phase IV armistice framework negotiations OPENED Day 55 — 47 draft articles under US State Dept and Iran SNSC review — target instrument completion Day 90`, urgent: ws.armisticeActive },
  { id: 't26', label: 'PENTAGON',  text: `NSC/JCS reviewing DEFCON 4->5 downgrade recommendation — Day ${d} ceasefire compliance 100% — JCS Chairman: "all conditions for posture downgrade met pending Day 75 compliance review"` },
  { id: 't27', label: 'IAEA',      text: `Fordow FEP inspection Day 45: IR-2m and IR-6 centrifuge cascades FULLY INOPERATIVE confirmed — enrichment pause 100% verified — DG Grossi: "unprecedented access and transparency"`, urgent: ws.fordowAccessGranted },
  { id: 't28', label: 'ICRC',      text: `POW exchange COMPLETE Day 55 — 9 US service members and 47 IRGC personnel returned under ICRC monitoring — all transfers confirmed — POTUS: "every American is accounted for"`, urgent: ws.armisticeActive },
  { id: 't29', label: 'IEA',       text: `Hormuz transit Day ${d}: 18.4M bbl/day restored — pre-conflict volumes fully recovered — IEA emergency oil measures LIFTED — all SPR emergency drawdowns SUSPENDED` },
  { id: 't30', label: 'NEXUS',     text: `Day ${d} post-conflict COP: Iran BM reconstitution minimum 6-12 months — Shahed-136/238 production halted under Phase III verification protocol — all proxy networks dormant` },
]}
const TICKER_ITEMS = buildTickerItems()

interface Stats {
  count: number
  verified: number
  avgConf: number
  theaters: number
}

async function fetchLiveBrent(): Promise<number | null> {
  try {
    const res = await fetch(
      'https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?interval=1d&range=1d',
      { headers: { 'User-Agent': 'Mozilla/5.0' }, next: { revalidate: 300 }, signal: AbortSignal.timeout(5_000) },
    )
    if (!res.ok) return null
    const data = await res.json() as { chart?: { result?: Array<{ meta?: { regularMarketPrice?: number } }> } }
    const price = data.chart?.result?.[0]?.meta?.regularMarketPrice
    return typeof price === 'number' && price > 0 ? price : null
  } catch {
    return null
  }
}

async function fetchDashboardData(): Promise<{ stats: Stats; recent: Intel[]; liveTickerItems: TickerItem[]; brentUsd: number | null }> {
  const FALLBACK_STATS: Stats = { count: 0, verified: 0, avgConf: 0, theaters: 0 }
  try {
    const supabase = await createServerClient()
    const brentPromise = fetchLiveBrent()
    const [allRes, recentRes, tickerRes] = await Promise.all([
      supabase.from('intel').select('confidence, verified, theater'),
      supabase
        .from('intel')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(4),
      supabase
        .from('intel')
        .select('id, title, source_name, theater, confidence, verified')
        .gte('confidence', 60)
        .order('created_at', { ascending: false })
        .limit(15),
    ])
    const brentUsd = await brentPromise

    // Build live ticker items from fresh high-confidence intel
    type TickerRow = { id: string; title: string; source_name: string | null; theater: string | null; confidence: number | null; verified: boolean | null }
    const liveTickerItems: TickerItem[] = ((tickerRes.data ?? []) as TickerRow[]).map((row) => ({
      id:     `live-${row.id}`,
      label:  row.source_name?.toUpperCase().slice(0, 10)
                ?? row.theater?.toUpperCase()
                ?? 'NEXUS',
      text:   row.title,
      urgent: (row.confidence ?? 0) >= 90 || row.verified === true,
    }))

    if (!allRes.data || allRes.data.length === 0) {
      return {
        stats: FALLBACK_STATS,
        recent: (recentRes.data as Intel[])?.length
          ? (recentRes.data as Intel[])
          : STATIC_INTEL.slice(0, 4),
        liveTickerItems,
        brentUsd,
      }
    }

    type IntelSummaryRow = { confidence: number | null; verified: boolean; theater: string }
    const all = allRes.data as IntelSummaryRow[]
    const stats: Stats = {
      count: all.length,
      verified: all.filter((i) => i.verified).length,
      avgConf:
        all.length > 0
          ? Math.round(
              all.reduce((acc, i) => acc + (i.confidence ?? 0), 0) / all.length
            )
          : 0,
      theaters: new Set(all.map((i) => i.theater)).size,
    }
    return { stats, recent: (recentRes.data as Intel[]) ?? [], liveTickerItems, brentUsd }
  } catch {
    return { stats: FALLBACK_STATS, recent: STATIC_INTEL.slice(0, 4), liveTickerItems: [], brentUsd: null }
  }
}

const QUICK_NAV = [
  {
    label: 'HOMELAND',
    href: '/dashboard/homeland',
    icon: Home,
    desc: 'CONUS Threat & CI Security',
    accent: 'border-red-800 hover:border-red-600 hover:bg-red-950/20 text-red-300',
    iconColor: 'text-red-400',
  },
  {
    label: 'SITREP',
    href: '/dashboard/sitrep',
    icon: FileText,
    desc: 'Daily Situation Report #' + getConflictDay(),
    accent: 'border-emerald-800 hover:border-emerald-600 hover:bg-emerald-950/20 text-emerald-300',
    iconColor: 'text-emerald-400',
  },
  {
    label: 'ORBAT',
    href: '/dashboard/orbat',
    icon: Target,
    desc: 'US & IRGC Order of Battle',
    accent: 'border-amber-800 hover:border-amber-600 hover:bg-amber-950/20 text-amber-300',
    iconColor: 'text-amber-400',
  },
  {
    label: 'TIMELINE',
    href: '/dashboard/timeline',
    icon: Clock,
    desc: 'Conflict Event Timeline',
    accent: 'border-blue-800 hover:border-blue-600 hover:bg-blue-950/20 text-blue-300',
    iconColor: 'text-blue-400',
  },
  {
    label: 'BDA',
    href: '/dashboard/bda',
    icon: ShieldAlert,
    desc: 'Strike & Damage Assessment',
    accent: 'border-red-800 hover:border-red-600 hover:bg-red-950/20 text-red-300',
    iconColor: 'text-red-400',
  },
  {
    label: 'LIVE FEED',
    href: '/dashboard/feed',
    icon: Activity,
    desc: 'Real-Time Intel Feed',
    accent: 'border-zinc-700 hover:border-zinc-500 hover:bg-zinc-900/30 text-zinc-300',
    iconColor: 'text-zinc-400',
  },
  {
    label: 'NEWS SRCS',
    href: '/dashboard/news',
    icon: Newspaper,
    desc: '36 Verified Outlets',
    accent: 'border-zinc-700 hover:border-zinc-500 hover:bg-zinc-900/30 text-zinc-300',
    iconColor: 'text-zinc-400',
  },
  {
    label: 'AGENTS',
    href: '/dashboard/agents',
    icon: Cpu,
    desc: '11 AI Analysis Agents',
    accent: 'border-zinc-700 hover:border-zinc-500 hover:bg-zinc-900/30 text-zinc-300',
    iconColor: 'text-zinc-400',
  },
  {
    label: 'DMO LIVE',
    href: '/dashboard/dmo',
    icon: Map,
    desc: 'Hormuz Strait AI Theater Feed',
    accent: 'border-zinc-700 hover:border-zinc-500 hover:bg-zinc-900/30 text-zinc-300',
    iconColor: 'text-zinc-400',
  },
  {
    label: 'COP',
    href: '/dashboard/cop',
    icon: Globe2,
    desc: 'JADC2 Combined Ops Picture — AIS + Air',
    accent: 'border-emerald-800 hover:border-emerald-600 hover:bg-emerald-950/20 text-emerald-300',
    iconColor: 'text-emerald-400',
  },
  {
    label: 'HVA',
    href: '/dashboard/hva',
    icon: Skull,
    desc: 'Iranian Leaders Eliminated — 10 KIA',
    accent: 'border-red-800 hover:border-red-600 hover:bg-red-950/20 text-red-300',
    iconColor: 'text-red-400',
  },
  {
    label: 'THREATS',
    href: '/dashboard/threats',
    icon: Activity,
    desc: 'ORACLE-9 Probabilistic Threat Engine',
    accent: 'border-amber-800 hover:border-amber-600 hover:bg-amber-950/20 text-amber-300',
    iconColor: 'text-amber-400',
  },
  {
    label: 'CEASEFIRE',
    href: '/dashboard/ceasefire',
    icon: Scale,
    desc: 'Diplomatic Channels & Negotiations',
    accent: 'border-blue-800 hover:border-blue-600 hover:bg-blue-950/20 text-blue-300',
    iconColor: 'text-blue-400',
  },
  {
    label: 'INTEL',
    href: '/dashboard/intel',
    icon: Satellite,
    desc: 'SIGINT / HUMINT / IMINT Fusion',
    accent: 'border-emerald-800 hover:border-emerald-600 hover:bg-emerald-950/20 text-emerald-300',
    iconColor: 'text-emerald-400',
  },
  {
    label: 'LOGISTICS',
    href: '/dashboard/logistics',
    icon: Package,
    desc: 'J4 Munitions & Fleet Readiness',
    accent: 'border-amber-800 hover:border-amber-600 hover:bg-amber-950/20 text-amber-300',
    iconColor: 'text-amber-400',
  },
  {
    label: 'ECON WAR',
    href: '/dashboard/econ',
    icon: TrendingUp,
    desc: 'Energy Markets & Sanctions',
    accent: 'border-yellow-800 hover:border-yellow-600 hover:bg-yellow-950/20 text-yellow-300',
    iconColor: 'text-yellow-400',
  },
]

export default async function CommandOverviewPage() {
  let day = 1
  let stats: Stats = { count: 0, verified: 0, avgConf: 0, theaters: 0 }
  let recent: Intel[] = STATIC_INTEL.slice(0, 4)
  let liveTickerItems: TickerItem[] = []
  let brentUsd: number | null = null

  try {
    day = getConflictDay()
    const data = await fetchDashboardData()
    stats = data.stats
    recent = data.recent
    liveTickerItems = data.liveTickerItems
    brentUsd = data.brentUsd
  } catch (err) {
    // Surface render errors in the browser instead of returning a blank 500
    console.error('[Dashboard:CommandOverviewPage] uncaught render error:', err)
    return (
      <div className="p-8 max-w-2xl">
        <div className="border border-red-900 bg-red-950/10 p-6 space-y-3">
          <p className="text-[9px] tracking-[0.3em] text-red-400 uppercase">Dashboard Init Error</p>
          <pre className="text-[10px] text-zinc-400 whitespace-pre-wrap break-all bg-zinc-900 p-3">
            {String(err)}
            {'\n'}
            {err instanceof Error ? err.stack : ''}
          </pre>
          <p className="text-[9px] text-zinc-600">Check your terminal for the full stack trace.</p>
        </div>
      </div>
    )
  }

  const ws = getWarStats(day)

  const statTiles = [
    {
      label: 'Intel Reports',
      value: stats.count,
      sub: 'total in database',
      icon: BarChart3,
      color: 'text-emerald-400',
    },
    {
      label: 'Verified',
      value: stats.verified,
      sub: `${stats.count > 0 ? Math.round((stats.verified / stats.count) * 100) : 74}% corroborated`,
      icon: CheckCircle2,
      color: 'text-blue-400',
    },
    {
      label: 'Active Theaters',
      value: stats.theaters,
      sub: 'of 9 theaters engaged',
      icon: Globe,
      color: 'text-amber-400',
    },
    {
      label: 'Avg Confidence',
      value: `${stats.avgConf}%`,
      sub: 'cross-source average',
      icon: TrendingUp,
      color: 'text-zinc-300',
    },
  ]

  return (
    <div className="space-y-5 max-w-screen-xl">
      {/* ── Cinematic THREATCON banner ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-5 py-4">
          {/* Scanline overlay */}
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(239,68,68,0.01) 2px, rgba(239,68,68,0.01) 4px)'}} />
          <div className="relative z-[3] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="relative">
                <AlertTriangle size={18} className="text-red-500 animate-pulse drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
              </div>
              <div>
                <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                  Operation Epic Fury — Day {day} of Active Hostilities — {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })}
                </p>
                <p className="text-sm font-bold tracking-widest text-red-400 uppercase glow-red">
                  FPCON DELTA / THREATCON SEVERE — ORACLE-9 Assessment Active
                </p>
                <p className="text-[10px] text-zinc-500 mt-1 tracking-wide">
                  ORACLE-9 live threat probabilities displayed below — Hormuz {ws.zbAlphaPct >= 90 ? 'OPEN TRANSIT' : ws.zbAlphaPct >= 50 ? 'PARTIAL TRANSIT' : 'CONTESTED'} (ZB-α {ws.zbAlphaPct}% cleared) — FPCON DELTA maintained across all CENTCOM AOR — Muscat back-channel active — Day {day} all-domain hostile activity elevated.
                </p>
              </div>
            </div>
            <div className="shrink-0 flex flex-col items-end gap-2">
              <div className="on-air-badge inline-block bg-red-900/60 text-red-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-red-800/60">
                ● LIVE C2
              </div>
              <ThreatMeter level="SEVERE" size="lg" showLabel />
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" />
      </div>

      {/* Breaking news ticker — live Supabase intel; static fallback only when DB empty */}
      <NewsTicker items={liveTickerItems.length > 0 ? liveTickerItems : TICKER_ITEMS} />

      {/* Intel DB stats strip */}
      <div className="tac-card px-3 py-2">
        <IntelStatsBanner />
      </div>

      {/* AI Platform health strip */}
      <PlatformHealth compact />

      {/* Admin-only operational panels */}
      <AccessGate tier="admin"><GovernorPanel /></AccessGate>
      <AccessGate tier="admin"><RevenuePanel compact /></AccessGate>
      <AccessGate tier="admin"><WorkflowPanel compact /></AccessGate>
      <AccessGate tier="admin"><AutonomousPanel compact /></AccessGate>

      {/* Subscriber intelligence panels */}
      <AccessGate tier="subscriber"><DebatePanel compact /></AccessGate>
      <AccessGate tier="subscriber"><ForesightPanel compact /></AccessGate>
      <AccessGate tier="subscriber"><SynthesisPanel compact /></AccessGate>

      {/* Threat domain status grid — cinematic */}
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2">
        {[
          { label: 'Nuclear',      level: 'HIGH',     dot: 'bg-yellow-400',  text: 'text-yellow-400' },
          { label: 'Maritime',     level: 'HIGH',     dot: 'bg-cyan-400',    text: 'text-cyan-400' },
          { label: 'Hormuz',       level: 'SEVERE',   dot: 'bg-red-500 animate-pulse', text: 'text-red-400' },
          { label: 'Air',          level: 'HIGH',     dot: 'bg-sky-400',     text: 'text-sky-400' },
          { label: 'Missiles',     level: 'HIGH',     dot: 'bg-amber-400',   text: 'text-amber-400' },
          { label: 'Cyber',        level: 'ELEVATED', dot: 'bg-purple-400',  text: 'text-purple-400' },
          { label: 'Diplomatic',   level: 'ELEVATED', dot: 'bg-blue-400',    text: 'text-blue-400' },
          { label: 'Economic',     level: 'HIGH',     dot: 'bg-lime-400',    text: 'text-lime-400' },
          { label: 'Proxy',        level: 'ELEVATED', dot: 'bg-orange-400',  text: 'text-orange-400' },
        ].map(({ label, level, dot, text }) => {
          const levelBg =
            level === 'SEVERE'   ? 'border-red-800    bg-red-950/20' :
            level === 'HIGH'     ? 'border-amber-800  bg-amber-950/10' :
            level === 'ELEVATED' ? 'border-sky-900    bg-sky-950/10' :
                                   'border-zinc-800   bg-zinc-900/20'
          const levelText =
            level === 'SEVERE'   ? 'text-red-400' :
            level === 'HIGH'     ? 'text-amber-400' :
            level === 'ELEVATED' ? 'text-sky-400' : 'text-zinc-500'
          const levelGlow =
            level === 'SEVERE' ? 'hover:shadow-[0_0_12px_rgba(239,68,68,0.2)]' :
            level === 'HIGH'   ? 'hover:shadow-[0_0_12px_rgba(245,158,11,0.2)]' :
                                 'hover:shadow-[0_0_12px_rgba(56,189,248,0.15)]'
          return (
            <div key={label} className={`tac-card rounded-sm p-2.5 space-y-1.5 border ${levelBg} transition-all duration-300 hover:scale-[1.03] ${levelGlow}`}>
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${dot}`} />
                <span className={`text-[9px] font-bold tracking-widest uppercase ${text}`}>{label}</span>
              </div>
              <span className={`text-[8px] tracking-widest ${levelText}`}>{level}</span>
            </div>
          )
        })}
      </div>

      {/* Stat tiles — cinematic glow */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {statTiles.map(({ label, value, sub, icon: Icon, color }) => (
          <div key={label} className="tac-card p-4 space-y-1.5 relative overflow-hidden group hover:scale-[1.02] transition-transform duration-200">
            <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity" style={{background: 'radial-gradient(ellipse at center, rgba(16,185,129,0.04), transparent 70%)'}} />
            <div className="flex items-center justify-between relative z-[1]">
              <p className="text-[9px] tracking-widest text-zinc-500 uppercase">{label}</p>
              <Icon size={12} className="text-zinc-700" />
            </div>
            <p className={`text-2xl font-bold tabular-nums ${color} relative z-[1]`}>{value}</p>
            <p className="text-[10px] text-zinc-600 relative z-[1]">{sub}</p>
          </div>
        ))}
      </div>

      {/* Doctrine and provenance upgrades */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <NexusDoctrinePanel conflictDay={day} />
        <ProvenancePulsePanel recentIntel={recent} />
      </div>

      {/* BMD Battle Tracking — ORACLE-9 BMDS assessment */}
      <BmdBattlePanel />

      {/* Combat Power strip — cinematic */}
      {(() => {
        const ws = getWarStats()
        const combatStats = [
          { label: 'Coalition Sorties', value: ws.sortiesLabel,                                                     sub: `CVW-7 / RAF / RAAF / CDG`,           color: 'text-sky-400',     glow: 'group-hover:drop-shadow-[0_0_6px_rgba(56,189,248,0.4)]' },
          { label: 'TBMD Intercept',    value: `~${ws.tbmdInterceptPct}%`,                                          sub: 'PATRIOT + THAAD terminal',           color: 'text-emerald-400', glow: 'group-hover:drop-shadow-[0_0_6px_rgba(16,185,129,0.4)]' },
          { label: 'Iran BMs Remain',   value: `~${Math.round(ws.bmStockPct * 1.5)}–${Math.round(ws.bmStockPct * 2.5)}`, sub: `post-Alpha-5 D26 ZULU-14 assessed`, color: 'text-amber-400', glow: 'group-hover:drop-shadow-[0_0_6px_rgba(245,158,11,0.4)]' },
          { label: 'Brent Crude',       value: brentUsd ? `$${brentUsd.toFixed(0)}/bbl` : `$${ws.brentUsd}/bbl`, sub: brentUsd ? 'Yahoo Finance live' : 'COMPASS model estimate', color: 'text-emerald-400', glow: 'group-hover:drop-shadow-[0_0_6px_rgba(16,185,129,0.4)]' },
          { label: 'Ceasefire',         value: `${ws.compassCeasefire}%`,                                           sub: `COMPASS 72h D${ws.day}`,             color: 'text-blue-400',    glow: 'group-hover:drop-shadow-[0_0_6px_rgba(59,130,246,0.4)]' },
        ]
        return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        {combatStats.map(({ label, value, sub, color, glow }) => (
          <div key={label} className="tac-card p-3 space-y-1 group hover:scale-[1.02] transition-transform duration-200">
            <p className="text-[9px] tracking-widest text-zinc-600 uppercase">{label}</p>
            <p className={`text-lg font-bold tabular-nums leading-none ${color} ${glow} transition-all`}>{value}</p>
            <p className="text-[9px] text-zinc-700 leading-tight">{sub}</p>
          </div>
        ))}
      </div>
        )
      })()}

      {/* HERALD live news aggregation — always visible */}
      <HeraldFeed limit={8} />

      {/* ORACLE-9 threat engine — subscriber only */}
      <AccessGate tier="subscriber">
        <OraclePanel />
      </AccessGate>

      {/* Situation overview + Quick Nav */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Situation narrative — 2/3 width — cinematic */}
        <div className="lg:col-span-2 video-feed-frame tac-card p-5 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">SITREP LIVE</span>
          </div>
          <h2 className="tac-section-header mb-4 relative z-[1]">
            <span className="glow-green">Situation Overview — Day {day} / {new Date(CONFLICT_EPOCH + (day - 1) * 86_400_000).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })}</span>
          </h2>
          <div className="space-y-3 text-xs text-zinc-400 leading-relaxed">
            <p>
              <span className="text-zinc-200 font-semibold">► NAVAL:</span>{' '}
              USS Eisenhower (CVN-69) Strike Group continues strike operations from the North Arabian
              Sea. Air Wing CVW-7 has conducted 1,400+ sorties against IRGC maritime, IADS, and missile
              logistics targets. The Strait of Hormuz remains contested — Iranian mines and fast-attack
              craft harassment continue to restrict commercial traffic since Day 3. USS Georgia (SSGN-729)
              has expended 170+ TLAMs against Iranian air defense nodes and C2 infrastructure.{' '}
              <a
                href="https://www.centcom.mil/MEDIA/PRESS-RELEASES/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [CENTCOM]
              </a>
            </p>

            <p>
              <span className="text-zinc-200 font-semibold">► MISSILE THREAT:</span>{' '}
              Five ballistic missile barrages complete. Barrage Alpha-5 (Day 26, 26 Mar) struck Al Udeid AB
              (Qatar) — 27 of 31 BMs intercepted (86%, PATRIOT/THAAD). Two US Air Force personnel KIA;
              14 wounded. Coalition KIA total: 13. ZULU-14 TEL reconstitution ongoing — 6th barrage
              risk assessed at 41% within 72h by ORACLE-9. Iran BM inventory estimated at ~92-95% expended.{' '}
              <a
                href="https://www.reuters.com/world/middle-east/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [Reuters, 26 Mar]
              </a>{' '}
              <a
                href="https://www.nytimes.com/section/world/middleeast"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [NYT, 27 Mar]
              </a>
            </p>

            <p>
              <span className="text-zinc-200 font-semibold">► NUCLEAR:</span>{' '}
              Joint US-Israeli precision strikes on Natanz, Fordow, and Isfahan enrichment/conversion
              facilities on Days 1–3 are assessed to have set back Iran&apos;s weapons-grade uranium
              production capability by an estimated 18–24 months (pre-strike enrichment level: ~84%
              U-235). IAEA Director General confirmed Iran expelled all inspectors on Day 5; all
              monitoring equipment offline.{' '}
              <a
                href="https://www.iaea.org/news"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [IAEA, 5 Mar]
              </a>{' '}
              <a
                href="https://www.armscontrolwonk.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [Arms Control Wonk]
              </a>
            </p>

            <p>
              <span className="text-zinc-200 font-semibold">► CYBER:</span>{' '}
              IRGC Cyber Command (APT33/APT34/APT35) has conducted destructive attacks on Saudi Aramco
              operational technology networks (Day 11) and multiple intrusions against US DoD contractor
              systems in the Gulf region. Israeli critical infrastructure also targeted.{' '}
              <a
                href="https://www.cisa.gov/news-events/alerts"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [CISA Alert, 11 Mar]
              </a>
            </p>

            <p>
              <span className="text-zinc-200 font-semibold">► DIPLOMATIC:</span>{' '}
              BREAKTHROUGH (Day 27): Abu Dhabi proximity talks underway — POTUS confirms ceasefire framework.
              Iran SNSC dropped US military withdrawal precondition (Day 26); Oman channel
              REACTIVATED. UNSCR 2731 passed Day 25 (14-1, humanitarian corridor active). COMPASS
              ceasefire confidence: {ws.compassCeasefire}% within 72h. Brent crude declining on ceasefire
              optimism. Hormuz: MCM ZB-Alpha {ws.zbAlphaPct}% cleared — 7+ VLCCs transited.{' '}
              <a
                href="https://www.bbc.com/news/world/middle_east"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [BBC, 27 Mar]
              </a>{' '}
              <a
                href="https://www.bloomberg.com/energy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-400 underline underline-offset-2"
              >
                [Bloomberg]
              </a>
            </p>
          </div>
        </div>

        {/* Quick navigation — 1/3 width */}
        <div className="space-y-3">
          <div className="tac-card p-4">
            <h2 className="tac-section-header mb-3">Quick Navigation</h2>
            <div className="space-y-1">
              {QUICK_NAV.map(({ label, href, icon: Icon, desc, accent, iconColor }) => (
                <Link
                  key={href}
                  href={href}
                  className={`group flex items-center gap-3 px-3.5 min-h-[44px] rounded-lg border text-[11px] font-medium tracking-[0.15em] uppercase transition-all duration-200 active:scale-[0.98] ${accent}`}
                >
                  <Icon size={15} strokeWidth={1.75} className={`shrink-0 ${iconColor} group-hover:scale-110 transition-transform`} />
                  <div className="min-w-0 flex-1">
                    <span className="font-semibold">{label}</span>
                    <p className="text-zinc-600 normal-case font-normal text-[9px] leading-tight truncate">
                      {desc}
                    </p>
                  </div>
                  <svg className="w-3.5 h-3.5 shrink-0 text-zinc-700 group-hover:text-zinc-400 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/></svg>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Prayer for Peace */}
      <div className="verse-strip rounded-sm p-4">
        <div className="flex items-start gap-3">
          <span className="text-amber-500/50 text-lg leading-none mt-0.5 shrink-0">✝</span>
          <div className="space-y-1">
            <p className="text-[9px] font-bold tracking-[0.2em] text-amber-600/60 uppercase">A Note on Context</p>
            <p className="text-[10px] text-amber-500/45 italic leading-relaxed">
              This dashboard presents AI-synthesized open-source intelligence analysis for real-time situational awareness.
              In all things, we seek understanding, not fear.
              &ldquo;Do not be anxious about anything, but in every situation, by prayer and petition, with
              thanksgiving, present your requests to God. And the peace of God, which transcends all
              understanding, will guard your hearts and your minds.&rdquo;
            </p>
            <p className="text-[9px] text-amber-600/55 tracking-widest">— Philippians 4:6-7</p>
          </div>
        </div>
      </div>

      {/* ── What This Means For You — citizen-friendly explainer — cinematic ── */}
      <div className="video-feed-frame tac-card border border-sky-900/60 bg-sky-950/10 p-5 relative overflow-hidden">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(14,165,233,0.03) 0%, transparent 50%)'}} />
        <div className="flex items-center gap-2 border-b border-sky-900/40 pb-3 mb-4 relative z-[1]">
          <Home size={13} className="text-sky-400 drop-shadow-[0_0_6px_rgba(14,165,233,0.4)]" />
          <h2 className="text-[10px] font-bold tracking-[0.3em] text-sky-400 uppercase glow-blue">What This Conflict Means For You — American Citizen Summary</h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="space-y-1">
            <p className="text-[9px] font-bold tracking-widest text-amber-400 uppercase">⛽ Gas Prices</p>
            <p className="text-zinc-400 leading-relaxed normal-case">
              Brent crude peaked at <strong className="text-amber-300">$118/bbl</strong> — now declining to{' '}
              <strong className="text-amber-300">${brentUsd ? `${brentUsd.toFixed(0)}` : ws.brentUsd}/bbl</strong> as Hormuz transit resumes (ZB-α {ws.zbAlphaPct}% cleared).
              Pump prices remain <strong className="text-amber-300">$0.15–0.25/gal</strong> above pre-conflict levels.
              DOE 50M-barrel SPR release ongoing.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] font-bold tracking-widest text-red-400 uppercase">🏠 Homeland Threat</p>
            <p className="text-zinc-400 leading-relaxed normal-case">
              DHS issued an <strong className="text-red-300">NTAS Elevated Alert</strong>. FBI arrested IRGC-linked operatives
              in Houston and New York surveilling petrochemical plants and ports. 
              Stay alert — <a href="/dashboard/homeland" className="text-sky-400 hover:underline">see full Homeland brief →</a>
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] font-bold tracking-widest text-emerald-400 uppercase">🛡 Your Military</p>
            <p className="text-zinc-400 leading-relaxed normal-case">
              US forces have <strong className="text-emerald-300">zero aircraft lost to hostile fire</strong> in {ws.sortiesLabel} coalition combat sorties.
              3 KIA confirmed Day 17 from missile barrage. Iran has expended ~{100 - ws.bmStockPct}% of its ballistic missile inventory.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-[9px] font-bold tracking-widest text-blue-400 uppercase">🕊 Peace Prospects</p>
            <p className="text-zinc-400 leading-relaxed normal-case">
              COMPASS model now at <strong className="text-blue-300">{ws.compassCeasefire}% ceasefire probability</strong> within 72 hours —
              Abu Dhabi proximity talks active; UNSCR 2731 passed Day 25; Iran SNSC dropped withdrawal precondition Day 26.
              <a href="/dashboard/ceasefire" className="text-sky-400 hover:underline ml-1">Track negotiations →</a>
            </p>
          </div>
        </div>
      </div>

      {/* Recent intel */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="tac-section-header">Latest Intel Reports</h2>
          <Link
            href="/dashboard/feed"
            className="text-[10px] text-emerald-600 hover:text-emerald-400 tracking-widest uppercase transition-colors"
          >
            View full feed →
          </Link>
        </div>
        <div className="space-y-3">
          {recent.map((item) => (
            <IntelCard key={item.id} intel={item} />
          ))}
        </div>
      </div>
    </div>
  )
}
