'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { RefreshCw, Shield, Activity } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { ThreatBadge } from '@/components/ThreatMeter'
import { getWarStats } from '@/lib/war-stats'
import { WatchfloorModeSelector } from '@/components/WatchfloorMode'

/** Conflict start: 01 MAR 2026 00:00 UTC */
const CONFLICT_START_UTC = Date.UTC(2026, 2, 1)

function useConflictDay() {
  // Lazy initializer so server and client both compute the real day (no "Day 1" flash)
  const [day, setDay] = useState<number>(() =>
    Math.max(1, Math.floor((Date.now() - CONFLICT_START_UTC) / 86_400_000) + 1)
  )
  useEffect(() => {
    const calc = () =>
      setDay(Math.max(1, Math.floor((Date.now() - CONFLICT_START_UTC) / 86_400_000) + 1))
    // Recalculate every minute so it rolls over at midnight UTC
    const id = setInterval(calc, 60_000)
    return () => clearInterval(id)
  }, [])
  return day
}

/** Live clock — updates every second, client-side only */
function LiveClock() {
  const [time, setTime] = useState<string>('')

  useEffect(() => {
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString('en-US', {
          hour12: false,
          timeZone: 'UTC',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }) + ' UTC'
      )
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    // suppressHydrationWarning: server renders placeholder; client immediately
    // overwrites with real time once useEffect fires — no mismatch error
    <span suppressHydrationWarning className="text-xs text-emerald-400 tracking-widest tabular-nums glow-green">
      {time || '──:──:── UTC'}
    </span>
  )
}

/** Live accuracy beacon — polls /api/intel/accuracy every 5 min */
function AccuracyBeacon() {
  const [pct, setPct]       = useState<number | null>(null)
  const [grade, setGrade]   = useState<string | null>(null)
  const [pulse, setPulse]   = useState(false)

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/accuracy', { cache: 'no-store' })
      if (!res.ok) return
      const data = await res.json() as { accuracyPct?: number; report?: { gradeLetter?: string } }
      if (typeof data.accuracyPct === 'number') {
        setPct(data.accuracyPct)
        setGrade(data.report?.gradeLetter ?? null)
        setPulse(true)
        setTimeout(() => setPulse(false), 1200)
      }
    } catch { /* silent */ }
  }, [])

  useSmartPoll(fetch_, 5 * 60_000)

  if (pct === null) return null

  const color =
    pct >= 85 ? 'text-emerald-400 glow-green'  :
    pct >= 70 ? 'text-yellow-400'               :
    pct >= 50 ? 'text-amber-400 glow-amber'     : 'text-red-400'

  return (
    <div
      className={`flex items-center gap-1 border border-zinc-800 rounded px-2 py-1 bg-zinc-900/60 ${pulse ? 'border-emerald-800' : ''} transition-colors`}
      title="Platform accuracy score — click for details"
    >
      <Activity size={10} className={color} />
      <span className={`text-[10px] font-mono font-bold tabular-nums ${color}`}>
        {pct}%
      </span>
      {grade && (
        <span className="text-[9px] text-zinc-600 font-mono">{grade}</span>
      )}
    </div>
  )
}

/** Compact inline stat for the hero strip */
function HeroStat({
  icon, label, value, color, pulse,
}: {
  icon: string
  label: string
  value: string
  color: string
  pulse?: boolean
}) {
  return (
    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-zinc-900/40 border border-zinc-800/30">
      <span className="text-sm leading-none">{icon}</span>
      <div className="flex flex-col">
        <span className="text-[8px] font-mono text-zinc-600 tracking-widest uppercase leading-none">{label}</span>
        <span className={`text-[11px] font-bold font-mono tracking-wider leading-tight ${color} ${pulse ? 'animate-pulse' : ''}`}>{value}</span>
      </div>
    </div>
  )
}

export function TopBar() {
  const router = useRouter()
  const [spinning, setSpinning] = useState(false)
  const day = useConflictDay()
  const war = getWarStats(day)

  const threatLevel =
    war.fpconLevel === 'DELTA' || war.fpconLevel === 'CHARLIE'
      ? 'SEVERE'
      : war.fpconLevel === 'BRAVO'
      ? 'HIGH'
      : 'ELEVATED'

  const handleRefresh = useCallback(() => {
    setSpinning(true)
    router.refresh()
    setTimeout(() => setSpinning(false), 800)
  }, [router])

  return (
    <header className="flex flex-col gap-0 border-b border-zinc-800/50 bg-zinc-950/95 backdrop-blur-xl shrink-0">
      {/* Row 1: title + controls */}
      <div className="flex items-center justify-between gap-4 px-4 py-3 md:px-5">
        {/* Left: Operation title + day badge — offset for mobile hamburger */}
        <div className="flex items-center gap-3 min-w-0 pl-12 md:pl-0">
          <Shield size={16} className="text-emerald-400 shrink-0" />
          <h1 className="text-sm font-bold tracking-widest text-emerald-300 uppercase glow-green truncate hidden sm:block">
            Operation Epic Fury
          </h1>
          <h1 className="text-xs font-bold tracking-wider text-emerald-300 uppercase glow-green truncate sm:hidden">
            EPIC FURY
          </h1>
          {/* Day counter */}
          <div className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 bg-emerald-950/40 border border-emerald-800/40" suppressHydrationWarning>
            <span className="text-[9px] font-mono text-emerald-600 tracking-widest uppercase">DAY</span>
            <span className="text-base font-black tabular-nums text-emerald-300 glow-green leading-none">{day}</span>
          </div>
        </div>

        {/* Right: controls — all with 44px min touch targets */}
        <div className="flex items-center gap-2 shrink-0">
          <WatchfloorModeSelector compact />
          <ThreatBadge level={threatLevel} />
          <AccuracyBeacon />
          <LiveClock />
          <button
            onClick={handleRefresh}
            title="Refresh data"
            aria-label="Refresh dashboard data"
            className="flex items-center justify-center w-10 h-10 rounded-lg border border-zinc-800/50 text-zinc-500 hover:text-emerald-400 hover:border-emerald-700/50 hover:bg-emerald-950/30 active:scale-95 transition-all duration-150"
          >
            <RefreshCw
              size={15}
              className={spinning ? 'animate-spin text-emerald-400' : ''}
            />
          </button>
        </div>
      </div>

      {/* Row 2: Hero strip — live indicators in card-style chips */}
      <div className="flex items-center gap-2 px-4 md:px-5 pb-2.5 overflow-x-auto scrollbar-none">
        <HeroStat icon="🛢" label="BRENT" value={`$${war.brentUsd}/bbl`} color="text-yellow-400" />
        <HeroStat icon="☮" label="CEASE 72H" value={`${war.compassCeasefire}%`} color="text-blue-400" />
        <HeroStat icon="⚠" label="HORMUZ" value={war.hormuzFullyOpen ? 'OPEN' : war.zbAlphaPct >= 90 ? 'OPEN TRANSIT' : 'PARTIAL'} color="text-cyan-400" />
        <HeroStat icon="🛡" label="FPCON" value={war.fpconLevel} color={war.fpconLevel === 'ALPHA' ? 'text-emerald-400' : 'text-red-400'} pulse={war.fpconLevel !== 'ALPHA'} />
      </div>
    </header>
  )
}

// ── Persistent theater-status ribbon ─────────────────────────────────────────
// Thin strip rendered just below the TopBar on every dashboard page.
// Values are AI-synthesized real-time assessments reflecting Op Epic Fury Day 28 state.

interface RibbonItem {
  label: string
  value: string
  color: string        // Tailwind text colour class
  pulse?: boolean      // animate-pulse on the status dot
}

function buildRibbonItems(day: number): RibbonItem[] {
  const war = getWarStats(day)
  const hormuzStatus =
    war.hormuzFullyOpen ? 'FULLY OPEN' : war.zbAlphaPct >= 90 ? 'OPEN TRANSIT' : 'PARTIAL TRANSIT'
  const fpconColor = war.fpconLevel === 'ALPHA' ? 'text-emerald-400' : 'text-red-400'

  return [
    { label: 'HORMUZ', value: hormuzStatus, color: 'text-cyan-400' },
    { label: 'COMPASS', value: `${war.compassCeasefire}% / 72h`, color: 'text-blue-400', pulse: war.compassCeasefire < 70 },
    { label: 'NUCLEAR', value: `${war.nuclearDegradedPct}% DEGRADED`, color: 'text-amber-400' },
    { label: 'BM STOCK', value: `~${war.bmStockPct}%`, color: war.bmStockPct <= 12 ? 'text-emerald-400' : 'text-amber-400' },
    { label: 'MCM ZB-A', value: `${war.zbAlphaPct}% CLEARED`, color: 'text-cyan-400' },
    { label: 'TBMD INT', value: `~${war.tbmdInterceptPct}%`, color: 'text-emerald-400' },
    { label: 'BRENT', value: `$${war.brentUsd}/bbl`, color: 'text-yellow-400' },
    { label: 'SORTIES', value: war.sortiesLabel, color: 'text-zinc-300' },
    { label: 'FPCON', value: war.fpconLevel, color: fpconColor, pulse: war.fpconLevel !== 'ALPHA' },
  ]
}

const DOT_COLOR: Record<string, string> = {
  'text-red-400':     'bg-red-500',
  'text-amber-400':   'bg-amber-500',
  'text-emerald-400': 'bg-emerald-500',
  'text-cyan-400':    'bg-cyan-400',
  'text-purple-400':  'bg-purple-500',
  'text-yellow-400':  'bg-yellow-400',
}

export function StatusRibbon() {
  const day = useConflictDay()
  const ribbonItems = buildRibbonItems(day)

  return (
    <div className="status-ribbon shrink-0" aria-label="Theater status ribbon">
      {ribbonItems.map((item) => (
        <div key={item.label} className="status-ribbon-item group">
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${DOT_COLOR[item.color] ?? 'bg-zinc-500'} ${item.pulse ? 'animate-pulse' : ''} transition-shadow group-hover:shadow-sm`}
            style={item.pulse ? undefined : { boxShadow: `0 0 4px ${item.color.includes('red') ? 'rgba(239,68,68,0.3)' : item.color.includes('emerald') ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.2)'}` }}
          />
          <span className="text-zinc-600 group-hover:text-zinc-400 transition-colors">{item.label}:</span>
          <span className={`${item.color} transition-all`}>{item.value}</span>
        </div>
      ))}
    </div>
  )
}
