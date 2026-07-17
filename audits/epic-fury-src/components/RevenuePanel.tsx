'use client'

/**
 * components/RevenuePanel.tsx — Layer 8 Wealth & Revenue Autonomy Dashboard
 *
 * Displays active revenue streams, monetization strategies proposed by the
 * DGM/GEA engine, revenue ledger stats, and pending compliance reviews.
 * Auto-refreshes every 90 seconds.
 *
 * Ethical notice: all strategies require compliance_verified=true and
 * human review before activation. No automated spend or withdrawal occurs.
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  DollarSign, TrendingUp, BarChart2, ShieldCheck, Zap,
  Clock, CheckCircle2, AlertTriangle, Circle,
} from 'lucide-react'
import type {
  RevenueStream,
  RevenueStats,
  MonetizationStrategy,
  RevenueStreamType,
  RevenueStreamStatus,
} from '@/lib/revenue-engine'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(1)}k`
  return `$${n.toFixed(2)}`
}

const TYPE_COLOR: Record<RevenueStreamType, string> = {
  SUBSCRIPTION:       'text-emerald-400 border-emerald-800/50 bg-emerald-950/20',
  DYNAMIC_ADS:        'text-amber-400 border-amber-800/50 bg-amber-950/20',
  AFFILIATE:          'text-blue-400 border-blue-800/50 bg-blue-950/20',
  DATA_LICENSING:     'text-violet-400 border-violet-800/50 bg-violet-950/20',
  SPONSORSHIP:        'text-cyan-400 border-cyan-800/50 bg-cyan-950/20',
  FINANCIAL_INSIGHTS: 'text-sky-400 border-sky-800/50 bg-sky-950/20',
  CRYPTO_MICRO:       'text-orange-400 border-orange-800/50 bg-orange-950/20',
  COMPOUND:           'text-zinc-400 border-zinc-700/50 bg-zinc-900/20',
}

const STATUS_BADGE: Record<RevenueStreamStatus, { label: string; cls: string }> = {
  PROPOSED:   { label: 'PROPOSED',   cls: 'text-zinc-400 border-zinc-700/40 bg-zinc-900/30' },
  TESTING:    { label: 'TESTING',    cls: 'text-amber-400 border-amber-800/40 bg-amber-950/20' },
  ACTIVE:     { label: 'ACTIVE',     cls: 'text-emerald-400 border-emerald-800/40 bg-emerald-950/20' },
  PAUSED:     { label: 'PAUSED',     cls: 'text-zinc-500 border-zinc-800/30 bg-zinc-900/20' },
  DEPRECATED: { label: 'DEPRECATED', cls: 'text-red-500 border-red-900/30 bg-red-950/10' },
}

interface RevenueAPIResponse {
  stats:        RevenueStats
  streams:      RevenueStream[]
  strategies:   MonetizationStrategy[]
  generatedAt:  string
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCell({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="text-center">
      <div className="text-[7px] text-zinc-600 tracking-widest uppercase">{label}</div>
      <div className="text-sm font-bold font-mono text-zinc-200">{value}</div>
      {sub && <div className="text-[7px] text-zinc-600 font-mono">{sub}</div>}
    </div>
  )
}

function StreamRow({ stream }: { stream: RevenueStream }) {
  const badge = STATUS_BADGE[stream.status] ?? STATUS_BADGE['PROPOSED']
  const typeColor = TYPE_COLOR[stream.type] ?? 'text-zinc-400 border-zinc-700/40 bg-zinc-900/20'
  const est = Number(stream.estimated_monthly_usd)
  const actual = Number(stream.actual_monthly_usd)
  const pct = est > 0 ? Math.min(100, Math.round((actual / est) * 100)) : 0

  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-zinc-800/30 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className={`text-[7px] font-bold px-1 py-0.5 rounded border ${typeColor}`}>
            {(stream.type ?? '').replace('_', ' ')}
          </span>
          <span className={`text-[7px] font-bold px-1 py-0.5 rounded border ${badge.cls}`}>
            {badge.label}
          </span>
          {stream.compliance_verified && (
            <ShieldCheck className="w-2.5 h-2.5 text-emerald-500" />
          )}
        </div>
        <div className="text-[9px] text-zinc-300 font-medium mt-0.5 truncate">{stream.name}</div>
        {stream.description && (
          <div className="text-[8px] text-zinc-600 mt-0.5 line-clamp-1">{stream.description}</div>
        )}
        {est > 0 && (
          <div className="mt-1">
            <div className="flex justify-between text-[7px] text-zinc-600 mb-0.5">
              <span>Revenue vs est</span>
              <span className="font-mono">{fmt(actual)} / {fmt(est)}/mo</span>
            </div>
            <div className="h-0.5 bg-zinc-800 rounded overflow-hidden">
              <div
                className={`h-full rounded ${stream.status === 'ACTIVE' ? 'bg-emerald-600' : 'bg-zinc-600'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StrategyRow({ strategy }: { strategy: MonetizationStrategy }) {
  const isProposed = strategy.status === 'PROPOSED'
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-zinc-800/30 last:border-0">
      {isProposed
        ? <Circle className="w-2.5 h-2.5 text-zinc-600 flex-shrink-0 mt-0.5" />
        : <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500 flex-shrink-0 mt-0.5" />
      }
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-zinc-200 font-medium truncate">{strategy.title}</span>
          {strategy.estimated_monthly_impact_usd > 0 && (
            <span className="text-[7px] font-mono text-emerald-500 flex-shrink-0">
              +{fmt(Number(strategy.estimated_monthly_impact_usd))}/mo
            </span>
          )}
        </div>
        {strategy.compliance_notes && (
          <div className="text-[7px] text-zinc-600 mt-0.5 line-clamp-1 italic">
            {strategy.compliance_notes}
          </div>
        )}
        {!strategy.compliance_verified && (
          <div className="flex items-center gap-1 mt-0.5">
            <AlertTriangle className="w-2 h-2 text-amber-500" />
            <span className="text-[7px] text-amber-500">Pending compliance review before activation</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface RevenuePanelProps {
  compact?: boolean
}

export default function RevenuePanel({ compact = false }: RevenuePanelProps) {
  const [data, setData]       = useState<RevenueAPIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState<'streams' | 'strategies'>('streams')

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/revenue?limit=15', { cache: 'no-store' })
      if (res.ok) setData(await res.json() as RevenueAPIResponse)
    } catch { /* non-fatal */ } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchData, 90_000)

  const s = data?.stats

  return (
    <div className="rounded-lg border border-zinc-800/60 bg-zinc-950/60 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <DollarSign className="w-4 h-4 text-emerald-400" />
        <span className="tac-label text-emerald-300 tracking-widest text-[10px]">WEALTH ENGINE</span>
        <span className="text-[7px] text-zinc-600 ml-auto font-mono">L8 · REVENUE AUTONOMY</span>
      </div>

      {/* Stats bar */}
      {s && (
        <div className={`grid gap-2 ${compact ? 'grid-cols-3' : 'grid-cols-3 sm:grid-cols-6'}`}>
          <StatCell label="Monthly"   value={fmt(s.monthlyRevenue)} />
          <StatCell label="Daily"     value={fmt(s.dailyRevenue)} />
          <StatCell label="Projected" value={fmt(s.projectedAnnualUsd)} sub="/yr" />
          {!compact && (
            <>
              <StatCell label="Active"    value={String(s.activeStreams)}     sub="streams" />
              <StatCell label="Proposed"  value={String(s.proposedStreams)}   sub="pending" />
              <StatCell label="DGM Tact"  value={String(s.strategiesProposed)} sub="proposed" />
            </>
          )}
        </div>
      )}

      {!compact && (
        <>
          {/* Tab switcher */}
          <div className="flex gap-1 border-b border-zinc-800/50 pb-1">
            {(['streams', 'strategies'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex items-center gap-1 px-2 py-0.5 rounded text-[8px] font-bold tracking-widest transition-colors ${
                  tab === t
                    ? 'bg-zinc-800/60 text-zinc-200'
                    : 'text-zinc-600 hover:text-zinc-400'
                }`}
              >
                {t === 'streams'     && <TrendingUp className="w-2.5 h-2.5" />}
                {t === 'strategies'  && <BarChart2   className="w-2.5 h-2.5" />}
                {t.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Content */}
          {loading && (
            <div className="text-[8px] text-zinc-600 tracking-widest animate-pulse">LOADING REVENUE DATA…</div>
          )}

          {!loading && tab === 'streams' && (
            <div className="space-y-0">
              {(data?.streams ?? []).length === 0
                ? (
                  <div className="text-[8px] text-zinc-600 text-center py-3">
                    No revenue streams yet — Governor Layer 8 will bootstrap on next cycle
                  </div>
                )
                : (data?.streams ?? []).map(st => (
                  <StreamRow key={st.id} stream={st} />
                ))
              }
            </div>
          )}

          {!loading && tab === 'strategies' && (
            <div className="space-y-0">
              {(data?.strategies ?? []).length === 0
                ? (
                  <div className="text-[8px] text-zinc-600 text-center py-3">
                    No DGM strategies yet — run a governor cycle to generate proposals
                  </div>
                )
                : (data?.strategies ?? []).map(st => (
                  <StrategyRow key={st.id} strategy={st} />
                ))
              }
            </div>
          )}

          {/* Ethical compliance footer */}
          <div className="border-t border-zinc-800/40 pt-2 flex items-start gap-1.5">
            <ShieldCheck className="w-2.5 h-2.5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div className="text-[7px] text-zinc-700 leading-tight">
              All strategies require compliance review before activation. No automated spend, withdrawal,
              or high-risk instruments. Editorial independence maintained. Not financial advice.
            </div>
          </div>
        </>
      )}

      {compact && s?.topStreamName && (
        <div className="flex items-center gap-1 text-[8px] text-zinc-600">
          <Zap className="w-2.5 h-2.5 text-emerald-600" />
          <span>Top stream: <span className="text-zinc-400">{s.topStreamName}</span></span>
          {s.recentStrategyTitle && (
            <>
              <Clock className="w-2.5 h-2.5 ml-2" />
              <span className="truncate max-w-[120px]">{s.recentStrategyTitle}</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}
