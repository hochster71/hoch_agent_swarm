'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import type { ForesightStats, ForesightSignal, TRiSMScan } from '@/lib/foresight-engine'
import type { GEAStats } from '@/lib/gea-engine'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function signalTypeColor(t: string): string {
  switch (t) {
    case 'SECURITY_THREAT':        return 'text-red-400'
    case 'GEOPOLITICAL_MOVE':      return 'text-orange-400'
    case 'REGULATORY_SHIFT':       return 'text-yellow-400'
    case 'NEWS_IMPACT':            return 'text-cyan-400'
    case 'MONETIZATION_OPPTY':     return 'text-green-400'
    case 'TECH_EMERGENCE':         return 'text-purple-400'
    case 'MARKET_SIGNAL':          return 'text-blue-400'
    case 'PLANETARY_SCALE_OPPTY':  return 'text-emerald-400'
    default:                       return 'text-gray-400'
  }
}

function riskColor(r: string): string {
  switch (r) {
    case 'CRITICAL': return 'text-red-400 animate-pulse'
    case 'HIGH':     return 'text-orange-400'
    case 'MEDIUM':   return 'text-yellow-400'
    default:         return 'text-green-400'
  }
}

function riskBg(r: string): string {
  switch (r) {
    case 'CRITICAL': return 'bg-red-900/30 border-red-700'
    case 'HIGH':     return 'bg-orange-900/30 border-orange-700'
    case 'MEDIUM':   return 'bg-yellow-900/20 border-yellow-700'
    default:         return 'bg-green-900/20 border-green-800'
  }
}

function horizonBadge(h: string): string {
  switch (h) {
    case '24H': return 'bg-red-900/40 text-red-300 border-red-800'
    case '72H': return 'bg-orange-900/40 text-orange-300 border-orange-800'
    case '1W':  return 'bg-yellow-900/40 text-yellow-300 border-yellow-800'
    case '1M':  return 'bg-blue-900/40 text-blue-300 border-blue-800'
    default:    return 'bg-gray-800 text-gray-400 border-gray-700'
  }
}

function fmtAge(ts: string): string {
  const d = Date.now() - new Date(ts).getTime()
  if (d < 60_000)    return `${Math.floor(d / 1000)}s ago`
  if (d < 3_600_000) return `${Math.floor(d / 60_000)}m ago`
  return `${Math.floor(d / 3_600_000)}h ago`
}

function confBar(conf: number): string {
  const w = Math.round(conf * 100)
  if (w >= 80) return 'bg-green-500'
  if (w >= 60) return 'bg-yellow-500'
  return 'bg-orange-500'
}

// ---------------------------------------------------------------------------
// Compact variant — for main dashboard
// ---------------------------------------------------------------------------

function ForesightPanelCompact() {
  const [stats,   setStats]   = useState<ForesightStats | null>(null)
  const [signals, setSignals] = useState<ForesightSignal[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const res  = await fetch('/api/intel/foresight?limit=4')
      if (!res.ok) return
      const data = await res.json() as { stats: ForesightStats; signals: ForesightSignal[] }
      setStats(data.stats)
      setSignals(data.signals)
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(load, 45_000)

  if (loading) return (
    <div className="border border-gray-800 rounded bg-black/40 p-3 animate-pulse h-20" />
  )
  if (!stats) return null

  const latestScan = stats.recentScans[0]

  return (
    <div className="border border-purple-900/40 rounded bg-black/60 p-3 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-purple-400 tracking-widest uppercase">
          ⚡ Layer 9 Foresight
        </span>
        {latestScan && (
          <span className={`text-[10px] font-mono font-bold ${riskColor(latestScan.risk_level)}`}>
            TRiSM: {latestScan.risk_level}
          </span>
        )}
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'SIGNALS',   val: stats.totalSignals,                     color: 'text-purple-300' },
          { label: 'HIGH CONF', val: stats.avgConfidence != null ? `${Math.round(stats.avgConfidence * 100)}%` : '—', color: 'text-green-400' },
          { label: 'HIGH RISK', val: stats.highRiskCount,                    color: 'text-orange-400' },
          { label: 'RULES',     val: stats.constitutionRules,                color: 'text-cyan-400' },
        ].map(({ label, val, color }) => (
          <div key={label} className="bg-black/40 rounded px-2 py-1.5 text-center">
            <div className={`text-sm font-bold font-mono ${color}`}>{val}</div>
            <div className="text-[9px] text-gray-600 tracking-widest">{label}</div>
          </div>
        ))}
      </div>

      {/* Recent signals */}
      {signals.slice(0, 4).map(sig => (
        <div key={sig.id} className="flex items-center gap-2 text-[10px] font-mono">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${sig.confidence >= 0.8 ? 'bg-green-400' : 'bg-yellow-400'}`} />
          <span className={`flex-shrink-0 ${signalTypeColor(sig.signal_type)}`}>
            {(sig.signal_type ?? '').replace(/_/g, ' ')}
          </span>
          <span className="text-gray-400 truncate flex-1">{sig.prediction}</span>
          <span className={`flex-shrink-0 px-1 py-0.5 rounded border text-[9px] ${horizonBadge(sig.horizon)}`}>
            {sig.horizon}
          </span>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// GEA Memory panel section (used in full panel)
// ---------------------------------------------------------------------------

function GEASection() {
  const [gea, setGea] = useState<GEAStats | null>(null)

  useEffect(() => {
    const load = async () => {
      const res = await fetch('/api/intel/foresight?mode=gea')
      const d   = await res.json() as { stats: GEAStats }
      setGea(d.stats)
    }
    void load()
  }, [])

  if (!gea) return <div className="text-gray-700 text-xs font-mono animate-pulse">loading GEA…</div>

  return (
    <div className="space-y-3">
      {/* Memory system counts */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'PERSIST', val: gea.persistentCount,  color: 'text-cyan-400' },
          { label: 'EPISODIC', val: gea.episodicCount,   color: 'text-blue-400' },
          { label: 'SEMANTIC', val: gea.semanticCount,   color: 'text-purple-400' },
          { label: 'PROCED',   val: gea.proceduralCount, color: 'text-green-400' },
        ].map(({ label, val, color }) => (
          <div key={label} className="bg-black/40 border border-gray-800 rounded p-2 text-center">
            <div className={`text-lg font-bold font-mono ${color}`}>{val}</div>
            <div className="text-[9px] text-gray-600 tracking-widest">{label}</div>
          </div>
        ))}
      </div>

      {/* Experience pool summary */}
      <div className="text-[10px] font-mono text-gray-500 grid grid-cols-2 gap-x-6 gap-y-1">
        <span>Total experiences: <span className="text-gray-300">{gea.totalExperiences}</span></span>
        <span>Avg Δ perf: <span className={gea.avgPerformanceDelta != null && gea.avgPerformanceDelta > 0 ? 'text-green-400' : 'text-orange-400'}>
          {gea.avgPerformanceDelta != null ? `${gea.avgPerformanceDelta > 0 ? '+' : ''}${gea.avgPerformanceDelta}` : '—'}
        </span></span>
      </div>

      {/* Top innovations */}
      {gea.topInnovations.length > 0 && (
        <div>
          <div className="text-[10px] text-gray-600 font-mono tracking-widest mb-1">TOP INNOVATIONS</div>
          {gea.topInnovations.slice(0, 3).map(e => (
            <div key={e.id} className="flex items-center gap-2 text-[10px] font-mono mb-1">
              <span className="text-green-400">✦</span>
              <span className="text-purple-300">{e.agent_type}</span>
              <span className="text-gray-400 truncate flex-1">{e.summary ?? 'Innovation logged'}</span>
              {e.performance_delta != null && (
                <span className="text-green-400 flex-shrink-0">+{e.performance_delta}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Full variant
// ---------------------------------------------------------------------------

function ForesightPanelFull() {
  const [stats,      setStats]      = useState<ForesightStats | null>(null)
  const [signals,    setSignals]    = useState<ForesightSignal[]>([])
  const [loading,    setLoading]    = useState(true)
  const [generating, setGenerating] = useState(false)
  const [genError,   setGenError]   = useState<string | null>(null)
  const [activeTab, setActiveTab]   = useState<'signals' | 'trism' | 'gea' | 'constitution'>('signals')

  const load = useCallback(async () => {
    try {
      const res  = await fetch('/api/intel/foresight?limit=30')
      const data = await res.json() as { stats: ForesightStats; signals: ForesightSignal[] }
      setStats(data.stats)
      setSignals(data.signals)
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(load, 30_000)

  const runCycle = async () => {
    setGenerating(true)
    setGenError(null)
    try {
      const res = await fetch('/api/intel/foresight', { method: 'POST' })
      const body = await res.json() as { ok: boolean; error?: string }
      if (!body.ok) {
        setGenError(body.error ?? 'Cycle failed')
      } else {
        await load()
      }
    } catch (e) {
      setGenError(String(e))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Metrics header */}
      {stats && (
        <>
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: 'SIGNALS',     val: stats.totalSignals,    color: 'text-purple-400' },
              { label: 'AVG CONF',    val: stats.avgConfidence != null ? `${Math.round(stats.avgConfidence * 100)}%` : '—', color: 'text-green-400' },
              { label: 'HIGH RISK',   val: stats.highRiskCount,   color: 'text-red-400' },
              { label: 'TRISM SCANS', val: stats.recentScans.length, color: 'text-cyan-400' },
              { label: 'ETH RULES',   val: stats.constitutionRules, color: 'text-yellow-400' },
            ].map(({ label, val, color }) => (
              <div key={label} className="bg-black/40 border border-gray-800 rounded p-3 text-center">
                <div className={`text-xl font-bold font-mono ${color}`}>{val}</div>
                <div className="text-[10px] text-gray-600 tracking-widest mt-1">{label}</div>
              </div>
            ))}
          </div>
          {/* Live intel context line */}
          <div className="text-[10px] font-mono text-gray-600 border border-gray-900 rounded px-3 py-1.5 bg-black/30">
            <span className="text-green-700">●</span>{' '}
            Predictions derived from{' '}
            <span className="text-green-400 font-bold">{stats.liveIntelCount}</span>{' '}
            live intel items ingested from real news sources — zero simulated data —{' '}
            <span className="text-purple-400">citations included per signal</span>
          </div>
        </>
      )}

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-gray-800">
        {(['signals', 'trism', 'gea', 'constitution'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            aria-pressed={activeTab === tab}
            className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider transition-colors ${
              activeTab === tab
                ? 'text-purple-400 border-b border-purple-500'
                : 'text-gray-600 hover:text-gray-400'
            }`}
          >
            {tab === 'trism' ? 'TRiSM' : tab === 'gea' ? 'GEA Memory' : tab}
          </button>
        ))}
      </div>

      {/* Foresight signals */}
      {activeTab === 'signals' && (
        <div className="space-y-2">
          {loading && <div className="text-gray-700 font-mono text-sm text-center py-8">loading…</div>}

          {!loading && signals.length === 0 && (
            <div className="space-y-4 py-4">
              <p className="text-gray-500 font-mono text-xs text-center leading-relaxed">
                No signals in database yet.<br />
                The AI Governor runs cycles automatically, but you can generate now.<br />
                <span className="text-gray-600">
                  Signals are derived from real ingested news — no simulated data.
                </span>
              </p>
              <div className="flex justify-center">
                <button
                  onClick={runCycle}
                  disabled={generating}
                  aria-label="Generate foresight signals from live intel"
                  className="px-4 py-2 bg-purple-900/60 border border-purple-700 rounded text-xs font-mono text-purple-300 hover:bg-purple-900 hover:text-purple-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-widest uppercase"
                >
                  {generating ? '⚡ ANALYZING LIVE INTEL…' : '⚡ GENERATE SIGNALS FROM LIVE INTEL'}
                </button>
              </div>
              {genError && (
                <p className="text-red-500 font-mono text-[10px] text-center">{genError}</p>
              )}
            </div>
          )}

          {/* GENERATE button always visible at top when signals exist */}
          {!loading && signals.length > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-gray-600">
                {signals.length} signals · auto-refreshes every 30s
              </span>
              <button
                onClick={runCycle}
                disabled={generating}
                aria-label="Regenerate foresight signals from latest live intel"
                className="px-3 py-1 bg-purple-900/40 border border-purple-800 rounded text-[10px] font-mono text-purple-400 hover:bg-purple-900/60 disabled:opacity-40 disabled:cursor-not-allowed transition-colors tracking-widest uppercase"
              >
                {generating ? '⚡ RUNNING…' : '⚡ REGEN'}
              </button>
            </div>
          )}

          {genError && signals.length > 0 && (
            <p className="text-red-500 font-mono text-[10px]">{genError}</p>
          )}

          {signals.map(sig => (
            <div key={sig.id} className="border border-gray-800 rounded p-3 hover:border-gray-700 transition-colors">
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`text-xs font-mono font-bold ${signalTypeColor(sig.signal_type)}`}>
                      {(sig.signal_type ?? '').replace(/_/g, ' ')}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded border text-[10px] font-mono ${horizonBadge(sig.horizon)}`}>
                      {sig.horizon}
                    </span>
                    <span className="text-[10px] text-gray-600 font-mono ml-auto">{fmtAge(sig.created_at)}</span>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed">{sig.prediction}</p>
                  {/* Confidence bar */}
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-gray-900 rounded h-1">
                      <div
                        className={`h-1 rounded ${confBar(sig.confidence)}`}
                        style={{ width: `${Math.round(sig.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-500 font-mono w-8">
                      {Math.round(sig.confidence * 100)}%
                    </span>
                  </div>
                  {/* Supporting evidence / citations */}
                  {Array.isArray(sig.supporting_evidence) && (sig.supporting_evidence as string[]).length > 0 && (
                    <div className="mt-2 space-y-0.5 border-t border-gray-900 pt-1.5">
                      {(sig.supporting_evidence as string[]).slice(0, 3).map((ev, i) => (
                        <div key={i} className="text-[9px] text-gray-600 font-mono leading-relaxed">
                          <span className="text-gray-700">↳</span>{' '}
                          {/* If evidence looks like a URL, make it a link */}
                          {ev.includes('http') ? (
                            <a
                              href={ev.replace(/^.*?(https?:\/\/)/, '$1')}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-700 hover:text-blue-500 underline"
                            >
                              {ev.length > 120 ? ev.slice(0, 120) + '…' : ev}
                            </a>
                          ) : (
                            <span className="text-gray-600">{ev}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TRiSM scans */}
      {activeTab === 'trism' && stats && (
        <div className="space-y-3">
          {stats.recentScans.length === 0 && (
            <div className="space-y-3 py-4">
              <p className="text-gray-700 font-mono text-sm text-center">
                No TRiSM scans yet — run a foresight cycle to trigger a scan
              </p>
              <div className="flex justify-center">
                <button
                  onClick={runCycle}
                  disabled={generating}
                  aria-label="Run TRiSM governance scan"
                  className="px-4 py-2 bg-cyan-900/40 border border-cyan-800 rounded text-xs font-mono text-cyan-400 hover:bg-cyan-900/60 disabled:opacity-50 tracking-widest uppercase"
                >
                  {generating ? '⚡ SCANNING…' : '⚡ RUN TRISM SCAN'}
                </button>
              </div>
            </div>
          )}
          {stats.recentScans.map((scan: TRiSMScan) => (
            <div key={scan.id} className={`border rounded p-3 ${riskBg(scan.risk_level)}`}>
              <div className="flex items-center gap-3 mb-2">
                <span className={`text-sm font-mono font-bold ${riskColor(scan.risk_level)}`}>
                  {scan.risk_level}
                </span>
                <span className="text-xs text-gray-400 font-mono">{scan.scan_type}</span>
                <span className="text-[10px] text-gray-600 font-mono ml-auto">{fmtAge(scan.created_at)}</span>
                {scan.auto_remediated && (
                  <span className="text-[10px] text-green-400 font-mono">AUTO-REMEDIATED</span>
                )}
              </div>
              {scan.recommendations.length > 0 && (
                <div className="space-y-0.5">
                  {scan.recommendations.slice(0, 3).map((rec, i) => (
                    <div key={i} className="text-[10px] text-gray-400 font-mono">
                      → {rec}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* GEA Memory */}
      {activeTab === 'gea' && <GEASection />}

      {/* Ethical Constitution */}
      {activeTab === 'constitution' && (
        <EthicalConstitutionSection />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Ethical Constitution section
// ---------------------------------------------------------------------------

function EthicalConstitutionSection() {
  const [rules, setRules] = useState<Array<{ rule_id: string; rule_text: string; rule_type: string; priority: number; active: boolean }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const { createBrowserClient } = await import('@/lib/supabase')
        const sb = createBrowserClient()
        const { data } = await sb
          .from('ethical_constitution')
          .select('rule_id, rule_text, rule_type, priority, active')
          .eq('active', true)
          .order('priority', { ascending: false })
        setRules(data ?? [])
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const typeColor = (t: string) => {
    switch (t) {
      case 'TRUTH':          return 'text-cyan-400'
      case 'NON_HARM':       return 'text-red-400'
      case 'TRANSPARENCY':   return 'text-yellow-400'
      case 'PRIVACY':        return 'text-purple-400'
      case 'SUSTAINABILITY': return 'text-green-400'
      case 'FINANCIAL':      return 'text-emerald-400'
      default:               return 'text-gray-400'
    }
  }

  if (loading) return <div className="text-gray-700 text-xs font-mono">loading constitution…</div>

  return (
    <div className="space-y-2">
      {rules.map(r => (
        <div key={r.rule_id} className="border border-gray-800 rounded p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-mono font-bold ${typeColor(r.rule_type)}`}>{r.rule_type}</span>
            <span className="text-[10px] text-gray-600 font-mono">{r.rule_id}</span>
            <span className="text-[10px] text-gray-600 font-mono ml-auto">P{r.priority}</span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{r.rule_text}</p>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export default function ForesightPanel(props: { compact?: boolean }) {
  if (props.compact) return <ForesightPanelCompact />
  return <ForesightPanelFull />
}
