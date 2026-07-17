'use client'

/**
 * NEXUS Command Center — /dashboard/nexus
 *
 * Strategic overview page showing live AI pipeline activity,
 * intel accuracy progress, system heartbeat, threat matrix,
 * and economic cascade data — all polling every 30s.
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Cpu, ShieldCheck, DatabaseZap, Activity, TrendingUp,
  RefreshCw, Radio, Zap, Globe2, Target, Clock,
} from 'lucide-react'
import SynthesisPanel from '@/components/SynthesisPanel'
import { getConflictDay } from '@/lib/conflict-day'

// ─── Types ─────────────────────────────────────────────────────────────────

interface IntelStats {
  total:         number
  verified:      number
  heraldAuthored: number
  last24h:       number
  lastAdded:     string | null
  topTheaters:   Array<{ theater: string; count: number }>
}

interface SystemStatus {
  name:     string
  status:   'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'
  lastSeen: string | null
  detail:   string
  metric:   string
}

interface PlatformStatusResponse {
  ok:           boolean
  systems:      SystemStatus[]
  health:       string
  aiAvailable:  boolean
  intelHerald:  number
}

interface OracleThreat {
  label:         string
  domain:        string
  probability:   number
  severity:      'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'MINIMAL'
  trend:         'UP' | 'DOWN' | 'STABLE'
  topSignal:     string
  windowHours:   number
  ciLow:         number
  ciHigh:        number
  // AI-enhanced fields (oracle/enhance)
  aiProbability: number | null
  aiConfidence:  'HIGH' | 'MEDIUM' | 'LOW' | null
  aiKeySignal:   string | null
  aiTrend:       'UP' | 'DOWN' | 'STABLE' | null
}

interface OracleResponse {
  threats:      OracleThreat[]
  conflictDay:  number
  generatedAt:  string
  modelVersion: string
  aiAvailable:  boolean
  intelWindow:  number
}

interface CompassCascade {
  brentUsd:             number
  hormuzThroughputMbpd: number
  lloydWarRiskPct:      number
  globalCpiImpulsePp:   number
  dxyMovePp:            number
  severity:             string
}

interface CompassResponse {
  cascade:     CompassCascade
  conflictDay: number
  generatedAt: string
  modelVersion: string
}

interface ForecastWindow {
  summary:     string
  keyRisk:     string
  probability: number
}

interface ConflictForecast {
  generatedAt:      string
  conflictDay:      number
  window24h:        ForecastWindow
  window72h:        ForecastWindow
  ceasefire30d:     number  // % probability
  escalation30d:    number  // % probability
  keyUncertainties: string[]
  modelConfidence:  'HIGH' | 'MEDIUM' | 'LOW'
}

interface IntelItem {
  id:          string
  title:       string
  theater:     string | null
  confidence:  number | null
  verified:    boolean | null
  source_name: string | null
  created_at:  string
}

// ─── Helpers ───────────────────────────────────────────────────────────────

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never'
  const ms = Date.now() - new Date(iso).getTime()
  const s  = Math.floor(ms / 1000)
  if (s < 60)  return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`
}

// getConflictDay imported from @/lib/conflict-day

const SEV_BAR: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-500',
  MODERATE: 'bg-yellow-500',
  LOW:      'bg-blue-500',
  MINIMAL:  'bg-slate-600',
}
const SEV_TEXT: Record<string, string> = {
  CRITICAL: 'text-red-400',
  HIGH:     'text-orange-400',
  MODERATE: 'text-yellow-400',
  LOW:      'text-blue-400',
  MINIMAL:  'text-slate-400',
}
const SEV_BORDER: Record<string, string> = {
  CRITICAL: 'border-red-800/60',
  HIGH:     'border-orange-800/60',
  MODERATE: 'border-yellow-800/60',
  LOW:      'border-blue-800/60',
  MINIMAL:  'border-slate-700/60',
}
const TREND_GLYPH: Record<string, string> = { UP: '▲', DOWN: '▼', STABLE: '◆' }
const TREND_COLOR: Record<string, string> = { UP: 'text-red-400', DOWN: 'text-green-400', STABLE: 'text-slate-400' }

const STATUS_DOT: Record<string, string> = {
  ONLINE:   'bg-emerald-400',
  DEGRADED: 'bg-amber-400 animate-pulse',
  OFFLINE:  'bg-red-500 animate-pulse',
  UNKNOWN:  'bg-zinc-600',
}
const STATUS_TEXT: Record<string, string> = {
  ONLINE:   'text-emerald-400',
  DEGRADED: 'text-amber-400',
  OFFLINE:  'text-red-400',
  UNKNOWN:  'text-zinc-500',
}

// ─── Component ─────────────────────────────────────────────────────────────

export default function NexusCommandPage() {
  const [stats,     setStats]     = useState<IntelStats | null>(null)
  const [platform,  setPlatform]  = useState<PlatformStatusResponse | null>(null)
  const [oracle,    setOracle]    = useState<OracleResponse | null>(null)
  const [compass,   setCompass]   = useState<CompassResponse | null>(null)
  const [latest,    setLatest]    = useState<IntelItem[]>([])
  const [forecast,  setForecast]  = useState<ConflictForecast | null>(null)
  const [lastPoll,  setLastPoll]  = useState<Date | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const day = getConflictDay()

  const fetchAll = useCallback(async () => {
    setIsPolling(true)
    try {
      const [a, b, c, d, e, f] = await Promise.allSettled([
        fetch('/api/intel/stats',            { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
        fetch('/api/platform/status',        { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
        fetch('/api/oracle/enhance',         { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
        fetch('/api/compass',                { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
        fetch('/api/intel/latest?limit=12',  { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
        fetch('/api/intel/forecast',         { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
      ])
      if (a.status === 'fulfilled' && a.value) setStats(a.value as IntelStats)
      if (b.status === 'fulfilled' && b.value) setPlatform(b.value as PlatformStatusResponse)
      if (c.status === 'fulfilled' && c.value) setOracle(c.value as OracleResponse)
      if (d.status === 'fulfilled' && d.value) setCompass(d.value as CompassResponse)
      if (e.status === 'fulfilled' && e.value) {
        const r = e.value as { ok: boolean; items: IntelItem[] }
        setLatest(r.items ?? [])
      }
      if (f.status === 'fulfilled' && f.value) {
        const fr = f.value as { forecast?: ConflictForecast; window24h?: ForecastWindow }
        // API wraps the ConflictForecast under a `forecast` key — unwrap it
        setForecast(fr.forecast ?? (fr.window24h ? (f.value as ConflictForecast) : null))
      }
      setLastPoll(new Date())
    } finally {
      setIsPolling(false)
    }
  }, [])

  useSmartPoll(fetchAll, 30_000)

  // ─── Derived ─────────────────────────────────────────────────────────────
  const total        = stats?.total ?? 0
  const verified     = stats?.verified ?? 0
  const authored     = stats?.heraldAuthored ?? 0
  const last24h      = stats?.last24h ?? 0
  const accuracy     = total > 0 ? Math.round((verified / total) * 100) : 0
  const aiRatio      = total > 0 ? Math.round((authored / total) * 100) : 0
  const onlineCount  = platform?.systems.filter(s => s.status === 'ONLINE').length ?? 0
  const totalSys     = platform?.systems.length ?? 7
  // API returns 'ALL GREEN' | 'DEGRADED' | 'PARTIAL' — normalize to 3-level
  const rawHealth    = platform?.health ?? ''
  const health       = rawHealth === 'ALL GREEN' ? 'green' : rawHealth === 'PARTIAL' ? 'yellow' : rawHealth === 'DEGRADED' ? 'red' : 'green'
  const topThreats   = oracle?.threats.slice(0, 5) ?? []

  const accuracyColor =
    accuracy >= 85 ? 'text-emerald-300' :
    accuracy >= 65 ? 'text-amber-300'   : 'text-red-300'

  const accuracyBarBg =
    accuracy >= 85
      ? 'from-emerald-700 to-emerald-400'
      : accuracy >= 65
      ? 'from-amber-700 to-amber-400'
      : 'from-red-700 to-red-400'

  const healthDot =
    health === 'green'  ? 'bg-emerald-400 animate-pulse' :
    health === 'yellow' ? 'bg-amber-400 animate-pulse'   : 'bg-red-500 animate-pulse'

  const healthText =
    health === 'green'  ? 'text-emerald-400' :
    health === 'yellow' ? 'text-amber-400'   : 'text-red-400'

  // ─── Render ──────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4 max-w-screen-xl">

      {/* ── HEADER ─────────────────────────────────────────────────────── */}
      <div className="tac-card p-4">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-3">
            <Zap size={14} className="text-emerald-400 animate-pulse" />
            <div>
              <p className="text-[8px] tracking-[0.3em] text-zinc-500 uppercase">
                Operation Epic Fury — Strategic Overview
              </p>
              <p className="text-sm font-bold tracking-widest text-emerald-300 uppercase glow-green" suppressHydrationWarning>
                NEXUS Command Center — Day {day}
              </p>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 ml-4 px-3 py-1.5 border border-emerald-900/60 bg-emerald-950/20 rounded-sm">
              <span className={`inline-block w-1.5 h-1.5 rounded-full ${healthDot}`} />
              <span className={`text-[9px] tracking-widest uppercase font-bold ${healthText}`}>
                {onlineCount}/{totalSys} SYSTEMS ONLINE
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastPoll && (
              <span className="text-[8px] text-zinc-600 font-mono tracking-widest">
                SYNCED {lastPoll.toLocaleTimeString('en-US', { hour12: false })}Z
              </span>
            )}
            <button
              onClick={() => void fetchAll()}
              disabled={isPolling}
              className="flex items-center justify-center w-10 h-10 text-zinc-600 hover:text-emerald-400 transition-all duration-150 border border-zinc-800 hover:border-emerald-800 rounded-lg active:scale-95 disabled:opacity-40"
              title="Force refresh all data"
            >
              <RefreshCw size={14} className={isPolling ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* ── ACCURACY PROGRESS BAR ──────────────────────────────────────── */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck size={10} className="text-emerald-400" />
              <span className="text-[9px] tracking-[0.25em] text-zinc-500 uppercase">
                Platform Accuracy — Verified / Total Intel
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-sm font-bold font-mono tabular-nums ${accuracyColor}`}>
                {total > 0 ? `${accuracy}%` : '–'}
              </span>
              <span className="text-[9px] text-zinc-700 tracking-widest">→ TARGET 100%</span>
            </div>
          </div>
          <div className="h-4 w-full bg-zinc-900 rounded-sm overflow-hidden border border-zinc-800">
            <div
              className={`h-full bg-gradient-to-r ${accuracyBarBg} transition-all duration-1000`}
              style={{ width: total > 0 ? `${accuracy}%` : '0%' }}
            >
              {/* inner shimmer stripe */}
              <div className="h-full w-full opacity-40 bg-[repeating-linear-gradient(90deg,transparent,transparent_8px,rgba(255,255,255,0.15)_8px,rgba(255,255,255,0.15)_10px)]" />
            </div>
          </div>
          <div className="flex justify-between text-[8px] text-zinc-700 font-mono tracking-widest">
            <span>0%</span>
            <span className="text-zinc-600">
              {verified.toLocaleString()} VERIFIED / {total.toLocaleString()} TOTAL
              {last24h > 0 && <span className="text-emerald-700 ml-2">+{last24h} IN 24H</span>}
            </span>
            <span>100%</span>
          </div>
        </div>
      </div>

      {/* ── KPI TILES ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Intel DB */}
        <div className="tac-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] tracking-widest text-zinc-500 uppercase">Intel DB</span>
            <DatabaseZap size={11} className="text-violet-500" />
          </div>
          <p className="text-2xl font-bold tabular-nums text-violet-300 font-mono">
            {total > 0 ? total.toLocaleString() : <span className="text-zinc-600 text-lg">—</span>}
          </p>
          <div className="space-y-0.5">
            <p className="text-[9px] text-zinc-600">Total intelligence items</p>
            {last24h > 0 && (
              <p className="text-[9px] text-emerald-500 font-mono">+{last24h} new in 24h</p>
            )}
            {total === 0 && (
              <p className="text-[9px] text-zinc-700 animate-pulse">Waiting for ingest cron…</p>
            )}
          </div>
        </div>

        {/* Accuracy */}
        <div className="tac-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] tracking-widest text-zinc-500 uppercase">Accuracy</span>
            <ShieldCheck size={11} className="text-emerald-500" />
          </div>
          <p className={`text-2xl font-bold tabular-nums font-mono ${total > 0 ? accuracyColor : 'text-zinc-600'}`}>
            {total > 0 ? `${accuracy}%` : '—'}
          </p>
          <div className="space-y-1">
            <p className="text-[9px] text-zinc-600">{verified} items cross-verified</p>
            {total > 0 && (
              <div className="h-1.5 w-full bg-zinc-800 rounded-full">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${accuracyBarBg} transition-all duration-700`}
                  style={{ width: `${accuracy}%` }}
                />
              </div>
            )}
          </div>
        </div>

        {/* AI-Authored */}
        <div className="tac-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] tracking-widest text-zinc-500 uppercase">AI-Authored</span>
            <Cpu size={11} className="text-sky-500" />
          </div>
          <p className="text-2xl font-bold tabular-nums text-sky-300 font-mono">
            {authored > 0 ? authored.toLocaleString() : <span className="text-zinc-600 text-lg">—</span>}
          </p>
          <div className="space-y-0.5">
            <p className="text-[9px] text-zinc-600">HERALD-3 synthetic intel</p>
            {authored > 0 && (
              <p className="text-[9px] text-sky-700 font-mono">{aiRatio}% of DB AI-authored</p>
            )}
          </div>
        </div>

        {/* Pipeline */}
        <div className="tac-card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] tracking-widest text-zinc-500 uppercase">Pipeline</span>
            <Activity
              size={11}
              className={
                health === 'green'  ? 'text-emerald-500' :
                health === 'yellow' ? 'text-amber-500'   : 'text-red-500'
              }
            />
          </div>
          <p className={`text-2xl font-bold tabular-nums font-mono ${healthText}`}>
            {onlineCount}/{totalSys}
          </p>
          <div className="space-y-0.5">
            <p className="text-[9px] text-zinc-600">AI subsystems online</p>
            {stats?.lastAdded && (
              <p className="text-[9px] text-zinc-500 font-mono">Last intel: {timeAgo(stats.lastAdded)}</p>
            )}
          </div>
        </div>
      </div>

      {/* ── ORACLE-9 + SYSTEM HEARTBEAT ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* ORACLE-9 Threat Matrix — 3/5 */}
        <div className="lg:col-span-3 tac-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Target size={11} className="text-red-400" />
              <span className="tac-section-header">ORACLE-9 Live Threat Matrix</span>
            </div>
            {oracle && (
              <div className="flex items-center gap-1.5">
                {oracle.aiAvailable && (
                  <span className="text-[8px] font-bold tracking-widest text-emerald-500 border border-emerald-900 bg-emerald-950/30 px-1.5 py-0.5 rounded-sm">
                    AI·{oracle.intelWindow ?? 0} signals
                  </span>
                )}
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                <span className="text-[8px] text-zinc-600 font-mono tracking-widest">
                  {oracle.modelVersion} · {timeAgo(oracle.generatedAt)}
                </span>
              </div>
            )}
          </div>

          <div className="space-y-2">
            {topThreats.map((t) => (
              <div
                key={t.label}
                className={`p-3 border rounded-sm space-y-2 ${SEV_BORDER[t.severity] ?? 'border-zinc-800'}`}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-bold tracking-widest uppercase ${SEV_TEXT[t.severity] ?? 'text-zinc-400'}`}>
                      {t.label}
                    </span>
                    <span className="text-[8px] text-zinc-600 tracking-widest uppercase">{t.domain}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-mono ${TREND_COLOR[t.aiTrend ?? t.trend] ?? 'text-zinc-400'}`}>
                      {TREND_GLYPH[t.aiTrend ?? t.trend]}
                    </span>
                    <span className={`text-sm font-bold tabular-nums font-mono ${SEV_TEXT[t.severity] ?? 'text-zinc-300'}`}>
                      {Math.round(t.probability * 100)}%
                    </span>
                    {t.aiProbability != null && (() => {
                      const delta = Math.round(t.aiProbability * 100) - Math.round(t.probability * 100)
                      return (
                        <span className={`text-[8px] font-mono tabular-nums ${
                          delta > 0 ? 'text-red-400' : delta < 0 ? 'text-green-400' : 'text-zinc-500'
                        }`}>
                          AI:{Math.round(t.aiProbability * 100)}%{delta !== 0 && ` (${delta > 0 ? '+' : ''}${delta})`}
                        </span>
                      )
                    })()}
                    <span className={`text-[8px] tracking-widest border px-1.5 py-0.5 rounded-sm ${SEV_TEXT[t.severity] ?? 'text-zinc-400'} ${SEV_BORDER[t.severity] ?? 'border-zinc-700'}`}>
                      {t.severity}
                    </span>
                  </div>
                </div>
                {/* Probability bar with optional AI tick overlay */}
                <div className="relative h-2 w-full bg-zinc-900 rounded-full">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${SEV_BAR[t.severity] ?? 'bg-zinc-600'}`}
                    style={{ width: `${Math.round(t.probability * 100)}%` }}
                  />
                  {t.aiProbability != null && (
                    <div
                      className="absolute top-0 h-full w-0.5 bg-emerald-400 opacity-80 rounded-full"
                      style={{ left: `${Math.round(t.aiProbability * 100)}%` }}
                    />
                  )}
                </div>
                <p className="text-[8px] text-zinc-600 leading-tight">
                  <span className="text-zinc-500">↳ </span>
                  {t.aiKeySignal ?? t.topSignal} — window: {t.windowHours}h — CI90: {Math.round(t.ciLow * 100)}–{Math.round(t.ciHigh * 100)}%
                </p>
              </div>
            ))}
            {topThreats.length === 0 && (
              <div className="text-[9px] text-zinc-600 text-center py-8 tracking-[0.3em] animate-pulse uppercase">
                Loading ORACLE-9 data…
              </div>
            )}
          </div>
        </div>

        {/* System Heartbeat — 2/5 */}
        <div className="lg:col-span-2 tac-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Radio size={11} className="text-emerald-400" />
            <span className="tac-section-header">AI Pipeline Heartbeat</span>
          </div>

          <div className="space-y-1.5">
            {platform?.systems.map((sys) => (
              <div
                key={sys.name}
                className="flex items-center justify-between p-2.5 border border-zinc-800/60 rounded-sm hover:border-zinc-700 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[sys.status] ?? 'bg-zinc-600'}`} />
                  <div>
                    <p className="text-[10px] font-bold tracking-widest uppercase text-zinc-200">{sys.name}</p>
                    {sys.metric && (
                      <p className="text-[8px] text-zinc-600">{sys.metric}</p>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-[9px] tracking-widest uppercase font-bold ${STATUS_TEXT[sys.status] ?? 'text-zinc-500'}`}>
                    {sys.status}
                  </p>
                  <p className="text-[8px] text-zinc-700 font-mono">{timeAgo(sys.lastSeen)}</p>
                </div>
              </div>
            ))}

            {/* Skeleton while loading */}
            {!platform && (
              <div className="space-y-1.5">
                {['HERALD-3', 'ORACLE-9', 'COMPASS', 'INGEST', 'ANALYZE', 'CROSS-REF', 'NEXUS DB'].map(name => (
                  <div
                    key={name}
                    className="flex items-center justify-between p-2.5 border border-zinc-800/60 rounded-sm animate-pulse"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="w-2 h-2 rounded-full bg-zinc-800" />
                      <span className="text-[10px] text-zinc-700 tracking-widest uppercase">{name}</span>
                    </div>
                    <span className="text-[8px] text-zinc-800 tracking-widest">…</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* GPT-4o availability badge */}
          <div
            className={`mt-1 p-2.5 border rounded-sm ${
              platform?.aiAvailable
                ? 'border-emerald-900/60 bg-emerald-950/20'
                : 'border-amber-900/60 bg-amber-950/20'
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <Cpu size={9} className={platform?.aiAvailable ? 'text-emerald-400' : 'text-amber-400'} />
              <span className={`text-[9px] tracking-widest uppercase font-bold ${platform?.aiAvailable ? 'text-emerald-400' : 'text-amber-400'}`}>
                GPT-4o {platform?.aiAvailable ? 'ONLINE' : 'FALLBACK MODE'}
              </span>
            </div>
            {!platform?.aiAvailable && (
              <p className="text-[8px] text-amber-700 text-center mt-0.5">
                Deterministic engines active — AI generation paused
              </p>
            )}
          </div>
        </div>
      </div>

      {/* ── LIVE INTEL STREAM ──────────────────────────────────────────── */}
      <div className="tac-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity size={11} className="text-amber-400" />
            <span className="tac-section-header">Live Intelligence Stream</span>
          </div>
          <div className="flex items-center gap-2">
            {latest.length > 0 && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            )}
            <span className="text-[8px] text-zinc-600 tracking-widest font-mono">
              {latest.length > 0 ? `${latest.length} ITEMS` : 'AWAITING FEED'} · REFRESH 30s
            </span>
          </div>
        </div>

        {latest.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
            {latest.map((item, idx) => (
              <div
                key={item.id}
                className="flex items-start gap-2.5 p-2.5 border border-zinc-800/60 rounded-sm hover:border-zinc-700 transition-colors group"
              >
                <span className="text-[8px] font-mono text-zinc-700 shrink-0 mt-0.5">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="text-[10px] text-zinc-300 leading-snug line-clamp-2 group-hover:text-zinc-200 transition-colors">
                    {item.title}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {item.theater && (
                      <span className="text-[8px] text-zinc-600 tracking-widest uppercase">{item.theater}</span>
                    )}
                    {item.confidence !== null && (
                      <span className={`text-[8px] font-mono font-bold ${
                        (item.confidence ?? 0) >= 80 ? 'text-emerald-500' :
                        (item.confidence ?? 0) >= 60 ? 'text-amber-500' : 'text-zinc-500'
                      }`}>
                        {item.confidence}%
                      </span>
                    )}
                    {item.verified && (
                      <span className="text-[8px] text-emerald-600 tracking-widest">✓ VER</span>
                    )}
                    <span className="text-[8px] text-zinc-700 font-mono ml-auto">
                      {timeAgo(item.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-10 space-y-3">
            <div className="text-[9px] text-zinc-600 tracking-[0.3em] uppercase animate-pulse">
              INGEST PIPELINE ACTIVE — AWAITING FIRST DATA CYCLE
            </div>
            <p className="text-[9px] text-zinc-700 max-w-md mx-auto leading-relaxed">
              The INGEST cron fires every 5 minutes. ORACLE-9 and COMPASS are running on
              deterministic models and do not require database data. Intel stream will
              populate automatically once the first cron cycle completes.
            </p>
            <div className="flex justify-center gap-6 mt-2">
              <div className="text-center">
                <p className="text-[8px] text-zinc-600 tracking-widest uppercase">ORACLE-9</p>
                <p className="text-[9px] text-emerald-500 font-bold">
                  {topThreats.length > 0 ? 'RUNNING' : 'LOADING…'}
                </p>
              </div>
              <div className="text-center">
                <p className="text-[8px] text-zinc-600 tracking-widest uppercase">COMPASS</p>
                <p className="text-[9px] text-emerald-500 font-bold">
                  {compass ? 'RUNNING' : 'LOADING…'}
                </p>
              </div>
              <div className="text-center">
                <p className="text-[8px] text-zinc-600 tracking-widest uppercase">HERALD-3</p>
                <p className="text-[9px] text-amber-500 font-bold">AWAITING DB</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── NEXUS-FORECAST AI — 24h / 72h / 30d ──────────────────────── */}
      <div className="tac-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={11} className="text-violet-400" />
            <span className="tac-section-header">NEXUS-FORECAST — AI Conflict Trajectory</span>
          </div>
          {forecast && (
            <div className="flex items-center gap-1.5">
              <span className={`text-[8px] font-bold tracking-widest border px-1.5 py-0.5 rounded-sm ${
                forecast.modelConfidence === 'HIGH'   ? 'text-emerald-400 border-emerald-800 bg-emerald-950/20' :
                forecast.modelConfidence === 'MEDIUM' ? 'text-amber-400 border-amber-800 bg-amber-950/20' :
                                                         'text-red-400 border-red-800 bg-red-950/20'
              }`}>{forecast.modelConfidence} CONF</span>
              <span className="text-[8px] text-zinc-600 font-mono tracking-widest">{timeAgo(forecast.generatedAt)}</span>
            </div>
          )}
        </div>

        {forecast ? (
          <div className="space-y-3">
            {/* 24h / 72h window cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { label: '24-HOUR WINDOW', win: forecast.window24h, color: 'text-red-400', border: 'border-red-900/40', bg: 'bg-red-950/10' },
                { label: '72-HOUR WINDOW', win: forecast.window72h, color: 'text-amber-400', border: 'border-amber-900/40', bg: 'bg-amber-950/10' },
              ].filter(({ win }) => win != null).map(({ label, win, color, border, bg }) => (
                <div key={label} className={`p-3 border rounded-sm space-y-2 ${border} ${bg}`}>
                  <div className="flex items-center justify-between">
                    <span className={`text-[8px] font-bold tracking-widest uppercase ${color}`}>{label}</span>
                    <span className={`text-sm font-bold font-mono tabular-nums ${color}`}>{win!.probability}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-zinc-900 rounded-full">
                    <div className={`h-full rounded-full transition-all duration-700 ${
                      win!.probability >= 70 ? 'bg-red-500' : win!.probability >= 50 ? 'bg-amber-500' : 'bg-zinc-500'
                    }`} style={{ width: `${win!.probability}%` }} />
                  </div>
                  <p className="text-[9px] text-zinc-400 leading-relaxed line-clamp-3">{win!.summary}</p>
                  <p className="text-[8px] text-zinc-600 leading-tight">
                    <span className="text-zinc-500">↳ KEY RISK: </span>{win!.keyRisk}
                  </p>
                </div>
              ))}
            </div>

            {/* 30-day probability gauges */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 border border-emerald-900/30 bg-emerald-950/10 rounded-sm space-y-1.5">
                <p className="text-[8px] tracking-widest text-zinc-500 uppercase">Ceasefire Probability — 30d</p>
                <div className="flex items-end gap-2">
                  <p className="text-2xl font-bold font-mono tabular-nums text-emerald-400">{forecast.ceasefire30d}%</p>
                  <p className="text-[9px] text-zinc-600 mb-0.5">probability</p>
                </div>
                <div className="h-1.5 w-full bg-zinc-900 rounded-full">
                  <div className="h-full rounded-full bg-emerald-600 transition-all duration-700" style={{ width: `${forecast.ceasefire30d}%` }} />
                </div>
              </div>
              <div className="p-3 border border-red-900/30 bg-red-950/10 rounded-sm space-y-1.5">
                <p className="text-[8px] tracking-widest text-zinc-500 uppercase">Escalation Probability — 30d</p>
                <div className="flex items-end gap-2">
                  <p className="text-2xl font-bold font-mono tabular-nums text-red-400">{forecast.escalation30d}%</p>
                  <p className="text-[9px] text-zinc-600 mb-0.5">probability</p>
                </div>
                <div className="h-1.5 w-full bg-zinc-900 rounded-full">
                  <div className="h-full rounded-full bg-red-600 transition-all duration-700" style={{ width: `${forecast.escalation30d}%` }} />
                </div>
              </div>
            </div>

            {/* Key uncertainties */}
            {forecast.keyUncertainties.length > 0 && (
              <div className="space-y-1">
                <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Key Uncertainties</p>
                {forecast.keyUncertainties.map((u, i) => (
                  <p key={i} className="text-[9px] text-zinc-500 leading-snug">
                    <span className="text-zinc-700 mr-1">◆</span>{u}
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="text-[9px] text-zinc-600 text-center py-6 tracking-[0.3em] animate-pulse uppercase">
            Loading NEXUS-FORECAST…
          </div>
        )}
      </div>

      {/* ── COMPASS ECONOMIC CASCADE ───────────────────────────────────── */}
      <div className="tac-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <TrendingUp size={11} className="text-yellow-400" />
            <span className="tac-section-header">COMPASS Economic Cascade</span>
          </div>
          {compass && (
            <span className="text-[8px] text-zinc-600 font-mono tracking-widest">
              {compass.modelVersion} · Day {compass.conflictDay}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="p-3 border border-yellow-900/40 bg-yellow-950/10 rounded-sm space-y-1">
            <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Brent Crude</p>
            <p className="text-xl font-bold text-yellow-300 font-mono tabular-nums">
              {compass ? `$${compass.cascade.brentUsd.toFixed(1)}` : '—'}
            </p>
            <p className="text-[8px] text-zinc-700">per barrel</p>
          </div>
          <div className="p-3 border border-cyan-900/40 bg-cyan-950/10 rounded-sm space-y-1">
            <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Hormuz Flow</p>
            <p className="text-xl font-bold text-cyan-300 font-mono tabular-nums">
              {compass ? `${compass.cascade.hormuzThroughputMbpd.toFixed(1)}` : '—'}
            </p>
            <p className="text-[8px] text-zinc-700">mb/d throughput</p>
          </div>
          <div className="p-3 border border-orange-900/40 bg-orange-950/10 rounded-sm space-y-1">
            <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Lloyd&apos;s War Risk</p>
            <p className="text-xl font-bold text-orange-300 font-mono tabular-nums">
              {compass ? `${compass.cascade.lloydWarRiskPct.toFixed(2)}%` : '—'}
            </p>
            <p className="text-[8px] text-zinc-700">insurance premium</p>
          </div>
          <div className="p-3 border border-zinc-800 rounded-sm space-y-1">
            <p className="text-[8px] tracking-widest text-zinc-600 uppercase">CPI Impulse</p>
            <p className="text-xl font-bold text-zinc-300 font-mono tabular-nums">
              {compass
                ? `+${compass.cascade.globalCpiImpulsePp.toFixed(2)}pp`
                : '—'}
            </p>
            <p className="text-[8px] text-zinc-700">global inflation push</p>
          </div>
          <div
            className={`p-3 border rounded-sm space-y-1 ${
              compass?.cascade.severity === 'SEVERE'
                ? 'border-red-900/40 bg-red-950/10'
                : compass?.cascade.severity === 'HIGH'
                ? 'border-amber-900/40 bg-amber-950/10'
                : 'border-zinc-800 bg-zinc-900/20'
            }`}
          >
            <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Scenario</p>
            <p className={`text-xl font-bold font-mono ${
              compass?.cascade.severity === 'SEVERE' ? 'text-red-300' :
              compass?.cascade.severity === 'HIGH'   ? 'text-amber-300' : 'text-zinc-300'
            }`}>
              {compass?.cascade.severity ?? '—'}
            </p>
            <p className="text-[8px] text-zinc-700">closure severity</p>
          </div>
        </div>
      </div>

      {/* ── THEATER COVERAGE ───────────────────────────────────────────── */}
      {stats?.topTheaters && stats.topTheaters.length > 0 && (
        <div className="tac-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Globe2 size={11} className="text-blue-400" />
            <span className="tac-section-header">Theater Intelligence Coverage</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
            {stats.topTheaters.map(({ theater, count }) => {
              return (
                <div key={theater} className="p-2.5 border border-zinc-800 rounded-sm space-y-1.5 hover:border-zinc-700 transition-colors">
                  <p className="text-[9px] font-bold tracking-widest uppercase text-zinc-400">{theater}</p>
                  <p className="text-lg font-bold tabular-nums text-zinc-200 font-mono">{count}</p>
                  <div className="space-y-1">
                    <div className="h-1 w-full bg-zinc-800 rounded-full">
                      <div className="h-full rounded-full bg-emerald-600 transition-all duration-700" style={{ width: `${Math.min(100, count * 8)}%` }} />
                    </div>
                    <p className="text-[8px] text-zinc-600 font-mono">{count} items tracked</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── NEXUS LAYER 10 — COMMANDER'S SYNTHESIS ──────────────────────── */}
      <div className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-4">
        <SynthesisPanel />
      </div>

      {/* ── FOOTER ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-[8px] text-zinc-700 font-mono tracking-widest pb-2 px-1">
        <span>NEXUS CMD v1.0 · POLLING 30s</span>
        <span>FPCON DELTA // UNCLASSIFIED // AI LIVE FEED</span>
        <span>
          {lastPoll
            ? `SYNCED ${lastPoll.toISOString().replace('T', ' ').slice(0, 19)}Z`
            : 'INITIALIZING…'}
        </span>
      </div>

    </div>
  )
}
