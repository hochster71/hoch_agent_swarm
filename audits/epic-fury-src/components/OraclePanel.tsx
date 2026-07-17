'use client'

import { useCallback, useState } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import type { OracleThreat, ThreatSeverity } from '@/lib/oracle-engine'

interface EnhancedThreat extends OracleThreat {
  aiProbability:  number | null    // 0-1 AI-adjusted probability
  aiConfidence:   'HIGH' | 'MEDIUM' | 'LOW' | null
  aiKeySignal:    string | null
  aiReasoning:    string | null
  aiTrend:        'UP' | 'DOWN' | 'STABLE' | null
}

interface OracleResponse {
  threats:      EnhancedThreat[]
  conflictDay:  number
  generatedAt:  string
  modelVersion: string
  aiAvailable:  boolean
  intelWindow:  number
}

const SEVERITY_COLOR: Record<ThreatSeverity, string> = {
  CRITICAL: 'text-red-400 border-red-500/60 bg-red-950/40',
  HIGH:     'text-orange-400 border-orange-500/60 bg-orange-950/30',
  MODERATE: 'text-yellow-400 border-yellow-500/50 bg-yellow-950/20',
  LOW:      'text-blue-400 border-blue-500/40 bg-blue-950/20',
  MINIMAL:  'text-slate-400 border-slate-600/40 bg-slate-900/20',
}

const BAR_COLOR: Record<ThreatSeverity, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-500',
  MODERATE: 'bg-yellow-500',
  LOW:      'bg-blue-500',
  MINIMAL:  'bg-slate-500',
}

const TREND_GLYPH: Record<string, string> = {
  UP:     '▲',
  DOWN:   '▼',
  STABLE: '◆',
}

const TREND_COLOR: Record<string, string> = {
  UP:     'text-red-400',
  DOWN:   'text-green-400',
  STABLE: 'text-slate-400',
}

export function OraclePanel() {
  const [data,    setData]    = useState<OracleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<string>('')

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/oracle/enhance', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json() as OracleResponse
      setData(json)
      setError(null)
      setLastRefresh(new Date().toLocaleTimeString('en-US', { hour12: false }) + 'Z')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fetch error')
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchData, 30_000)

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-700/50 rounded-sm p-4 animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-48 mb-3" />
        {[1, 2, 3].map(i => (
          <div key={i} className="h-12 bg-slate-800 rounded mb-2" />
        ))}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900/60 border border-red-900/40 rounded-sm p-4">
        <p className="text-red-400 text-xs font-mono">ORACLE-9 OFFLINE — {error ?? 'No data'}</p>
      </div>
    )
  }

  const highest = data.threats.length > 0
    ? data.threats.reduce((mx, t) => (t.probability ?? 0) > (mx.probability ?? 0) ? t : mx, data.threats[0])
    : null

  return (
    <div className="bg-slate-950/80 border border-slate-700/40 rounded-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/40">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-xs font-mono font-bold text-slate-200 tracking-widest">ORACLE-9</span>
          <span className="text-xs font-mono text-slate-500">{data.modelVersion}</span>
          {data.aiAvailable && (
            <span className="text-[9px] font-mono text-emerald-600 tracking-widest border border-emerald-900 px-1 rounded-sm">
              AI·{data.intelWindow} signals
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-500">
            DAY&nbsp;{data.conflictDay}
          </span>
          <span className="text-xs font-mono text-slate-600">
            {lastRefresh}
          </span>
        </div>
      </div>

      {/* Top threat alert */}
      {highest && highest.probability >= 0.50 && (
        <div className={`px-4 py-2 border-b border-slate-700/30 ${SEVERITY_COLOR[highest.severity]}`}>
          <p className="text-xs font-mono font-bold">
            ⚠ HIGHEST THREAT — {highest.label.toUpperCase()}
          </p>
          <p className="text-xs font-mono opacity-70 mt-0.5 line-clamp-1">
            {highest.topSignal}
          </p>
        </div>
      )}

      {/* Threat rows */}
      <div className="divide-y divide-slate-800/60">
        {data.threats.map(t => {
          const pct    = Math.round(t.probability * 100)
          const aiPct  = t.aiProbability !== null ? Math.round(t.aiProbability * 100) : null
          const aiDiff = aiPct !== null ? aiPct - pct : null
          return (
            <div key={t.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <div>
                  <span className="text-xs font-mono text-slate-200 font-semibold">{t.label}</span>
                  <span className="ml-2 text-xs font-mono text-slate-500">{t.domain}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs font-mono font-bold ${TREND_COLOR[t.trend]}`}>
                    {TREND_GLYPH[t.trend]}&thinsp;{Math.abs(t.trendDeltaPp) > 0 ? `${t.trendDeltaPp > 0 ? '+' : ''}${t.trendDeltaPp}pp` : ''}
                  </span>
                  <span className={`text-xs font-mono px-2 py-0.5 border rounded-sm font-bold ${SEVERITY_COLOR[t.severity]}`}>
                    {t.severity}
                  </span>
                </div>
              </div>

              {/* Probability bars — Bayesian + AI overlay */}
              <div className="flex items-center gap-2 mb-1">
                <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden relative">
                  {/* Base Bayesian bar */}
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${BAR_COLOR[t.severity]}`}
                    style={{ width: `${pct}%` }}
                  />
                  {/* AI overlay tick */}
                  {aiPct !== null && (
                    <div
                      className="absolute top-0 h-full w-0.5 bg-emerald-400 opacity-80"
                      style={{ left: `${aiPct}%` }}
                    />
                  )}
                </div>
                <div className="flex items-center gap-1 w-24 justify-end">
                  <span className="text-sm font-mono font-bold text-slate-100">
                    {pct}%
                  </span>
                  {aiPct !== null && aiDiff !== null && (
                    <span className={`text-[9px] font-mono font-bold ${
                      aiDiff > 0 ? 'text-red-400' : aiDiff < 0 ? 'text-emerald-400' : 'text-slate-500'
                    }`}>
                      AI:{aiPct}%{aiDiff !== 0 ? ` (${aiDiff > 0 ? '+' : ''}${aiDiff})` : ''}
                    </span>
                  )}
                </div>
              </div>

              {/* CI + window */}
              <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
                <span>90% CI [{Math.round(t.ciLow * 100)}–{Math.round(t.ciHigh * 100)}%]</span>
                <span>{t.windowHours}h window</span>
                {t.hazardP !== undefined && (
                  <span className="text-slate-600">
                    Bayes {Math.round(t.bayesP * 100)}% · Hazard {Math.round(t.hazardP * 100)}%
                  </span>
                )}
              </div>

              {/* AI key signal */}
              {t.aiKeySignal && (
                <p className="text-[9px] font-mono text-emerald-700 mt-1 leading-relaxed">
                  <span className="text-emerald-800">◉ AI:</span> {t.aiKeySignal}
                </p>
              )}

              {/* Active signals fallback */}
              {!t.aiKeySignal && t.activeSignals.length > 0 && (
                <p className="text-xs font-mono text-slate-600 mt-1">
                  {t.activeSignals.length} active signal{t.activeSignals.length !== 1 ? 's' : ''}:&nbsp;
                  <span className="text-slate-500">
                    {t.activeSignals[0]?.description.substring(0, 60)}…
                  </span>
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
