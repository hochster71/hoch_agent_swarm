import {
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  BarChart3,
  Globe,
  Zap,
  ExternalLink,
  AlertTriangle,
  ShieldAlert,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toDateStr } from '@/lib/conflict-day'
import { CompassPanel } from '@/components/CompassPanel'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'

export const revalidate = 0
export const metadata = { title: 'Economic Warfare — Operation Epic Fury' }

// ── Live spot price fetch (Yahoo Finance, 5-min server cache) ─────────────────
interface SpotPrices {
  brentUsd:   number
  wtiUsd:     number
  ngUsdMmbtu: number
  source:     string
  stale:      boolean
  fetchedAt:  string
}

const SPOT_FALLBACK: SpotPrices = {
  brentUsd:   0,
  wtiUsd:     0,
  ngUsdMmbtu: 0,
  source:     'static-fallback',
  stale:      true,
  fetchedAt:  new Date().toISOString(),
}

async function fetchSpotPrice(ticker: string): Promise<number | null> {
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=1d`
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0' },
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(6_000),
    })
    if (!res.ok) return null
    const data = await res.json() as {
      chart?: { result?: Array<{ meta?: { regularMarketPrice?: number } }> }
    }
    const price = data.chart?.result?.[0]?.meta?.regularMarketPrice
    return typeof price === 'number' && price > 0 ? price : null
  } catch {
    return null
  }
}

async function getLiveSpotPrices(): Promise<SpotPrices> {
  try {
    const [brent, wti, ng] = await Promise.allSettled([
      fetchSpotPrice('BZ=F'),
      fetchSpotPrice('CL=F'),
      fetchSpotPrice('NG=F'),
    ])
    const brentUsd   = brent.status === 'fulfilled' ? brent.value   : null
    const wtiUsd     = wti.status   === 'fulfilled' ? wti.value     : null
    const ngUsdMmbtu = ng.status    === 'fulfilled' ? ng.value      : null

    if (brentUsd === null && wtiUsd === null && ngUsdMmbtu === null) {
      return SPOT_FALLBACK
    }
    return {
      brentUsd:   brentUsd   ?? SPOT_FALLBACK.brentUsd,
      wtiUsd:     wtiUsd     ?? SPOT_FALLBACK.wtiUsd,
      ngUsdMmbtu: ngUsdMmbtu ?? SPOT_FALLBACK.ngUsdMmbtu,
      source:     'yahoo-finance',
      stale:      (brentUsd === null || wtiUsd === null || ngUsdMmbtu === null),
      fetchedAt:  new Date().toISOString(),
    }
  } catch {
    return SPOT_FALLBACK
  }
}

const CONFLICT_DAY  = getConflictDay()
const CONFLICT_DATE = toDateStr(CONFLICT_DAY)

// ── Energy markets ────────────────────────────────────────────────────────────

interface EnergyMarket {
  commodity: string
  unit: string
  preConflict: number
  current: number
  dayHigh: number
  dayLow: number
  pctChange: number
  trend: 'UP' | 'DOWN' | 'STABLE'
  driver: string
  source: string
  sourceUrl: string
}

const ENERGY: EnergyMarket[] = [
  {
    commodity: 'Brent Crude',
    unit: 'USD/bbl',
    preConflict: 74,
    current: 94,
    dayHigh: 97,
    dayLow: 91,
    pctChange: 27,
    trend: 'DOWN',
    driver: `Price recovering from $123 Day-17 peak. Ceasefire framework (68% COMPASS probability) and Oman/UAE diplomatic progress reducing conflict risk premium. First 7+ VLCC commercial transits via ZB-Alpha corridor since D24. Saudi Arabia OPEC+ +2M bbl/day announced with US coordination. UNSCR 2731 passed Day 25.`,
    source: 'Bloomberg Energy',
    sourceUrl: 'https://www.bloomberg.com/energy',
  },
  {
    commodity: 'WTI Crude',
    unit: 'USD/bbl',
    preConflict: 71,
    current: 90,
    dayHigh: 93,
    dayLow: 87,
    pctChange: 27,
    trend: 'DOWN',
    driver: `US SPR emergency release (50M bbl Day 14) limited WTI-Brent spread. Shale ramp-up accelerating — Permian rig count +18% since conflict start. Refinery margin stabilizing as Hormuz ZB-Alpha corridor 78% cleared.`,
    source: 'CME Group',
    sourceUrl: 'https://www.cmegroup.com/markets/energy/crude-oil/light-crude.html',
  },
  {
    commodity: 'LNG (DES Japan)',
    unit: 'USD/MMBtu',
    preConflict: 12.4,
    current: 35.2,
    dayHigh: 37.1,
    dayLow: 33.0,
    pctChange: 184,
    trend: 'DOWN',
    driver: 'Qatar LNG route still offline but Abu Dhabi ceasefire framework (D27) triggered 15% spot price reduction in 48 hours. Japan/Korea strategic reserves at 72% — buffer maintained. EU emergency gas storage drawdown pace slowing on diplomatic progress.',
    source: 'S&P Global Platts',
    sourceUrl: 'https://www.spglobal.com/commodities/en/market-insights/latest-news/lng',
  },
  {
    commodity: 'Fuel Oil (380 CST)',
    unit: 'USD/MT',
    preConflict: 410,
    current: 820,
    dayHigh: 840,
    dayLow: 798,
    pctChange: 100,
    trend: 'DOWN',
    driver: `Bunkering disruption easing as Cape of Good Hope diversions decrease — 7 VLCCs transited ZB-Alpha corridor D24–D${CONFLICT_DAY} under coalition escort. Singapore hub benchmark recovering.`,
    source: 'Argus Media',
    sourceUrl: 'https://www.argusmedia.com/en/crude-oil',
  },
  {
    commodity: 'US Natural Gas (HH)',
    unit: 'USD/MMBtu',
    preConflict: 3.2,
    current: 5.6,
    dayHigh: 5.8,
    dayLow: 5.3,
    pctChange: 75,
    trend: 'DOWN',
    driver: 'European LNG demand remains elevated with Qatar route offline but US export terminal bookings easing as ceasefire probability rises. Freeport and Sabine Pass at 98% capacity — down from 103% peak.',
    source: 'EIA Natural Gas',
    sourceUrl: 'https://www.eia.gov/naturalgas/',
  },
]

// ── Sanctions scorecard ───────────────────────────────────────────────────────

interface SanctionRow {
  regime: string
  authority: string
  effective: string
  target: string
  impact: 'HIGH' | 'MEDIUM' | 'LIMITED'
  status: 'ACTIVE' | 'PROPOSED' | 'SUPERSEDED'
  notes: string
}

const SANCTIONS: SanctionRow[] = [
  {
    regime: 'CAPTA-2026 (IRGC Total)',
    authority: 'OFAC / EO 14147',
    effective: 'Day 1 · 28 FEB 2026',
    target: 'All IRGC entities, subsidiaries, front companies globally',
    impact: 'HIGH',
    status: 'ACTIVE',
    notes: 'Full blocking sanctions on all IRGC-associated entities. SWIFT network has suspended 12 Iranian banks. OFAC SDN list expanded by 847 entries. Oil revenue interception mechanisms active.',
  },
  {
    regime: 'EU Regulation 2026/118',
    authority: 'EU Council / HR/VP',
    effective: 'Day 3 · 03 MAR 2026',
    target: 'Iranian energy exports, IRGC senior leadership, defense procurement',
    impact: 'HIGH',
    status: 'ACTIVE',
    notes: 'EU total embargo on Iranian oil and petroleum products. Asset freeze on 234 individuals and 78 entities. European P&I clubs withdrawing insurance from Iranian tanker fleet.',
  },
  {
    regime: 'G7 SWIFT Exclusion',
    authority: 'G7 Finance Ministers',
    effective: 'Day 4 · 04 MAR 2026',
    target: 'Bank Melli, Bank Saderat, Bank Tejarat and 14 subsidiaries',
    impact: 'HIGH',
    status: 'ACTIVE',
    notes: 'SWIFT messaging access suspended for top 17 Iranian financial institutions. Iranian central bank excluded from Euroclear and Clearstream. Rial-dollar exchange market collapsed.',
  },
  {
    regime: 'US Petroleum Revenue Freeze',
    authority: 'Treasury OFAC / EO 14148',
    effective: 'Day 5 · 05 MAR 2026',
    target: 'Iranian oil revenue in third-country accounts (China, UAE, India)',
    impact: 'MEDIUM',
    status: 'ACTIVE',
    notes:
      'Secondary sanctions warning issued to Chinese state banks holding Iranian oil revenues. India complied Day 8 — $2.3B frozen. China partial compliance — $6.1B disputed. UAE full compliance Day 3.',
  },
  {
    regime: 'Arms / Dual-Use Technology',
    authority: 'Wassenaar + EAR/ITAR',
    effective: 'Day 1 (pre-existing)',
    target: 'Defense technology, semiconductors, precision manufacturing',
    impact: 'LIMITED',
    status: 'ACTIVE',
    notes: 'Pre-existing regime — limited marginal impact. Iran has sufficient domestic production for near-term conflict. Semiconductor sanctions reducing long-term precision weapons development.',
  },
  {
    regime: 'Global Maritime Exclusion',
    authority: 'IMO / Flag State Notices',
    effective: 'Day 6 · 06 MAR 2026',
    target: 'Iranian flag vessels, IRISL fleet, IRGCN commercial fronts',
    impact: 'MEDIUM',
    status: 'ACTIVE',
    notes: 'IMO approved emergency exclusion of 47 Iranian-flagged vessels from global ports. P&I insurance withdrawn from all IRISL-associated vessels. 19 vessels currently stranded in foreign ports.',
  },
]

// ── Financial market impact ───────────────────────────────────────────────────

interface MarketData {
  market: string
  pctChange: number
  trend: 'UP' | 'DOWN' | 'STABLE'
  note: string
}

const MARKETS: MarketData[] = [
  { market: 'S&P 500', pctChange: -11.2, trend: 'DOWN', note: 'Energy sector +28%; Technology -14%; Defense +41%' },
  { market: 'MSCI Emerging Markets', pctChange: -18.4, trend: 'DOWN', note: 'Gulf EM equities worst hit; China -9.1%; India -12.3%' },
  { market: 'Gold (spot)', pctChange: +24.1, trend: 'UP', note: '$3,247/oz — safe haven demand; central bank purchases accelerating' },
  { market: 'US Dollar Index (DXY)', pctChange: +6.8, trend: 'UP', note: 'Reserve currency flight — EUR/USD at 1.06; safe-haven demand' },
  { market: 'VIX (Volatility)', pctChange: +187, trend: 'UP', note: '62.4 — highest since COVID-19 March 2020 peak' },
  { market: 'Iran CDS (5yr sovereign)', pctChange: +1840, trend: 'UP', note: 'Effectively in default — no buyers; NIOC bond trading at 3 cents/$' },
  { market: 'Saudi ARAMCO (2222.SR)', pctChange: +38.4, trend: 'UP', note: 'Capacity premium despite Abqaiq disruption; war premium embedded' },
  { market: 'Defense ETF (ITA)', pctChange: +41.2, trend: 'UP', note: 'Raytheon +47%; LMT +39%; Northrop +44%; Boeing +28%' },
]

// ── Iranian economy ───────────────────────────────────────────────────────────

const IRAN_ECONOMIC = [
  { label: 'Iranian Rial / USD (black market)', value: '2,100,000:1', vs: '590,000:1 pre-conflict', pct: -72, color: 'text-red-400' },
  { label: 'Estimated oil export revenue loss/day', value: '$420M/day', vs: 'Total loss since Day 1', pct: -100, color: 'text-red-400' },
  { label: 'Tehran Stock Exchange (TEDPIX)', value: '-61%', vs: 'vs Day 1 open — suspended Day 7', pct: -61, color: 'text-red-400' },
  { label: 'Iranian foreign exchange reserves', value: '~$18B accessible', vs: '$35B pre-conflict (China holding ~$8B disputed)', pct: -49, color: 'text-red-400' },
  { label: 'Iran domestic inflation estimate', value: '~240% annualised', vs: '42% annualised pre-conflict', pct: 471, color: 'text-red-400' },
  { label: 'Petrochemical production (Bandar Imam)', value: '~18% capacity', vs: '~85% pre-conflict — US strikes', pct: -79, color: 'text-red-400' },
]

// ── Global supply disruption ──────────────────────────────────────────────────

const SUPPLY_IMPACT = [
  { region: 'East Asia (Japan/Korea/Taiwan)', vulnerability: 88, note: '35–40% of crude oil imports via Hormuz — emergency reserves 90 days declared' },
  { region: 'India', vulnerability: 72, note: '18% crude via Hormuz — VLCC rerouting Cape adds $4.2/bbl premium' },
  { region: 'European Union', vulnerability: 34, note: 'Qatar LNG 12% of EU gas supply offline — emergency storage drawdown active' },
  { region: 'United States', vulnerability: 12, note: 'Low direct exposure — SPR release + shale buffer; refinery margin spike $18/bbl' },
  { region: 'China', vulnerability: 41, note: '7% crude via Hormuz — strategic reserve drawdown to 90 days; Russia pipeline reroute' },
]

// ── Energy price sparkline data (Day 1 → present) ─────────────────────────────────────────────
const ENERGY_SPARKLINES: Record<string, number[]> = {
  'Brent Crude':         [ 78,  92, 103, 107, 108, 108, 107, 108, 109, 110, 111, 110, 111, 109, 110, 111, 112, 114, 116, 118, 120, 122, 118, 109, 103,  98,  94 ],
  'WTI Crude':           [ 74,  87,  96,  97,  98,  97,  96,  97,  97,  98,  98,  97,  98,  95,  96,  97,  98,  98,  98,  98,  99, 100,  97,  94,  92,  91,  90 ],
  'LNG (DES Japan)':     [ 14,  18,  26,  31,  34,  36,  37,  38,  39,  40,  40,  41,  41,  40,  40,  41,  41,  41,  41, 41.6, 42, 43, 42, 39.5, 37.5, 36.2, 35.2 ],
  'Fuel Oil (380 CST)':  [420, 510, 650, 710, 740, 760, 780, 800, 815, 825, 835, 845, 855, 860, 865, 868, 870, 874, 882, 890, 894, 900, 888,  865,  845,  832, 820 ],
  'US Natural Gas (HH)': [3.2, 3.4, 3.8, 4.1, 4.3, 4.5, 4.6, 4.7, 4.8, 5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.1, 6.2, 6.3, 6.2,   6.0,   5.8,  5.7,  5.6 ],
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function TrendIcon({ trend }: { trend: 'UP' | 'DOWN' | 'STABLE' }) {
  if (trend === 'UP')   return <TrendingUp   size={12} className="text-red-400 shrink-0" />
  if (trend === 'DOWN') return <TrendingDown size={12} className="text-emerald-400 shrink-0" />
  return <Minus size={12} className="text-zinc-500 shrink-0" />
}

function MiniSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null
  const w = 100, h = 28
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w
    const y = h - ((v - min) / range) * (h - 6) - 3
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const fillPts = `0,${h} ${pts} ${w},${h}`
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <polyline points={fillPts} fill="#f59e0b" fillOpacity="0.08" stroke="none" />
      <polyline points={pts} fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ImpactBadge({ impact }: { impact: SanctionRow['impact'] }) {
  const cfg = {
    HIGH:    'text-emerald-400 border-emerald-700 bg-emerald-950/20',
    MEDIUM:  'text-yellow-400 border-yellow-700 bg-yellow-950/20',
    LIMITED: 'text-zinc-400 border-zinc-600 bg-zinc-800',
  }[impact]
  return <span className={cn('px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm uppercase', cfg)}>{impact}</span>
}

function StatusDot({ status }: { status: SanctionRow['status'] }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[9px] font-bold tracking-widest',
      status === 'ACTIVE' ? 'text-emerald-400' : status === 'PROPOSED' ? 'text-amber-400' : 'text-zinc-500'
    )}>
      <span className={cn('inline-block w-1.5 h-1.5 rounded-full', status === 'ACTIVE' ? 'bg-emerald-400 animate-pulse' : status === 'PROPOSED' ? 'bg-amber-400' : 'bg-zinc-500')} />
      {status}
    </span>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function EconPage() {
  const spot = await getLiveSpotPrices()

  // Scenario conflict premium vs. real market (how much of war is already priced in)
  const brentPremium  = spot.source !== 'static-fallback' ? Math.round(spot.brentUsd - 74) : null
  const wtiPremium    = spot.source !== 'static-fallback' ? Math.round(spot.wtiUsd - 71)   : null

  return (
    <div className="space-y-5 max-w-screen-xl">

      {/* Live feeds — economic & energy intel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TheaterIntelFeed theater="Economic" limit={12} />
        <LiveNewsBoard limit={20} warFilter={false} compact={false} />
      </div>

      {/* ── Cinematic Econ Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(234,179,8,0.012) 2px, rgba(234,179,8,0.012) 4px)'}} />
          <div className="relative z-[3] flex items-start gap-3">
            <div className="relative">
              <DollarSign size={26} className="text-yellow-400 drop-shadow-[0_0_8px_rgba(234,179,8,0.5)]" />
              <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-yellow-400 rounded-full animate-pulse" />
            </div>
            <div className="flex-1">
              <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                Economic Warfare Assessment — Day {CONFLICT_DAY} of Active Hostilities
              </p>
              <h1 className="text-lg font-bold tracking-widest text-yellow-400 glow-amber uppercase">
                ECONOMIC WARFARE — {CONFLICT_DATE}
              </h1>
              <p className="text-[10px] text-zinc-500 mt-1 leading-relaxed max-w-lg">
                Energy markets, sanctions regime, global supply disruption, Iranian economic collapse, and financial market impact.
              </p>
            </div>
            <div className="on-air-badge inline-block bg-yellow-900/60 text-yellow-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-yellow-800/60 shrink-0">
              ● ECON LIVE
            </div>
          </div>
        </div>
        <div className="studio-accent-bar-amber" />
      </div>

      {/* What This War Costs Americans — cinematic */}
      <div className="video-feed-frame tac-card border-amber-900/60 bg-amber-950/10 p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-amber-500/60 font-bold tracking-[0.2em]">IMPACT LIVE</span>
        </div>
        <div className="tac-section-header relative z-[1]">
          <AlertTriangle size={11} className="text-amber-400 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]" />
          <span className="text-amber-300 tracking-widest glow-amber">WHAT THIS WAR COSTS AMERICANS — Day {CONFLICT_DAY}</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            { label: 'Extra at the pump',      value: '+$0.68/gal',  sub: 'vs. pre-conflict avg', color: 'text-amber-400 border-amber-800 bg-amber-950/20'  },
            { label: 'Grocery inflation add-on', value: '+1.4%',     sub: 'fuel → freight → shelf', color: 'text-orange-400 border-orange-800 bg-orange-950/20' },
            { label: '401(k) / market impact',  value: '−11%',       sub: 'S&P 500 since Day 1',  color: 'text-red-400 border-red-800 bg-red-950/20'          },
            { label: 'Taxpayer cost (war ops)',  value: '~$3B/wk',   sub: 'est. supplemental spend', color: 'text-violet-400 border-violet-800 bg-violet-950/20' },
            { label: 'US troops deployed',       value: '~45,000',   sub: 'to theater',            color: 'text-sky-400 border-sky-800 bg-sky-950/20'          },
          ].map((stat) => (
            <div key={stat.label} className={cn('border rounded p-3 text-center space-y-1', stat.color)}>
              <p className={cn('text-xl font-bold tracking-tight', stat.color.split(' ')[0])}>{stat.value}</p>
              <p className="text-[10px] font-semibold text-zinc-200 leading-tight">{stat.label}</p>
              <p className="text-[9px] text-zinc-500">{stat.sub}</p>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-600 border-t border-zinc-800/60 pt-2">
          Estimates based on IEA, CME, S&amp;P market data, and CBO emergency spending projections. All figures are approximate.
          See full breakdowns in the sections below.
        </p>
      </div>

      {/* COMPASS live economic cascade — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-yellow-500/60 font-bold tracking-[0.2em]">COMPASS</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <DollarSign size={11} className="text-yellow-400 animate-pulse drop-shadow-[0_0_4px_rgba(234,179,8,0.4)]" />
          <span className="text-yellow-400 tracking-widest glow-amber">COMPASS LIVE — Economic Cascade Model</span>
          <span className="ml-auto text-[9px] font-mono text-zinc-500 normal-case font-normal">auto-refresh 60s</span>
        </div>
        <CompassPanel />
      </div>

      {/* Live spot commodity prices — cinematic */}
      <div className="video-feed-frame tac-card border-orange-900/40 bg-orange-950/10 p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-orange-500/60 font-bold tracking-[0.2em]">NEXUS SPOT</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <Activity size={11} className="text-orange-400 animate-pulse drop-shadow-[0_0_4px_rgba(249,115,22,0.4)]" />
          <span className="text-orange-300 tracking-widest glow-amber">NEXUS SPOT MARKET — Live Commodity Quotes</span>
          <span className={cn(
            'ml-auto text-[9px] font-mono normal-case font-normal',
            spot.stale ? 'text-zinc-600' : 'text-emerald-600',
          )}>
            {spot.stale ? 'data unavailable' : 'yahoo finance'} · {new Date(spot.fetchedAt).toUTCString().slice(17, 25)}Z
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Brent Crude */}
          <div className="border border-orange-900/40 rounded p-3 space-y-1">
            <p className="text-[9px] text-zinc-500 tracking-widest uppercase">Brent Crude · BZ=F</p>
            <p className="text-2xl font-bold tabular-nums text-orange-300">
              {spot.stale ? <span className="text-zinc-500 text-base">UNAVAILABLE</span> : `$${spot.brentUsd.toFixed(2)}`}
              <span className="text-xs text-zinc-600 ml-1">USD/bbl</span>
            </p>
            {brentPremium !== null && (
              <p className="text-[9px] text-amber-500">
                +${brentPremium}/bbl war premium vs. pre-conflict $74
              </p>
            )}
            <div className="h-1 rounded-full bg-zinc-800 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-orange-700 to-red-500" style={{ width: `${Math.min(100, (spot.brentUsd / 150) * 100).toFixed(0)}%` }} />
            </div>
          </div>
          {/* WTI Crude */}
          <div className="border border-amber-900/40 rounded p-3 space-y-1">
            <p className="text-[9px] text-zinc-500 tracking-widest uppercase">WTI Crude · CL=F</p>
            <p className="text-2xl font-bold tabular-nums text-amber-300">
              {spot.stale ? <span className="text-zinc-500 text-base">UNAVAILABLE</span> : `$${spot.wtiUsd.toFixed(2)}`}
              <span className="text-xs text-zinc-600 ml-1">USD/bbl</span>
            </p>
            {wtiPremium !== null && (
              <p className="text-[9px] text-amber-500">
                +${wtiPremium}/bbl war premium vs. pre-conflict $71
              </p>
            )}
            <div className="h-1 rounded-full bg-zinc-800 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-amber-700 to-orange-500" style={{ width: `${Math.min(100, (spot.wtiUsd / 130) * 100).toFixed(0)}%` }} />
            </div>
          </div>
          {/* Natural Gas */}
          <div className="border border-sky-900/40 rounded p-3 space-y-1">
            <p className="text-[9px] text-zinc-500 tracking-widest uppercase">Nat Gas · NG=F</p>
            <p className="text-2xl font-bold tabular-nums text-sky-300">
              {spot.stale ? <span className="text-zinc-500 text-base">UNAVAILABLE</span> : `$${spot.ngUsdMmbtu.toFixed(2)}`}
              <span className="text-xs text-zinc-600 ml-1">USD/MMBtu</span>
            </p>
            <p className="text-[9px] text-zinc-600">HH hub · US domestic benchmark</p>
            <div className="h-1 rounded-full bg-zinc-800 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-sky-700 to-blue-500" style={{ width: `${Math.min(100, (spot.ngUsdMmbtu / 12) * 100).toFixed(0)}%` }} />
            </div>
          </div>
        </div>
        <p className="text-[9px] text-zinc-700 border-t border-zinc-800/60 pt-2">
          Live prices via Yahoo Finance public market data (BZ=F, CL=F, NG=F).
          {spot.stale && ' ⚠ Live fetch unavailable — real-time data cannot be displayed. Visit Yahoo Finance directly for current prices.'}
          {!spot.stale && ' Scenario projection prices in the table below are war-scenario models, NOT real market data.'}
        </p>
      </div>

      {/* Energy markets */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Zap size={11} className="text-orange-400" />
          <span>Scenario Commodity Prices — Day 1 through Day {CONFLICT_DAY} Baseline</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">AI-projected baseline — live COMPASS model above</span>
        </div>
        <div className="space-y-3">
          {ENERGY.map((e) => (
            <div key={e.commodity} className="border border-zinc-800 rounded p-3">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <TrendIcon trend={e.trend} />
                    <p className="text-sm font-bold text-zinc-100">{e.commodity}</p>
                    <span className={cn('text-xs font-bold tabular-nums', e.trend === 'UP' ? 'text-red-400' : 'text-emerald-400')}>
                      {e.trend === 'UP' ? '+' : ''}{e.pctChange}%
                    </span>
                  </div>
                  <p className="text-[9px] text-zinc-500">{e.driver}</p>
                </div>
                <div className="shrink-0 text-right space-y-0.5">
                  <p className="text-lg font-bold tabular-nums text-amber-400">{e.current.toLocaleString()} <span className="text-xs text-zinc-600">{e.unit}</span></p>
                  <p className="text-[9px] text-zinc-600">Pre-conflict: {e.preConflict} {e.unit}</p>
                  <p className="text-[9px] text-zinc-700">H: {e.dayHigh} / L: {e.dayLow}</p>
                  <a href={e.sourceUrl} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[9px] text-emerald-700 hover:text-emerald-400 transition-colors">
                    <ExternalLink size={8} />{e.source}
                  </a>
                </div>
              </div>
              {/* Sparkline row */}
              {ENERGY_SPARKLINES[e.commodity] && (
                <div className="flex items-end justify-between gap-4 pt-2 mt-1 border-t border-zinc-900/60">
                  <div>
                    <p className="text-[7px] text-zinc-700 mb-1 tracking-widest uppercase">Day 1 → Day {CONFLICT_DAY} Price Trajectory</p>
                    <MiniSparkline values={ENERGY_SPARKLINES[e.commodity]} />
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-[7px] text-zinc-700 tracking-widest uppercase mb-0.5">Pre-conflict → Current</p>
                    <p className="text-[9px] font-bold text-zinc-500 tabular-nums">{e.preConflict} → <span className="text-amber-400">{e.current.toLocaleString()}</span> {e.unit}</p>
                    <p className="text-[7px] text-red-500 mt-0.5">↗ +{e.pctChange}% over {CONFLICT_DAY} days</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Global supply impact */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Globe size={11} className="text-sky-400" />
          <span>Global Supply Disruption — Hormuz Vulnerability by Region</span>
        </div>
        <div className="space-y-2">
          {SUPPLY_IMPACT.sort((a, b) => b.vulnerability - a.vulnerability).map((s) => (
            <div key={s.region} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-zinc-300">{s.region}</span>
                <span className={cn('text-sm font-bold tabular-nums',
                  s.vulnerability >= 70 ? 'text-red-400' : s.vulnerability >= 40 ? 'text-amber-400' : 'text-yellow-400'
                )}>{s.vulnerability}%</span>
              </div>
              <div className="h-2 bg-zinc-800 rounded-sm overflow-hidden">
                <div
                  className={cn('h-full rounded-sm',
                    s.vulnerability >= 70 ? 'bg-red-600' : s.vulnerability >= 40 ? 'bg-amber-500' : 'bg-yellow-500'
                  )}
                  style={{ width: `${s.vulnerability}%` }}
                />
              </div>
              <p className="text-[9px] text-zinc-600">{s.note}</p>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-700 pt-1 border-t border-zinc-800">
          Vulnerability index = % of major energy imports transiting Hormuz + Gulf LNG dependency.{' '}
          <a href="https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints" target="_blank" rel="noopener noreferrer"
            className="text-emerald-700 hover:text-emerald-400 transition-colors inline-flex items-center gap-1"><ExternalLink size={8} /> EIA Chokepoints</a>
        </p>
      </div>

      {/* Maritime Shipping Disruption */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Globe size={11} className="text-cyan-400" />
          <span>Maritime Shipping Disruption — Hormuz &amp; Global Routes</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">Day {CONFLICT_DAY} · NAVCENT / IMO</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Left: key metrics */}
          <div className="space-y-0">
            {[
              { label: 'VLCCs Diverted (Cape of Good Hope)',   value: '47',     unit: 'vessels',          color: 'text-red-400',    delta: '+47 from baseline — rerouting adds 16 days transit' },
              { label: 'LNG Tankers Delayed (Qatar routes)',   value: '23',     unit: 'vessels',          color: 'text-amber-400',  delta: 'En-route demurrage accumulating — force majeure declared' },
              { label: 'Daily Shipping Revenue Loss',          value: '$2.1B',  unit: '/day',             color: 'text-red-400',    delta: 'Hormuz PARTIAL TRANSIT recovery underway; Bab el-Mandeb disruption ongoing' },
              { label: 'War Risk Premium (Hull & Cargo)',      value: '+3.5%',  unit: 'LOT basis',        color: 'text-red-400',    delta: 'Up from 0.05% pre-conflict — Lloyd\'s of London' },
              { label: 'Container Trade (Middle East route)',  value: '−31%',   unit: 'volume',           color: 'text-amber-500',  delta: 'MSC, Evergreen, COSCO route suspensions' },
              { label: 'P&I Insurance Withdrawn (IRISL)',      value: '47',     unit: 'vessels stranded', color: 'text-zinc-400',   delta: 'IMO emergency exclusion — 19 currently in foreign ports' },
            ].map(({ label, value, unit, color, delta }) => (
              <div key={label} className="flex items-start justify-between py-1.5 border-b border-zinc-800/50 last:border-0 gap-3">
                <div className="min-w-0">
                  <p className="text-[10px] font-bold text-zinc-300">{label}</p>
                  <p className="text-[8px] text-zinc-600">{delta}</p>
                </div>
                <div className="shrink-0 text-right">
                  <span className={cn('text-sm font-bold tabular-nums', color)}>{value}</span>
                  <span className="text-[8px] text-zinc-600 ml-1">{unit}</span>
                </div>
              </div>
            ))}
          </div>
          {/* Right: chokepoint status */}
          <div className="space-y-2">
            <p className="text-[9px] font-bold tracking-widest text-zinc-400 uppercase">Global Chokepoint Status</p>
            {[
              { name: 'Strait of Hormuz',    status: 'PARTIAL TRANSIT',  pctCleared: 78,  note: 'ZB-α 78% cleared — 7 VLCC transits D24–D27 under MCM escort (Op COPPER GAVEL)' },
              { name: 'Bab el-Mandeb',       status: 'CONTESTED',       pctCleared: 0,   note: 'Houthi ASM threat — commercial northbound suspended' },
              { name: 'Suez Canal',          status: 'OPEN / REDUCED',  pctCleared: 0,   note: '40% traffic reduction — war risk surcharge diverting ships' },
              { name: 'Strait of Malacca',   status: 'OPEN',            pctCleared: 0,   note: 'Normal ops — increased PLAN monitoring presence' },
              { name: 'Persian Gulf (Gulf)', status: 'RESTRICTED',      pctCleared: 0,   note: 'Military exclusion zones; commercial traffic prohibited' },
            ].map(({ name, status, pctCleared, note }) => (
              <div key={name} className="border border-zinc-800 rounded p-2.5 space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-bold text-zinc-200">{name}</span>
                  <span className={cn('text-[8px] font-bold tracking-widest shrink-0',
                    status === 'CLOSED'          ? 'text-red-400'     :
                    status === 'CONTESTED'        ? 'text-amber-400'   :
                    status === 'RESTRICTED'       ? 'text-orange-400'  :
                    status === 'PARTIAL TRANSIT'  ? 'text-cyan-400'    :
                    status === 'OPEN / REDUCED'   ? 'text-yellow-400'  : 'text-emerald-400'
                  )}>{status}</span>
                </div>
                {pctCleared > 0 && (
                  <div className="space-y-0.5">
                    <p className="text-[7px] text-zinc-700 tracking-widest">MCM CLEARANCE PROGRESS</p>
                    <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full bg-teal-700 rounded-full" style={{ width: `${pctCleared}%` }} />
                    </div>
                    <p className="text-[7px] text-teal-600">{pctCleared}% of estimated mine barrier cleared — Op COPPER GAVEL</p>
                  </div>
                )}
                <p className="text-[9px] text-zinc-500">{note}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sanctions regime */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <ShieldAlert size={11} className="text-amber-400" />
          <span>Sanctions Regime — {SANCTIONS.filter(s => s.status === 'ACTIVE').length} Active Measures</span>
        </div>
        <div className="space-y-2">
          {SANCTIONS.map((s) => (
            <div key={s.regime} className="border border-zinc-800 rounded p-3 space-y-1.5">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-xs font-bold text-zinc-100">{s.regime}</p>
                    <ImpactBadge impact={s.impact} />
                    <StatusDot status={s.status} />
                  </div>
                  <p className="text-[9px] text-zinc-500">Authority: {s.authority} · Effective: {s.effective}</p>
                  <p className="text-[9px] text-zinc-600">Target: {s.target}</p>
                </div>
              </div>
              <p className="text-[10px] text-zinc-400 leading-relaxed">{s.notes}</p>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-700">
          Sources:{' '}
          <a href="https://ofac.treasury.gov/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 inline-flex items-center gap-1 transition-colors"><ExternalLink size={8} /> OFAC</a>
          {' · '}
          <a href="https://eur-lex.europa.eu/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 inline-flex items-center gap-1 transition-colors"><ExternalLink size={8} /> EUR-Lex</a>
        </p>
      </div>

      {/* Iranian economy — cinematic */}
      <div className="tac-card-critical p-4 space-y-3 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none z-0" style={{background: 'linear-gradient(135deg, rgba(239,68,68,0.04), transparent 60%)'}} />
        <div className="tac-section-header mb-1 relative z-[1]">
          <AlertTriangle size={11} className="text-red-400 drop-shadow-[0_0_4px_rgba(239,68,68,0.5)]" />
          <span className="text-red-400 glow-red">Iranian Economic Collapse — Day {CONFLICT_DAY} Indicators</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">Sources: IMF, World Bank, Reuters, FX data</span>
        </div>
        <div className="space-y-2">
          {IRAN_ECONOMIC.map((item) => (
            <div key={item.label} className="flex items-center justify-between py-2 border-b border-zinc-800/60 last:border-0 gap-3">
              <div className="min-w-0">
                <p className="text-[10px] font-bold text-zinc-300">{item.label}</p>
                <p className="text-[9px] text-zinc-600">Baseline: {item.vs}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={cn('text-base font-bold tabular-nums', item.color)}>{item.value}</span>
              </div>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-700 pt-1 border-t border-zinc-800">
          Iranian economic data is scenario extrapolation from IMF Article IV 2025 baseline.{' '}
          <a href="https://www.imf.org/en/Countries/IRN" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 inline-flex items-center gap-1 transition-colors"><ExternalLink size={8} /> IMF Iran</a>
          {' · '}
          <a href="https://www.reuters.com/markets/currencies/iran-rial-falls-record-low-amid-geopolitical-tensions/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 inline-flex items-center gap-1 transition-colors"><ExternalLink size={8} /> Reuters Rial</a>
        </p>
      </div>

      {/* Global financial markets — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-purple-500/60 font-bold tracking-[0.2em]">MARKETS</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <BarChart3 size={11} className="text-purple-400 drop-shadow-[0_0_4px_rgba(168,85,247,0.4)]" />
          <span className="text-purple-400">Global Financial Markets — Day {CONFLICT_DAY} Close</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {MARKETS.map((m) => (
            <div key={m.market} className="border border-zinc-800 rounded p-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <TrendIcon trend={m.trend} />
                  <p className="text-xs font-bold text-zinc-200">{m.market}</p>
                </div>
                <p className="text-[9px] text-zinc-500 leading-relaxed mt-0.5">{m.note}</p>
              </div>
              <span className={cn('text-base font-bold tabular-nums shrink-0',
                m.trend === 'DOWN' ? 'text-red-400' : 'text-emerald-400'
              )}>
                {m.pctChange > 0 ? '+' : ''}{m.pctChange}%
              </span>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-700 pt-1 border-t border-zinc-800">
          Market data is AI-synthesized analysis from public economic models and historical conflict analogues (2022 Russia/Ukraine, 1990 Gulf War, 2019 Saudi Aramco attack).{' '}
          <a href="https://www.bloomberg.com/markets" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 inline-flex items-center gap-1 transition-colors"><ExternalLink size={8} /> Bloomberg</a>
          {' · '}
          <a href="https://finance.yahoo.com/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 inline-flex items-center gap-1 transition-colors"><ExternalLink size={8} /> Yahoo Finance</a>
        </p>
      </div>

      {/* Removed duplicate CompassPanel - now rendered at top */}

    </div>
  )
}
