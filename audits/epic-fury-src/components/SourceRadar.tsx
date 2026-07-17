'use client'

/**
 * SourceRadar
 * Polls /api/intel/stats and shows which news sources are contributing
 * the most intel by count, with theater distribution and verification rates.
 * Polls every 2 minutes.
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { Radio, ShieldCheck, DatabaseZap } from 'lucide-react'
import type { IntelStats } from '@/app/api/intel/stats/route'

const SOURCE_TIERS: Record<string, number> = {
  // Tier 1 — highly credible primaries
  reuters: 1, 'associated press': 1, 'ap news': 1, bbc: 1, 'al jazeera': 1,
  centcom: 1, pentagon: 1, afp: 1, axios: 1,
  // Tier 2 — reliable secondaries
  cnn: 2, 'fox news': 2, nbc: 2, abc: 2, nyt: 2, guardian: 2,
  'times of israel': 2, haaretz: 2, 'arab news': 2, middle: 2,
  // Tier 3 — OSINT / analysis
  isw: 3, bellingcat: 3, oryx: 3, janes: 3,
}

function getTier(name: string): number {
  const lower = name.toLowerCase()
  for (const [key, tier] of Object.entries(SOURCE_TIERS)) {
    if (lower.includes(key)) return tier
  }
  return 3
}

function tierLabel(t: number) {
  if (t === 1) return { text: 'T1', color: 'text-emerald-400' }
  if (t === 2) return { text: 'T2', color: 'text-sky-400' }
  return { text: 'T3', color: 'text-zinc-500' }
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60)   return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

interface SourceRadarProps {
  /** Max sources to display (default 10) */
  limit?: number
  compact?: boolean
}

export function SourceRadar({ limit = 10, compact = false }: SourceRadarProps) {
  const [data, setData]       = useState<IntelStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/stats', { cache: 'no-store' })
      if (!res.ok) return
      const json: IntelStats = await res.json()
      setData(json)
      setLastFetch(new Date())
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useSmartPoll(fetchStats, 2 * 60 * 1000)

  if (loading) {
    return (
      <div className="tac-card p-4 animate-pulse">
        <div className="h-3 bg-zinc-800 rounded w-1/3 mb-3" />
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-2 bg-zinc-800 rounded w-full mb-2" />
        ))}
      </div>
    )
  }

  if (!data) {
    return <div className="tac-card p-3"><p className="text-[10px] text-zinc-600">Source data unavailable</p></div>
  }

  // Build source list from byTheater tags — stats API returns topTheaters
  // We reconstruct from topTheaters as a proxy; use byTheater for theater bars
  const theaters = Object.entries(data.byTheater ?? {})
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, limit)

  const maxTheater = theaters.length > 0 ? (theaters[0][1] as number) : 1
  const total      = data.total ?? 0
  const verified   = data.verified ?? 0
  const verifyRate = total > 0 ? Math.round((verified / total) * 100) : 0

  // ── Compact mode ──────────────────────────────────────────────────────────
  if (compact) {
    return (
      <div className="tac-card p-2.5 flex items-center gap-3">
        <Radio size={11} className="text-emerald-400 animate-pulse shrink-0" />
        <span className="text-[9px] text-zinc-400 tracking-wider">
          {total.toLocaleString()} items · {data.topTheaters?.length ?? 0} theaters · {verifyRate}% verified
        </span>
        {lastFetch && (
          <span className="text-[8px] text-zinc-700 ml-auto">{timeAgo(lastFetch.toISOString())}</span>
        )}
      </div>
    )
  }

  // ── Full mode ─────────────────────────────────────────────────────────────
  return (
    <div className="tac-card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio size={12} className="text-emerald-400 animate-pulse" />
          <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Source Intelligence Radar</p>
        </div>
        <div className="flex items-center gap-2 text-right">
          <DatabaseZap size={9} className="text-zinc-600" />
          <span className="text-[8px] text-zinc-600 tabular-nums">
            {lastFetch ? timeAgo(lastFetch.toISOString()) : '--'}
          </span>
        </div>
      </div>

      {/* DB-level stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'TOTAL', value: total.toLocaleString(), color: 'text-zinc-200' },
          { label: 'VERIFIED', value: `${verified} (${verifyRate}%)`, color: 'text-emerald-400' },
          { label: 'AI-AUTHORED', value: String(data.heraldAuthored ?? 0), color: 'text-sky-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="tac-card bg-zinc-900/40 p-2 text-center">
            <p className="text-[8px] text-zinc-600 tracking-widest">{label}</p>
            <p className={`text-xs font-bold tabular-nums ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Theater distribution bars */}
      {theaters.length > 0 && (
        <div>
          <p className="text-[8px] text-zinc-600 tracking-[0.2em] uppercase mb-2">Theater Distribution</p>
          <div className="space-y-1.5">
            {theaters.map(([name, count]) => {
              const pct = Math.round(((count as number) / maxTheater) * 100)
              return (
                <div key={name} className="flex items-center gap-2">
                  <span className="text-[9px] text-zinc-400 w-20 shrink-0 truncate">{name}</span>
                  <div className="flex-1 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-full bg-emerald-700/70 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[9px] text-zinc-500 w-5 text-right tabular-nums">{count as number}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Top source names */}
      {data.topTheaters && data.topTheaters.length > 0 && (
        <div>
          <p className="text-[8px] text-zinc-600 tracking-[0.2em] uppercase mb-2">Active Theaters Ranked</p>
          <div className="flex flex-wrap gap-1.5">
            {data.topTheaters.slice(0, limit).map((t, i) => {
              const tier = getTier(t.theater ?? '')
              const tl   = tierLabel(tier)
              return (
                <div
                  key={i}
                  className="flex items-center gap-1.5 bg-zinc-900/60 rounded-lg px-3 py-2 min-h-[32px]"
                >
                  <span className={`text-[8px] font-bold ${tl.color}`}>{tl.text}</span>
                  <span className="text-[9px] text-zinc-300">{t.theater}</span>
                  <span className="text-[8px] text-zinc-600">{t.count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Verdict distribution */}
      {data.byVerdict && Object.keys(data.byVerdict).length > 0 && (
        <div>
          <p className="text-[8px] text-zinc-600 tracking-[0.2em] uppercase mb-2">Verdict Distribution</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.byVerdict).map(([verdict, count]) => {
              const color =
                verdict === 'VERIFIED'       ? 'text-emerald-400 border-emerald-800/40' :
                verdict === 'LIKELY_TRUE'    ? 'text-sky-400     border-sky-800/40' :
                verdict === 'SUSPICIOUS'     ? 'text-amber-400   border-amber-800/40' :
                verdict === 'DISINFORMATION' ? 'text-red-400     border-red-800/40' :
                                              'text-zinc-500    border-zinc-800/40'
              return (
                <div key={verdict} className={`text-center border rounded px-2 py-1 ${color}`}>
                  <p className="text-[8px] tracking-wider">{verdict}</p>
                  <p className="text-xs font-bold tabular-nums">{count as number}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Last added */}
      {data.lastAdded && (
        <div className="flex items-center gap-1.5 text-[8px] text-zinc-700 border-t border-zinc-800/60 pt-2">
          <ShieldCheck size={8} className="text-zinc-700" />
          <span>Last intel: {timeAgo(data.lastAdded)}</span>
        </div>
      )}
    </div>
  )
}
