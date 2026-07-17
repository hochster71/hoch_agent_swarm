'use client'

/**
 * AnalyzeBatchMonitor
 *
 * Displays live status of the NEXUS Batch Analysis cron
 * (/api/analyze-batch).  Polls /api/analyze-batch/status every 30s.
 * Includes a TRIGGER NOW button for manual test runs.
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { Search, Clock, Zap, BarChart2, RefreshCw } from 'lucide-react'
import type { BatchSnapshot } from '@/app/api/analyze-batch/status/route'

interface StatusPayload {
  ok:             boolean
  lastRun:        string | null
  runCount:       number
  totalProcessed: number
  totalUpdated:   number
  verdictTotals:  Record<string, number>
  batches:        BatchSnapshot[]
}

const VERDICT_COLORS: Record<string, string> = {
  VERIFIED:      'text-emerald-400',
  LIKELY_TRUE:   'text-sky-400',
  UNCONFIRMED:   'text-zinc-400',
  SUSPICIOUS:    'text-amber-400',
  DISINFORMATION:'text-red-400',
}

const VERDICT_BG: Record<string, string> = {
  VERIFIED:      'bg-emerald-900/50',
  LIKELY_TRUE:   'bg-sky-900/50',
  UNCONFIRMED:   'bg-zinc-800/50',
  SUSPICIOUS:    'bg-amber-900/50',
  DISINFORMATION:'bg-red-900/60',
}

const VERDICT_BAR: Record<string, string> = {
  VERIFIED:      'bg-emerald-500',
  LIKELY_TRUE:   'bg-sky-500',
  UNCONFIRMED:   'bg-zinc-500',
  SUSPICIOUS:    'bg-amber-500',
  DISINFORMATION:'bg-red-500',
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never'
  const ms = Date.now() - new Date(iso).getTime()
  const m  = Math.floor(ms / 60_000)
  if (m < 1)    return 'Just now'
  if (m < 60)   return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24)   return `${h}h ${m % 60}m ago`
  return `${Math.floor(h / 24)}d ago`
}

function fmtDuration(ms: number): string {
  if (ms < 1000)   return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

function utcTime(iso: string): string {
  return new Date(iso).toUTCString().replace('GMT', 'UTC').slice(0, 25)
}

export function AnalyzeBatchMonitor() {
  const [status, setStatus]     = useState<StatusPayload | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [trigResult, setTrigResult] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/analyze-batch/status', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: StatusPayload = await res.json()
      setStatus(data)
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchStatus, 30_000)

  const triggerNow = async () => {
    setTriggering(true)
    setTrigResult(null)
    try {
      const res = await fetch('/api/analyze-batch/trigger', {
        method:  'POST',
        cache:   'no-store',
      })
      const data = await res.json() as { ok?: boolean; error?: string; processed?: number; updated?: number }
      if (data.ok) {
        setTrigResult(`✓ Batch complete — ${data.processed} processed, ${data.updated} updated`)
        fetchStatus()
      } else {
        setTrigResult(`✗ Error: ${data.error ?? 'Unknown'}`)
      }
    } catch (e) {
      setTrigResult(`✗ ${String(e)}`)
    } finally {
      setTriggering(false)
    }
  }

  // Verdict totals for bar chart
  const verdictEntries = status
    ? Object.entries(status.verdictTotals).sort((a, b) => b[1] - a[1])
    : []
  const totalVerdicts = verdictEntries.reduce((s, [, n]) => s + n, 0)

  return (
    <div className="tac-card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-sky-400" />
          <span className="tac-label text-sky-300 tracking-widest">NEXUS BATCH ANALYSIS</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchStatus}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={triggerNow}
            disabled={triggering}
            className="flex items-center gap-1 px-2 py-1 text-[10px] font-bold tracking-widest bg-sky-900/40 hover:bg-sky-800/60 border border-sky-700/50 text-sky-300 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Zap className="w-2.5 h-2.5" />
            {triggering ? 'RUNNING…' : 'TRIGGER NOW'}
          </button>
        </div>
      </div>

      {/* Trigger result */}
      {trigResult && (
        <div className={`text-[10px] px-2 py-1 rounded ${trigResult.startsWith('✓') ? 'bg-emerald-900/40 text-emerald-300' : 'bg-red-900/40 text-red-300'}`}>
          {trigResult}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-[10px] text-red-400 bg-red-900/20 px-2 py-1 rounded">
          {error}
        </div>
      )}

      {/* 4-stat grid */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { label: 'BATCH RUNS',  value: status?.runCount       ?? '—', icon: BarChart2, color: 'text-sky-400' },
          { label: 'PROCESSED',   value: status?.totalProcessed ?? '—', icon: Search,    color: 'text-violet-400' },
          { label: 'UPDATED',     value: status?.totalUpdated   ?? '—', icon: Zap,       color: 'text-emerald-400' },
          { label: 'LAST RUN',    value: timeAgo(status?.lastRun ?? null), icon: Clock,  color: 'text-amber-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-zinc-900/50 border border-zinc-800/50 rounded p-2 space-y-1">
            <div className="flex items-center gap-1">
              <Icon className={`w-3 h-3 ${color}`} />
              <span className="text-[9px] text-zinc-500 tracking-widest">{label}</span>
            </div>
            <div className={`text-sm font-bold font-mono ${color}`}>{String(value)}</div>
          </div>
        ))}
      </div>

      {/* Verdict distribution */}
      {verdictEntries.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[9px] text-zinc-500 tracking-widest uppercase">Verdict Distribution (all runs)</div>
          {verdictEntries.map(([verdict, count]) => {
            const pct = totalVerdicts > 0 ? (count / totalVerdicts) * 100 : 0
            return (
              <div key={verdict} className="flex items-center gap-2">
                <div className="w-24 text-[9px] font-mono truncate text-right">
                  <span className={VERDICT_COLORS[verdict] ?? 'text-zinc-400'}>{verdict}</span>
                </div>
                <div className="flex-1 h-2 bg-zinc-800 rounded overflow-hidden">
                  <div
                    className={`h-2 rounded ${VERDICT_BAR[verdict] ?? 'bg-zinc-600'}`}
                    style={{ width: `${pct.toFixed(1)}%` }}
                  />
                </div>
                <div className="w-10 text-right text-[9px] text-zinc-500 font-mono">{count}</div>
              </div>
            )
          })}
        </div>
      )}

      {/* Batch history table */}
      {status && status.batches.length > 0 && (
        <div className="space-y-1">
          <div className="text-[9px] text-zinc-500 tracking-widest uppercase">Recent Batch Runs</div>
          <div className="overflow-x-auto">
            <table className="w-full text-[9px] font-mono">
              <thead>
                <tr className="text-zinc-600 border-b border-zinc-800">
                  <th className="text-left pb-1 pr-2">UTC</th>
                  <th className="text-center pb-1 px-1">DAY</th>
                  <th className="text-center pb-1 px-1">PROC</th>
                  <th className="text-center pb-1 px-1">UPD</th>
                  <th className="text-left pb-1 px-1">VERDICTS</th>
                  <th className="text-right pb-1 pl-1">DUR</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {status.batches.slice(0, 10).map(b => {
                  const tally: Record<string, number> = {}
                  for (const v of b.verdicts) tally[v] = (tally[v] ?? 0) + 1
                  return (
                    <tr key={b.id} className="hover:bg-zinc-900/30 transition-colors">
                      <td className="py-0.5 pr-2 text-zinc-500">{utcTime(b.processedAt)}</td>
                      <td className="py-0.5 px-1 text-center text-zinc-400">D{b.conflictDay}</td>
                      <td className="py-0.5 px-1 text-center text-violet-400">{b.processed}</td>
                      <td className="py-0.5 px-1 text-center text-emerald-400">{b.updated}</td>
                      <td className="py-0.5 px-1">
                        <div className="flex flex-wrap gap-0.5">
                          {Object.entries(tally).map(([v, n]) => (
                            <span
                              key={v}
                              className={`px-1 rounded text-[8px] ${VERDICT_BG[v] ?? 'bg-zinc-800/50'} ${VERDICT_COLORS[v] ?? 'text-zinc-400'}`}
                            >
                              {v.slice(0, 4)}{n > 1 ? `×${n}` : ''}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-0.5 pl-1 text-right text-zinc-500">{fmtDuration(b.durationMs)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && status && status.batches.length === 0 && (
        <div className="text-center py-4 text-zinc-600 text-[10px] tracking-widest">
          NO BATCH RUNS RECORDED YET
        </div>
      )}
    </div>
  )
}
