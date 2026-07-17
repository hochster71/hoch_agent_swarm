'use client'

/**
 * LiveSitrepDoc — replaces the static OPORD sections 1-7 in sitrep/page.tsx.
 * Polls /api/intel/digest every 90 seconds and renders live AI assessment data.
 */

import { useEffect, useState, useCallback } from 'react'
import {
  AlertTriangle, CheckCircle2, TrendingUp, TrendingDown,
  Minus, RefreshCw, Wifi, WifiOff, BarChart2, Cpu, Globe,
  Zap, Activity,
} from 'lucide-react'
import type { IntelDigest } from '@/app/api/intel/digest/route'

// ── helpers ──────────────────────────────────────────────────────────────────

function confColor(c: number) {
  if (c >= 80) return 'text-emerald-400'
  if (c >= 60) return 'text-amber-400'
  return 'text-red-400'
}

function levelColor(level: IntelDigest['assessmentLevel']) {
  return {
    CRITICAL: 'text-red-400 border-red-700 bg-red-950/30',
    HIGH:     'text-orange-400 border-orange-700 bg-orange-950/20',
    ELEVATED: 'text-amber-400 border-amber-700 bg-amber-950/20',
    MODERATE: 'text-emerald-400 border-emerald-800 bg-emerald-950/20',
  }[level]
}

function severityBadge(s: string) {
  const map: Record<string, string> = {
    CRITICAL: 'bg-red-900/60 text-red-300 border-red-700',
    HIGH:     'bg-orange-900/60 text-orange-300 border-orange-700',
    ELEVATED: 'bg-amber-900/60 text-amber-300 border-amber-700',
    MODERATE: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  }
  return map[s] ?? 'bg-zinc-800 text-zinc-400 border-zinc-700'
}

function trendIcon(t: string) {
  if (t === 'RISING')   return <TrendingUp   size={10} className="text-red-400" />
  if (t === 'FALLING')  return <TrendingDown size={10} className="text-emerald-400" />
  return <Minus size={10} className="text-zinc-500" />
}

function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="text-[9px] font-bold text-emerald-600 tracking-widest border border-emerald-900 px-1.5 py-0.5">
        {num}
      </span>
      <h2 className="text-[10px] font-bold text-zinc-300 tracking-widest uppercase">{title}</h2>
      <div className="flex-1 border-t border-zinc-800" />
    </div>
  )
}

function Row({ label, children, conf }: { label: string; children: React.ReactNode; conf?: string }) {
  const confMap: Record<string, string> = { HIGH: 'text-emerald-500', MOD: 'text-amber-500', LOW: 'text-red-500' }
  return (
    <div className="flex gap-2 text-[10px] py-1 border-b border-zinc-900/60 last:border-0">
      <div className="shrink-0 w-28 text-zinc-500 tracking-wide flex gap-1 items-start pt-0.5">
        {label}
        {conf && <span className={`text-[8px] font-bold ${confMap[conf] ?? 'text-zinc-600'}`}>[{conf}]</span>}
      </div>
      <div className="text-zinc-300 leading-relaxed flex-1">{children}</div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export function LiveSitrepDoc({ pollMs = 90_000 }: { pollMs?: number }) {
  const [digest, setDigest]     = useState<IntelDigest | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [lastPoll, setLastPoll] = useState<string>('')

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/digest', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: IntelDigest = await res.json()
      setDigest(data)
      setError(null)
      setLastPoll(new Date().toISOString())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'fetch error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch_()
    const id = setInterval(fetch_, pollMs)
    return () => clearInterval(id)
  }, [fetch_, pollMs])

  // ── skeleton ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="tac-card p-5 animate-pulse">
            <div className="h-3 w-32 bg-zinc-800 rounded mb-4" />
            {[1, 2, 3].map(j => (
              <div key={j} className="flex gap-2 mb-2">
                <div className="h-2.5 w-24 bg-zinc-800 rounded shrink-0" />
                <div className="h-2.5 flex-1 bg-zinc-900 rounded" />
              </div>
            ))}
          </div>
        ))}
      </div>
    )
  }

  // ── error / empty state ──────────────────────────────────────────────────
  if (error || !digest) {
    return (
      <div className="tac-card p-6 flex flex-col items-center gap-3 text-center">
        <WifiOff size={28} className="text-zinc-700" />
        <p className="text-[10px] text-zinc-500 tracking-widest uppercase">
          Digest feed unavailable — {error ?? 'no data'}
        </p>
        <button
          onClick={fetch_}
          className="text-[9px] tracking-widest text-emerald-500 hover:text-emerald-300 flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw size={10} /> RETRY
        </button>
      </div>
    )
  }

  const d = digest

  // ── assessment level header ──────────────────────────────────────────────
  const assessClass = levelColor(d.assessmentLevel)

  return (
    <div className="space-y-4">

      {/* Live indicator */}
      <div className="flex items-center justify-between text-[8px] text-zinc-600 tracking-widest uppercase">
        <span className="flex items-center gap-1.5">
          <Wifi size={9} className="text-emerald-600 animate-pulse" />
          LIVE AI DIGEST — DAY {d.conflictDay} — {d.dtg}
        </span>
        {lastPoll && (
          <span>UPDATED {new Date(lastPoll).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
        )}
      </div>

      {/* ASSESSMENT LEVEL BANNER */}
      <div className={`tac-card p-4 border ${assessClass}`}>
        <div className="flex items-center gap-2 mb-1">
          <AlertTriangle size={12} className="animate-pulse" />
          <span className="text-[9px] font-bold tracking-widest uppercase">
            THREAT ASSESSMENT: {d.assessmentLevel}
          </span>
        </div>
        <p className="text-[10px] text-zinc-400 leading-relaxed">{d.assessmentReason}</p>
      </div>

      {/* AI NARRATIVE */}
      {d.aiNarrative && (
        <div className="tac-card p-4 border border-zinc-800 bg-zinc-900/20">
          <div className="flex items-center gap-1.5 mb-2">
            <Cpu size={10} className="text-emerald-600" />
            <span className="text-[9px] font-bold tracking-widest text-emerald-600 uppercase">
              AI Executive Summary
            </span>
            <span className="text-[8px] text-zinc-700 ml-auto">GPT-4o · {d.dtg}</span>
          </div>
          <p className="text-[10px] text-zinc-300 leading-relaxed whitespace-pre-line">{d.aiNarrative}</p>
        </div>
      )}

      {/* ── SECTION 1: SITUATION ── */}
      <div className="tac-card p-5">
        <SectionHeader num="1" title="Situation" />

        <p className="text-[10px] font-bold text-zinc-300 tracking-widest uppercase mb-3">1a. Intel DB Summary (Last 24h)</p>
        <div className="space-y-0.5 mb-4">
          <Row label="Day" conf="HIGH">Day {d.conflictDay} — Operation Epic Fury</Row>
          <Row label="Intel items" conf="HIGH">{d.total24h} items ingested · {d.verified24h} verified ({d.verifyRate}%)</Row>
          <Row label="Source diversity" conf="HIGH">{d.sourceCount} distinct sources active</Row>
          <Row label="Theaters" conf="HIGH">{d.theaters.length} active theaters with reporting</Row>
        </div>

        <p className="text-[10px] font-bold text-zinc-300 tracking-widest uppercase mb-3">1b. Theater Coverage</p>
        <div className="space-y-0.5">
          {d.theaters.length === 0 ? (
            <p className="text-[10px] text-zinc-600 italic">No theater data — ingest pipeline may be warming up.</p>
          ) : (
            d.theaters.map(t => (
              <Row key={t.name} label={t.name} conf={t.avgConf >= 75 ? 'HIGH' : t.avgConf >= 55 ? 'MOD' : 'LOW'}>
                {t.count} items · {t.verified}/{t.count} verified ·{' '}
                <span className={confColor(t.avgConf)}>avg conf {t.avgConf}%</span>
                {t.topTitle && (
                  <span className="text-zinc-500"> — top: <span className="text-zinc-300">{t.topTitle.slice(0, 90)}{t.topTitle.length > 90 ? '…' : ''}</span></span>
                )}
              </Row>
            ))
          )}
        </div>
      </div>

      {/* ── SECTION 2: KEY DEVELOPMENTS ── */}
      <div className="tac-card p-5">
        <SectionHeader num="2" title="Key Developments" />
        {d.keyDevelopments.length === 0 ? (
          <p className="text-[10px] text-zinc-600 italic">No verified developments in last 24h — awaiting ingest cycle.</p>
        ) : (
          <div className="space-y-3">
            {d.keyDevelopments.map((dev, i) => (
              <div key={i} className="flex gap-3 text-[10px]">
                <span className="shrink-0 text-[9px] font-bold text-emerald-700 tracking-widest pt-0.5">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 space-y-0.5">
                  <p className="text-zinc-200">{dev.title}</p>
                  <div className="flex items-center gap-2 text-[9px] text-zinc-600">
                    <span className="text-zinc-500">[{dev.theater}]</span>
                    <span className={confColor(dev.confidence)}>{dev.confidence}% conf</span>
                    {dev.verified && (
                      <span className="flex items-center gap-0.5 text-emerald-500">
                        <CheckCircle2 size={8} /> VERIFIED
                      </span>
                    )}
                    {dev.source && <span className="text-zinc-700">· {dev.source}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── SECTION 3: ORACLE THREAT ASSESSMENT ── */}
      <div className="tac-card p-5">
        <SectionHeader num="3" title="ORACLE-9 Threat Assessment" />
        {d.topThreats.length === 0 ? (
          <p className="text-[10px] text-zinc-600 italic">ORACLE-9 threat model processing…</p>
        ) : (
          <div className="space-y-2">
            {d.topThreats.map((threat, i) => (
              <div key={i} className="flex items-center gap-3 text-[10px]">
                <div className="shrink-0 w-6 text-zinc-600 text-[9px] font-bold">{String(i + 1).padStart(2, '0')}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-zinc-200">{threat.label}</span>
                    <span className={`text-[8px] font-bold border px-1 py-0.5 rounded-sm ${severityBadge(threat.severity)}`}>
                      {threat.severity}
                    </span>
                    {trendIcon(threat.trend)}
                    <span className="text-zinc-600 text-[9px]">[{threat.domain}]</span>
                  </div>
                  <div className="flex items-center gap-1 mt-1">
                    <div className="h-1 rounded-full bg-zinc-800 flex-1 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          threat.probability >= 70 ? 'bg-red-500' :
                          threat.probability >= 45 ? 'bg-amber-500' : 'bg-emerald-600'
                        }`}
                        style={{ width: `${threat.probability}%` }}
                      />
                    </div>
                    <span className={`text-[9px] font-bold w-8 text-right ${confColor(threat.probability)}`}>
                      {threat.probability}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── SECTION 4: ECONOMICS / COMPASS ── */}
      <div className="tac-card p-5">
        <SectionHeader num="4" title="COMPASS Economic Cascade" />
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { label: 'Brent Crude',      value: `$${d.economics.brentUsd.toFixed(1)}/bbl`,    icon: <BarChart2  size={11} className="text-amber-500" /> },
            { label: 'Hormuz Throughput', value: `${d.economics.hormuzThroughputMbpd.toFixed(1)} Mbpd`, icon: <Activity size={11} className="text-blue-400" /> },
            { label: 'Lloyd War Risk',    value: `${d.economics.lloydWarRiskPct.toFixed(1)}%`,  icon: <Zap       size={11} className="text-red-400" /> },
            { label: 'CPI Impulse',       value: `+${d.economics.globalCpiImpulsePp.toFixed(2)} pp`, icon: <TrendingUp size={11} className="text-orange-400" /> },
            { label: 'DXY Move',          value: `${d.economics.dxyMovePp >= 0 ? '+' : ''}${d.economics.dxyMovePp.toFixed(2)} pp`, icon: <Globe size={11} className="text-zinc-400" /> },
          ].map(({ label, value, icon }) => (
            <div key={label} className="bg-zinc-900/40 rounded-sm p-3 border border-zinc-800 flex items-start gap-2">
              <div className="mt-0.5">{icon}</div>
              <div>
                <p className="text-[8px] text-zinc-600 tracking-widest uppercase">{label}</p>
                <p className="text-[12px] font-bold text-zinc-200 mt-0.5">{value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── SECTION 5: PIPELINE HEALTH (AI) ── */}
      {d.aiPipelineHealth && (
        <div className="tac-card p-5">
          <SectionHeader num="5" title="AI Pipeline Health" />
          <div className="space-y-0.5">
            <Row label="Data quality" conf={d.aiPipelineHealth.dataQuality === 'HIGH' ? 'HIGH' : d.aiPipelineHealth.dataQuality === 'MEDIUM' ? 'MOD' : 'LOW'}>
              {d.aiPipelineHealth.dataQuality}
            </Row>
            {d.aiPipelineHealth.gaps.length > 0 && (
              <Row label="Coverage gaps" conf="LOW">
                {d.aiPipelineHealth.gaps.join(' · ')}
              </Row>
            )}
            {d.aiPipelineHealth.biasWarnings.length > 0 && (
              <Row label="Bias warnings" conf="MOD">
                {d.aiPipelineHealth.biasWarnings.join(' · ')}
              </Row>
            )}
            {d.aiPipelineHealth.recommendations.length > 0 && (
              <Row label="Recommendations">
                {d.aiPipelineHealth.recommendations.join(' · ')}
              </Row>
            )}
          </div>
        </div>
      )}

      {/* ── SECTION 6: INTELLIGENCE GAPS ── */}
      <div className="tac-card p-5">
        <SectionHeader num="6" title="Intelligence Gaps" />
        <div className="space-y-0.5">
          {d.theaters.filter(t => t.count < 3).length === 0 ? (
            <p className="text-[10px] text-zinc-400">All theaters reporting ≥3 items. No critical coverage gaps.</p>
          ) : (
            d.theaters.filter(t => t.count < 3).map(t => (
              <Row key={t.name} label={t.name} conf="LOW">
                Only {t.count} item{t.count !== 1 ? 's' : ''} — sparse coverage. Recommend OSINT tasking.
              </Row>
            ))
          )}
        </div>
      </div>

      {/* footer timestamp */}
      <div className="text-[8px] text-zinc-700 tracking-widest uppercase flex items-center gap-2 pb-2">
        <Wifi size={8} className="text-zinc-700" />
        NEXUS LIVE DIGEST · DAY {d.conflictDay} · GENERATED {new Date(d.generatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC
        · AI {d.aiAvailable ? 'ONLINE' : 'OFFLINE'}
      </div>
    </div>
  )
}
