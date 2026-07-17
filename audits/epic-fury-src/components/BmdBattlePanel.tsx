'use client'

/**
 * BmdBattlePanel — Ballistic Missile Defense Battle Tracking
 *
 * Live assessment of THAAD / PAC-3 / SM-3 battery status, barrage timeline,
 * intercept history, and ORACLE-9 BM threat model.
 *
 * Doctrine source: 7 years BMDS / Aegis BMD — Op Epic Fury Day compute.
 */

import { useState } from 'react'
import { Shield, Target, AlertTriangle, CheckCircle2, Zap, TrendingDown } from 'lucide-react'
import { getWarStats } from '@/lib/war-stats'
import { getConflictDay } from '@/lib/conflict-day'

// ── Static barrage history (ORACLE-9 confirmed) ──────────────────────────────
const BARRAGES = [
  {
    day: 1,
    label: 'BARRAGE-1 OP-ONSET',
    launched: 47,
    intercepted: 44,
    leakers: 3,
    systems: 'THAAD α / PAC-3 / SM-3 IIA',
    note: 'Opening salvo — Shahab-3, Ghadr variants targeting Al Udeid, CENTCOM',
  },
  {
    day: 3,
    label: 'BARRAGE-2 RETALIATORY',
    launched: 38,
    intercepted: 35,
    leakers: 3,
    systems: 'THAAD α,β / PAC-3',
    note: 'Qom-directed strike response — Emad & Khorramshahr-2 mix',
  },
  {
    day: 7,
    label: 'BARRAGE-3 SATURATION',
    launched: 65,
    intercepted: 58,
    leakers: 7,
    systems: 'THAAD α,β / PAC-3 / SM-3 IIA × 2 ships',
    note: 'Mass-raid saturation attempt — heaviest engagement to date',
  },
  {
    day: 12,
    label: 'BARRAGE-4 PRECISION',
    launched: 52,
    intercepted: 48,
    leakers: 4,
    systems: 'THAAD α,β / PAC-3 / GBI (terminal-phase assist)',
    note: 'IRGCAF strike on Carrier Strike Group 12 — SM-3 primary',
  },
  {
    day: 17,
    label: 'BARRAGE-5 APEX',
    launched: 71,
    intercepted: 61,
    leakers: 10,
    systems: 'All BMDS layers — THAAD α,β,γ / PAC-3 / SM-3 / Arrow-3',
    note: 'Largest barrage — 71 BMs in 4h — Khorramshahr-4 variant debut',
  },
  {
    day: 20,
    label: 'BARRAGE-6 DEGRADED',
    launched: 29,
    intercepted: 28,
    leakers: 1,
    systems: 'THAAD β / PAC-3 / SM-3 IIA',
    note: 'Final Iranian barrage — depleted inventory — 97% intercept',
  },
]

// ── Battery status model (Day-parameterized) ──────────────────────────────────
type ReadinessStatus = 'OPERATIONAL' | 'RELOADING' | 'DEPLETED' | 'REDEPLOYED'

interface Battery {
  id: string
  name: string
  type: 'THAAD' | 'PAC-3 MSE' | 'SM-3 IIA'
  location: string
  status: ReadinessStatus
  interceptorsRemaining: number
  interceptorsMax: number
  intercepts: number
  color: string
}

function getBatteries(day: number): Battery[] {
  // Inventory depletes across barrages, restocked via CRAF/LOGAIR
  const thaadAlpha = Math.max(4, 24 - Math.floor(day * 0.35))
  const thaadBravo = Math.max(2, 24 - Math.floor(day * 0.42))
  const thaadCharlie = Math.max(6, 24 - Math.floor(day * 0.28))
  const pac3Battery1 = Math.max(3, 48 - Math.floor(day * 0.9))
  const pac3Battery2 = Math.max(1, 48 - Math.floor(day * 1.1))
  const sm3Cole      = Math.max(4, 22 - Math.floor(day * 0.38))
  const sm3Roosevelt = Math.max(8, 22 - Math.floor(day * 0.32))

  return [
    {
      id: 'thaad-alpha',
      name: 'THAAD Bty ALPHA',
      type: 'THAAD',
      location: 'Al Udeid AB, Qatar',
      status: thaadAlpha > 6 ? 'OPERATIONAL' : thaadAlpha > 2 ? 'RELOADING' : 'DEPLETED',
      interceptorsRemaining: thaadAlpha,
      interceptorsMax: 24,
      intercepts: 49,
      color: 'emerald',
    },
    {
      id: 'thaad-bravo',
      name: 'THAAD Bty BRAVO',
      type: 'THAAD',
      location: 'Ayn al-Asad AB, Iraq',
      status: thaadBravo > 6 ? 'OPERATIONAL' : thaadBravo > 2 ? 'RELOADING' : 'DEPLETED',
      interceptorsRemaining: thaadBravo,
      interceptorsMax: 24,
      intercepts: 44,
      color: 'emerald',
    },
    {
      id: 'thaad-charlie',
      name: 'THAAD Bty CHARLIE',
      type: 'THAAD',
      location: 'Prince Sultan AB, KSA',
      status: day >= 43 ? 'REDEPLOYED' : thaadCharlie > 6 ? 'OPERATIONAL' : 'RELOADING',
      interceptorsRemaining: thaadCharlie,
      interceptorsMax: 24,
      intercepts: 36,
      color: 'sky',
    },
    {
      id: 'pac3-1',
      name: 'PAC-3 1/43 ADA',
      type: 'PAC-3 MSE',
      location: 'Camp Arifjan, Kuwait',
      status: pac3Battery1 > 8 ? 'OPERATIONAL' : pac3Battery1 > 3 ? 'RELOADING' : 'DEPLETED',
      interceptorsRemaining: pac3Battery1,
      interceptorsMax: 48,
      intercepts: 61,
      color: 'amber',
    },
    {
      id: 'pac3-2',
      name: 'PAC-3 3/43 ADA',
      type: 'PAC-3 MSE',
      location: 'NSA Bahrain',
      status: pac3Battery2 > 8 ? 'OPERATIONAL' : pac3Battery2 > 3 ? 'RELOADING' : 'DEPLETED',
      interceptorsRemaining: pac3Battery2,
      interceptorsMax: 48,
      intercepts: 53,
      color: 'amber',
    },
    {
      id: 'sm3-cole',
      name: 'USS Cole DDG-67',
      type: 'SM-3 IIA',
      location: 'Arabian Sea / Gulf of Oman',
      status: sm3Cole > 6 ? 'OPERATIONAL' : sm3Cole > 3 ? 'RELOADING' : 'DEPLETED',
      interceptorsRemaining: sm3Cole,
      interceptorsMax: 22,
      intercepts: 28,
      color: 'blue',
    },
    {
      id: 'sm3-roosevelt',
      name: 'USS Dwight D Eisenhower CVN-69',
      type: 'SM-3 IIA',
      location: 'North Arabian Sea / CSG-12',
      status: sm3Roosevelt > 6 ? 'OPERATIONAL' : sm3Roosevelt > 3 ? 'RELOADING' : 'DEPLETED',
      interceptorsRemaining: sm3Roosevelt,
      interceptorsMax: 22,
      intercepts: 32,
      color: 'blue',
    },
  ]
}

const STATUS_COLOR: Record<ReadinessStatus, string> = {
  OPERATIONAL: 'text-emerald-400',
  RELOADING:   'text-yellow-400',
  DEPLETED:    'text-red-400',
  REDEPLOYED:  'text-zinc-500',
}
const STATUS_DOT: Record<ReadinessStatus, string> = {
  OPERATIONAL: 'bg-emerald-500',
  RELOADING:   'bg-yellow-400 animate-pulse',
  DEPLETED:    'bg-red-500',
  REDEPLOYED:  'bg-zinc-600',
}

// ── Battery readiness bar ─────────────────────────────────────────────────────
function BatteryCard({ b }: { b: Battery }) {
  const pct = Math.round((b.interceptorsRemaining / b.interceptorsMax) * 100)
  const barColor =
    pct >= 50 ? 'bg-emerald-500' :
    pct >= 25 ? 'bg-yellow-400' : 'bg-red-500'

  return (
    <div className="tac-card rounded-sm p-3 space-y-2 border border-zinc-800 hover:border-zinc-600 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[b.status]}`} />
          <span className="text-[9px] font-mono font-bold text-zinc-200 tracking-widest uppercase truncate">{b.name}</span>
        </div>
        <span className={`text-[8px] font-mono font-bold tracking-widest uppercase shrink-0 ${STATUS_COLOR[b.status]}`}>
          {b.status}
        </span>
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest">{b.type}</span>
          <span className="text-[8px] font-mono text-zinc-500">{b.interceptorsRemaining}/{b.interceptorsMax} RDY</span>
        </div>
        <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[8px] text-zinc-600 font-mono truncate">{b.location}</span>
        <span className="text-[8px] font-mono text-zinc-500 shrink-0">{b.intercepts} KILLs</span>
      </div>
    </div>
  )
}

// ── Barrage timeline row ──────────────────────────────────────────────────────
function BarrageRow({ b }: { b: typeof BARRAGES[0] }) {
  const [open, setOpen] = useState(false)
  const rate = Math.round((b.intercepted / b.launched) * 100)
  const barWidth = rate
  const barColor =
    rate >= 95 ? 'bg-emerald-500' :
    rate >= 88 ? 'bg-emerald-600' :
    rate >= 80 ? 'bg-yellow-500' : 'bg-amber-500'

  return (
    <div
      className="border border-zinc-800 rounded-sm overflow-hidden hover:border-zinc-700 transition-all cursor-pointer"
      onClick={() => setOpen(o => !o)}
    >
      <div className="flex items-center gap-3 px-3 py-2">
        {/* Day badge */}
        <div className="shrink-0 w-8 text-center">
          <span className="text-[8px] font-mono text-zinc-600 block leading-none">D{b.day}</span>
        </div>

        {/* Label */}
        <div className="flex-1 min-w-0">
          <span className="text-[9px] font-mono font-bold text-zinc-300 tracking-wider">{b.label}</span>
        </div>

        {/* Intercept rate + bar */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-20 h-1.5 bg-zinc-900 rounded-full overflow-hidden hidden sm:block">
            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${barWidth}%` }} />
          </div>
          <span className={`text-[10px] font-mono font-bold tabular-nums ${rate >= 90 ? 'text-emerald-400' : 'text-yellow-400'}`}>
            {rate}%
          </span>
        </div>

        {/* Counts */}
        <div className="flex items-center gap-2 shrink-0 text-[8px] font-mono">
          <span className="text-red-500">{b.launched}↑</span>
          <span className="text-emerald-400">{b.intercepted}✓</span>
          <span className="text-amber-500">{b.leakers}⚡</span>
        </div>
      </div>

      {open && (
        <div className="px-4 py-2 bg-zinc-900/50 border-t border-zinc-800/60 space-y-1">
          <p className="text-[8px] font-mono text-zinc-500 leading-relaxed">{b.note}</p>
          <p className="text-[8px] font-mono text-zinc-600 uppercase tracking-widest">SYSTEMS: {b.systems}</p>
        </div>
      )}
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────
export function BmdBattlePanel() {
  const day = getConflictDay()
  const ws = getWarStats(day)
  const batteries = getBatteries(day)

  const totalLaunched   = BARRAGES.reduce((a, b) => a + b.launched,    0)
  const totalIntercepted = BARRAGES.reduce((a, b) => a + b.intercepted, 0)
  const totalLeakers    = BARRAGES.reduce((a, b) => a + b.leakers,     0)
  const overallRate     = Math.round((totalIntercepted / totalLaunched) * 100)
  const activeBatteries = batteries.filter(b => b.status === 'OPERATIONAL').length

  return (
    <div className="tac-card rounded-sm border border-zinc-800 space-y-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800/60 bg-zinc-950/40">
        <div className="flex items-center gap-2">
          <Shield size={13} className="text-emerald-400 shrink-0" />
          <span className="text-[9px] font-mono font-bold tracking-[0.25em] text-emerald-300 uppercase">
            BMDS BATTLE TRACKER — ORACLE-9
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[8px] font-mono text-zinc-600 tracking-widest uppercase">TBMD INT</span>
          <span className="text-[10px] font-mono font-bold text-emerald-400">~{ws.tbmdInterceptPct}%</span>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-zinc-800/30">
        {[
          {
            label: 'TOTAL LAUNCHES',
            value: totalLaunched.toString(),
            icon: Target,
            color: 'text-red-400',
            sub: `6 barrages D1–D${BARRAGES[BARRAGES.length - 1].day}`,
          },
          {
            label: 'INTERCEPTED',
            value: totalIntercepted.toString(),
            icon: CheckCircle2,
            color: 'text-emerald-400',
            sub: `${overallRate}% overall rate`,
          },
          {
            label: 'LEAKERS',
            value: totalLeakers.toString(),
            icon: AlertTriangle,
            color: 'text-amber-400',
            sub: 'penetrated BMDS envelope',
          },
          {
            label: 'BATTERIES READY',
            value: `${activeBatteries}/7`,
            icon: Zap,
            color: 'text-blue-400',
            sub: 'THAAD + PAC-3 + SM-3',
          },
        ].map(({ label, value, icon: Icon, color, sub }) => (
          <div key={label} className="px-3 py-3 bg-zinc-950/20 space-y-1">
            <div className="flex items-center gap-1.5">
              <Icon size={10} className={color} />
              <span className="text-[7px] font-mono text-zinc-600 tracking-widest uppercase">{label}</span>
            </div>
            <span className={`text-xl font-black font-mono tabular-nums ${color} leading-none block`}>{value}</span>
            <span className="text-[8px] font-mono text-zinc-600">{sub}</span>
          </div>
        ))}
      </div>

      {/* ZULU-14 TEL kill banner */}
      <div className="flex items-center gap-3 px-4 py-2 bg-emerald-950/20 border-y border-emerald-900/30">
        <CheckCircle2 size={12} className="text-emerald-400 shrink-0" />
        <span className="text-[8px] font-mono text-emerald-400 tracking-widest uppercase">
          ZULU-14 TEL — DESTROYED D38 B-1B STRIKE — IRGCAF LAST MOBILE LAUNCHER ELIMINATED — BM RECONSTITUTION 6–12 MONTHS
        </span>
        <TrendingDown size={11} className="text-emerald-400 shrink-0 ml-auto" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4">
        {/* Battery status grid */}
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[8px] font-mono font-bold text-zinc-500 tracking-widest uppercase">BATTERY STATUS — ALL LAYERS</p>
            <span className="text-[7px] font-mono text-zinc-700">RDY = READY ROUND COUNT</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-2">
            {batteries.map(b => <BatteryCard key={b.id} b={b} />)}
          </div>
        </div>

        {/* Barrage timeline */}
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[8px] font-mono font-bold text-zinc-500 tracking-widest uppercase">BARRAGE TIMELINE — TAP FOR DETAIL</p>
            <span className="text-[7px] font-mono text-zinc-700">↑ FIRED · ✓ KILLED · ⚡ LEAKER</span>
          </div>
          <div className="space-y-1">
            {BARRAGES.map(b => <BarrageRow key={b.day} b={b} />)}
          </div>

          {/* ORACLE-9 assessment */}
          <div className="border border-zinc-800/60 rounded-sm p-3 mt-2 space-y-1.5 bg-zinc-950/30">
            <div className="flex items-center gap-1.5">
              <AlertTriangle size={10} className="text-amber-400" />
              <span className="text-[8px] font-mono font-bold text-amber-400 tracking-widest uppercase">ORACLE-9 BM THREAT MODEL</span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {[
                { label: 'NEXT BARRAGE RISK', value: '≤2%', color: 'text-emerald-400' },
                { label: 'BM STOCK REMAINING', value: `~${ws.bmStockPct}%`, color: ws.bmStockPct <= 5 ? 'text-emerald-400' : 'text-amber-400' },
                { label: 'IRGCAF SORTIES', value: ws.daysSinceIRGCAFSortie !== null ? `ZERO (D${21}+)` : 'ACTIVE', color: 'text-emerald-400' },
                { label: 'MRBM READY EST', value: '3–7', color: 'text-amber-400' },
                { label: 'RECONSTITUTION', value: '6–12 MONTHS', color: 'text-zinc-400' },
                { label: 'TBMD INT RATE', value: `~${ws.tbmdInterceptPct}%`, color: 'text-emerald-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex items-center justify-between gap-1">
                  <span className="text-[7px] font-mono text-zinc-600 uppercase tracking-widest">{label}</span>
                  <span className={`text-[8px] font-mono font-bold ${color}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer doctrine strip */}
      <div className="px-4 py-2 border-t border-zinc-800/60 bg-zinc-950/30 flex items-center justify-between">
        <span className="text-[7px] font-mono text-zinc-700 uppercase tracking-widest">
          BMDS DOCTRINE: LAYERED DEFENSE — THAAD EXOATMOSPHERIC + PAC-3 TERMINAL + SM-3 MIDCOURSE
        </span>
        <span className="text-[7px] font-mono text-zinc-700 uppercase tracking-widest">
          D{day} / FPCON {ws.fpconLevel}
        </span>
      </div>
    </div>
  )
}
