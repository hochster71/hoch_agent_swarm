/**
 * components/GovernorPanel.tsx — Platform Governor Status Card
 *
 * Displays the 6-layer Governor state, KG stats, escalations,
 * and DGM mutation history. Includes a manual GOVERN trigger button.
 */

'use client'

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Brain, GitBranch, ShieldCheck, FlaskConical,
  Layers, AlertTriangle,
  Zap, ChevronDown, ChevronRight, Film, DollarSign,
} from 'lucide-react'
import type { GovernorReport } from '@/lib/governor'
import type { KGStats } from '@/lib/kg-engine'
import type { VisualStats } from '@/lib/visual-engine'
import type { RevenueStats } from '@/lib/revenue-engine'

interface GovernorCycleSummary {
  id:                  string
  conflict_day:        number
  trigger:             string
  layer_reached:       number
  entities_extracted:  number
  claims_verified:     number
  mutations_applied:   number
  duration_ms:         number
  error:               string | null
  created_at:          string
}

interface GovernorAPIResponse {
  cycles:      GovernorCycleSummary[]
  kgStats:     KGStats
  visualStats: VisualStats
  revenueStats: RevenueStats
  summary: {
    cyclesReturned:         number
    avgLayersCompleted:     number
    totalEntitiesExtracted: number
    totalClaimsVerified:    number
    totalMutationsApplied:  number
    avgDurationMs:          number
  }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const LAYER_NAMES = ['', 'Perception', 'Reasoning', 'Generation', 'Visual', 'Healing', 'Expansion', 'DGM', 'Revenue']
const LAYER_ICONS = [null, Brain, GitBranch, Zap, Film, ShieldCheck, Layers, FlaskConical, DollarSign]

function LayerBadge({ n, reached }: { n: number; reached: number }) {
  const Icon = LAYER_ICONS[n] ?? Brain
  const state = n <= reached ? 'done' : 'pending'
  return (
    <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-bold border ${
      state === 'done'
        ? 'bg-emerald-950/25 border-emerald-800/40 text-emerald-400'
        : 'bg-zinc-900/40 border-zinc-800/30 text-zinc-600'
    }`}>
      <Icon className="w-2 h-2" />
      L{n}
    </div>
  )
}

export default function GovernorPanel() {
  const [data, setData]     = useState<GovernorAPIResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [lastReport, setLastReport] = useState<GovernorReport | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading]   = useState(true)

  const fetchState = useCallback(async () => {
    try {
      const res = await fetch('/api/governor?limit=5', { cache: 'no-store' })
      if (res.ok) setData(await res.json() as GovernorAPIResponse)
    } catch { /* non-fatal */ } finally {
      setLoading(false)
    }
  }, [])

  const triggerGovernor = useCallback(async () => {
    if (running) return
    setRunning(true)
    try {
      const res = await fetch('/api/governor/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
      })
      if (res.ok) {
        const report = await res.json() as GovernorReport
        setLastReport(report)
        await fetchState()
      }
    } catch { /* non-fatal */ } finally {
      setRunning(false)
    }
  }, [running, fetchState])

  useSmartPoll(fetchState, 60_000)

  const kg      = data?.kgStats
  const vs      = data?.visualStats
  const rv      = data?.revenueStats
  const last    = data?.cycles?.[0]
  const summary = data?.summary

  const accuracyPct = kg && kg.totalClaims > 0
    ? Math.round((kg.verifiedClaims / kg.totalClaims) * 100)
    : null

  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/60 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Brain className="w-4 h-4 text-violet-400" />
        <span className="tac-label text-violet-300 tracking-widest text-[10px]">PLATFORM GOVERNOR</span>
        {last && (
          <span className={`ml-auto text-[8px] font-bold px-1.5 py-0.5 rounded border ${
            last.error
              ? 'border-red-700/50 text-red-400 bg-red-950/20'
              : 'border-emerald-700/50 text-emerald-400 bg-emerald-950/20'
          }`}>
            {last.error ? 'FAULT' : `L${last.layer_reached}/8 OK`}
          </span>
        )}
        <button
          onClick={triggerGovernor}
          disabled={running}
          className={`flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-bold tracking-widest border transition-colors ${
            running
              ? 'border-violet-700/50 text-violet-400 animate-pulse cursor-wait'
              : 'border-violet-800/50 text-violet-500 hover:border-violet-500 hover:text-violet-300'
          }`}
        >
          <Zap className="w-2.5 h-2.5" />
          {running ? 'GOVERNING…' : 'GOVERN'}
        </button>
      </div>

      {/* KG stats row */}
      {kg && (
        <div className="grid grid-cols-5 gap-2">
          {[
            { label: 'ENTITIES',   value: kg.totalEntities },
            { label: 'CLAIMS',     value: kg.totalClaims },
            { label: 'VERIFIED',   value: `${accuracyPct ?? '—'}%` },
            { label: 'VISUALS',    value: vs?.total ?? 0 },
            { label: 'REVENUE',    value: rv ? `$${rv.monthlyRevenue.toFixed(0)}/mo` : '—' },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-[8px] text-zinc-600 tracking-widest">{label}</div>
              <div className={`text-sm font-bold font-mono ${
                label === 'VERIFIED'
                  ? (accuracyPct ?? 0) >= 70 ? 'text-emerald-400' : (accuracyPct ?? 0) >= 40 ? 'text-amber-400' : 'text-red-400'
                  : 'text-zinc-300'
              }`}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Last cycle layer map */}
      {last && (
        <div>
          <div className="flex items-center gap-1 mb-1.5">
            <span className="text-[8px] text-zinc-600 tracking-widest">LAST CYCLE</span>
            <span className="text-[8px] text-zinc-700 font-mono ml-1">
              {last.trigger.toUpperCase()} · {(last.duration_ms / 1000).toFixed(1)}s
            </span>
          </div>
          <div className="flex gap-1 flex-wrap">
            {[1, 2, 3, 4, 5, 6, 7, 8].map(n => (
              <LayerBadge key={n} n={n} reached={last.layer_reached} />
            ))}
          </div>
        </div>
      )}

      {/* Live governor report (after manual trigger) */}
      {lastReport && lastReport.urgentEscalations.length > 0 && (
        <div className="border-t border-zinc-800/50 pt-2 space-y-1">
          <div className="text-[8px] text-amber-500 tracking-widest font-bold">URGENT ESCALATIONS</div>
          {lastReport.urgentEscalations.map((e, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[9px]">
              <AlertTriangle className="w-2.5 h-2.5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <span className="text-amber-400 font-bold">{e.code}</span>
                <span className="text-zinc-500 ml-1">{e.detail}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* DGM mutations toggle */}
      {kg && kg.mutations > 0 && (
        <div className="border-t border-zinc-800/50 pt-2">
          <button
            onClick={() => setExpanded(x => !x)}
            className="flex items-center gap-1 text-[8px] text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {expanded ? <ChevronDown className="w-2.5 h-2.5" /> : <ChevronRight className="w-2.5 h-2.5" />}
            <span className="tracking-widest">DGM EVOLUTION LOG — {kg.mutations} mutations · {kg.appliedMutations} applied</span>
          </button>

          {expanded && kg.topActors.length > 0 && (
            <div className="mt-2 space-y-1">
              <div className="text-[8px] text-zinc-600 tracking-widest">TOP KG ACTORS</div>
              {kg.topActors.slice(0, 4).map(a => (
                <div key={a.name} className="flex items-center gap-2 text-[9px]">
                  <div className="w-20 truncate text-zinc-300 font-bold">{a.name}</div>
                  <div className="flex-1 h-1 bg-zinc-800 rounded overflow-hidden">
                    <div
                      className="h-full bg-violet-600 rounded"
                      style={{ width: `${a.confidence}%` }}
                    />
                  </div>
                  <span className="text-zinc-600 font-mono w-6 text-right">{a.confidence}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summary aggregate */}
      {summary && !loading && (
        <div className="text-[8px] text-zinc-700 font-mono pt-1 border-t border-zinc-800/30">
          {summary.cyclesReturned} cycles · avg {summary.avgLayersCompleted}/8 layers ·
          {summary.totalEntitiesExtracted} entities · {summary.totalClaimsVerified} claims ·
          {summary.avgDurationMs / 1000 | 0}s avg
        </div>
      )}
    </div>
  )
}
