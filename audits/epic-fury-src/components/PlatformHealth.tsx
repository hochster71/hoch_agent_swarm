'use client'

/**
 * PlatformHealth
 *
 * Shows the live health of all Epic Fury autonomous subsystems.
 * Polls /api/platform/status every 12 seconds.
 * Auto-bootstraps the ingest pipeline on first load when HERALD is OFFLINE.
 *
 * Props:
 *   compact - if true, renders a single horizontal strip (for top of dashboard)
 *             if false (default), renders full card grid
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  RefreshCw, Cpu, Activity, Zap,
  CheckCircle2, AlertTriangle, XCircle, HelpCircle, ShieldAlert,
  Brain, Wifi, WifiOff, RotateCcw, CircleDot, Radio,
} from 'lucide-react'
import type { PlatformStatus, SystemStatus } from '@/app/api/platform/status/route'
import type { HealReport } from '@/app/api/platform/heal/route'
import { buildNeuralState, computeNeuralHealthScore } from '@/lib/neural-map'

type FullStatus = PlatformStatus & { health: string; aiAvailable: boolean; aiAssessment: unknown }

type CircuitState = 'CLOSED' | 'HALF_OPEN' | 'OPEN'

const CIRCUIT_COLOR: Record<CircuitState, string> = {
  CLOSED:    'text-emerald-400',
  HALF_OPEN: 'text-amber-400',
  OPEN:      'text-red-400',
}
const CIRCUIT_BG: Record<CircuitState, string> = {
  CLOSED:    'bg-emerald-950/20 border-emerald-800/40',
  HALF_OPEN: 'bg-amber-950/20 border-amber-800/40',
  OPEN:      'bg-red-950/25 border-red-700/50',
}

type StatusLevel = 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'

const POLL_MS       = 12_000
const HEAL_DEBOUNCE = 120_000  // 2 min between heal attempts

const STATUS_ICON: Record<StatusLevel, React.ElementType> = {
  ONLINE:   CheckCircle2,
  DEGRADED: AlertTriangle,
  OFFLINE:  XCircle,
  UNKNOWN:  HelpCircle,
}

const STATUS_COLOR: Record<StatusLevel, string> = {
  ONLINE:   'text-emerald-400',
  DEGRADED: 'text-amber-400',
  OFFLINE:  'text-red-400',
  UNKNOWN:  'text-zinc-500',
}

const STATUS_RING: Record<StatusLevel, string> = {
  ONLINE:   'border-emerald-800/50',
  DEGRADED: 'border-amber-800/50',
  OFFLINE:  'border-red-800/50',
  UNKNOWN:  'border-zinc-800/40',
}

const STATUS_BG: Record<StatusLevel, string> = {
  ONLINE:   'bg-emerald-950/20',
  DEGRADED: 'bg-amber-950/20',
  OFFLINE:  'bg-red-950/20',
  UNKNOWN:  'bg-zinc-900/20',
}

const HEALTH_BANNER: Record<string, string> = {
  'ALL GREEN': 'bg-emerald-950/30 border-emerald-700/40 text-emerald-300',
  'DEGRADED':  'bg-amber-950/30 border-amber-700/40 text-amber-300',
  'PARTIAL':   'bg-red-950/30 border-red-700/40 text-red-300',
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Awaiting first run'
  const ms = Date.now() - new Date(iso).getTime()
  const s  = Math.floor(ms / 1_000)
  if (s < 10)  return 'Just now'
  if (s < 60)  return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ${m % 60}m ago`
  return `${Math.floor(h / 24)}d ago`
}

interface PlatformHealthProps {
  compact?: boolean
}

export function PlatformHealth({ compact = false }: PlatformHealthProps) {
  const [status, setStatus]         = useState<FullStatus | null>(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [ingesting, setIngesting]   = useState(false)
  const [healing, setHealing]       = useState(false)
  const [healReport, setHealReport] = useState<HealReport | null>(null)
  const [neuralScore, setNeuralScore] = useState<number | null>(null)
  const [countdown, setCountdown]   = useState(POLL_MS / 1000)
  const bootstrapped                = useRef(false)
  const lastHealAttemptMs           = useRef(0)
  const healingRef                  = useRef(false)
  const ingestingRef                = useRef(false)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/platform/status', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as FullStatus
      setStatus(data)
      setError(null)
      // Compute neural health score client-side from status data
      // (avoids fragile self-referential server fetch in heal GET route)
      if (data.systems) {
        const states = buildNeuralState(data.systems)
        setNeuralScore(computeNeuralHealthScore(states))
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
      setCountdown(POLL_MS / 1000)
    }
  }, [])

  // Auto-bootstrap: kick /api/ingest if HERALD never ran
  const triggerIngest = useCallback(async () => {
    if (ingestingRef.current) return
    ingestingRef.current = true
    setIngesting(true)
    try {
      // /api/platform/bootstrap adds CRON_SECRET server-side — no client secret needed
      await fetch('/api/platform/bootstrap', { cache: 'no-store' })
      await fetchStatus()
    } catch { /* non-fatal */ } finally {
      ingestingRef.current = false
      setIngesting(false)
    }
  }, [fetchStatus])

  // Self-Healing Neural Orchestrator — POST /api/platform/heal
  const triggerHeal = useCallback(async () => {
    if (healingRef.current) return
    const nowMs = Date.now()
    if (nowMs - lastHealAttemptMs.current < HEAL_DEBOUNCE) return
    lastHealAttemptMs.current = nowMs
    healingRef.current = true
    setHealing(true)
    try {
      const res = await fetch('/api/platform/heal', {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        const report = await res.json() as HealReport
        setHealReport(report)
        setNeuralScore(report.neuralHealthAfter)
        // Refresh platform status after healing
        await fetchStatus()
      }
    } catch { /* non-fatal */ } finally {
      healingRef.current = false
      setHealing(false)
    }
  }, [fetchStatus])

  useSmartPoll(fetchStatus, POLL_MS)

  // Live countdown ticker
  useEffect(() => {
    const id = setInterval(() => {
      setCountdown(c => (c <= 1 ? POLL_MS / 1000 : c - 1))
    }, 1000)
    return () => clearInterval(id)
  }, [])

  // Auto-bootstrap once when we first learn HERALD has never run
  useEffect(() => {
    if (!status || bootstrapped.current) return
    const herald = status.systems.find(s => s.name.includes('HERALD'))
    if (herald && herald.lastSeen === null) {
      bootstrapped.current = true
      triggerIngest()
    }
  }, [status, triggerIngest])

  // Auto-heal: fire when any system goes OFFLINE (not just degraded)
  useEffect(() => {
    if (!status) return
    const offlineCount = status.systems.filter(s => s.status === 'OFFLINE').length
    if (offlineCount > 0) {
      triggerHeal()
    }
  }, [status, triggerHeal])

  // ── Compact strip mode ──────────────────────────────────────────────────
  if (compact) {
    return (
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1">
          <Cpu className="w-3 h-3 text-zinc-500" />
          <span className="text-[9px] text-zinc-600 tracking-widest">PLATFORM</span>
        </div>

        {loading && <span className="text-[9px] text-zinc-600 animate-pulse">LOADING…</span>}
        {error   && <span className="text-[9px] text-red-500 truncate max-w-48">{error}</span>}

        {status?.systems.map(sys => {
          const level = sys.status as StatusLevel
          const Icon  = STATUS_ICON[level] ?? HelpCircle
          return (
            <div key={sys.name} className="flex items-center gap-1" title={`${sys.name}: ${sys.detail}`}>
              <Icon className={`w-3 h-3 ${STATUS_COLOR[level]} ${level === 'ONLINE' ? 'animate-pulse' : ''}`} />
              <span className={`text-[9px] font-mono tracking-tight ${STATUS_COLOR[level]}`}>
                {sys.name.split(' ')[0]}
              </span>
            </div>
          )
        })}

        {status && (
          <span className={`text-[9px] font-bold tracking-widest ml-auto ${
            status.health === 'ALL GREEN' ? 'text-emerald-400'
            : status.health === 'DEGRADED' ? 'text-amber-400'
            : 'text-red-400'
          }`}>
            ● {status.health}
          </span>
        )}

        {neuralScore !== null && (
          <span className={`text-[9px] font-mono ml-1 ${
            neuralScore >= 80 ? 'text-emerald-500'
            : neuralScore >= 50 ? 'text-amber-500'
            : 'text-red-500'
          }`} title={`Neural health score: ${neuralScore}/100`}>
            ⬡{neuralScore}
          </span>
        )}

        <button
          onClick={fetchStatus}
          className="flex items-center justify-center w-8 h-8 rounded-lg text-zinc-600 hover:text-zinc-400 hover:bg-zinc-800/50 active:scale-95 transition-all ml-1"
          title="Refresh platform status"
          aria-label="Refresh platform status"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    )
  }

  // ── Full card mode ───────────────────────────────────────────────────────
  return (
    <div className="tac-card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-violet-400" />
          <span className="tac-label text-violet-300 tracking-widest">AI PIPELINE HEARTBEAT</span>
          {status && (
            <span className="text-[9px] text-zinc-600 font-mono">
              DAY {status.conflictDay}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Neural health score */}
          {neuralScore !== null && (
            <div className={`flex items-center gap-1 px-2 py-0.5 rounded border text-[9px] font-bold font-mono ${
              neuralScore >= 80 ? 'border-emerald-800/50 text-emerald-400 bg-emerald-950/20'
              : neuralScore >= 50 ? 'border-amber-800/50 text-amber-400 bg-amber-950/20'
              : 'border-red-800/50 text-red-400 bg-red-950/20'
            }`} title="Neural health score">
              <Brain className="w-2.5 h-2.5" />
              {neuralScore}/100
            </div>
          )}
          {/* Countdown */}
          <span className="text-[9px] text-zinc-600 font-mono tabular-nums">
            ↻ {countdown}s
          </span>
          {/* Neural Heal button */}
          <button
            onClick={triggerHeal}
            disabled={healing}
            className={`flex items-center gap-1.5 px-3 min-h-[36px] rounded-lg text-[9px] font-bold tracking-widest border transition-all duration-150 active:scale-95 ${
              healing
                ? 'border-cyan-700/50 text-cyan-400 animate-pulse cursor-wait'
                : 'border-cyan-800/50 text-cyan-500 hover:border-cyan-600 hover:text-cyan-300 hover:bg-cyan-950/20'
            }`}
            title="Trigger self-healing neural recovery"
            aria-label="Trigger self-healing neural recovery"
          >
            <RotateCcw className="w-3 h-3" />
            {healing ? 'HEALING…' : 'SELF-HEAL'}
          </button>
          {/* Force Ingest button */}
          <button
            onClick={triggerIngest}
            disabled={ingesting}
            className={`flex items-center gap-1.5 px-3 min-h-[36px] rounded-lg text-[9px] font-bold tracking-widest border transition-all duration-150 active:scale-95 ${
              ingesting
                ? 'border-amber-700/50 text-amber-400 animate-pulse cursor-wait'
                : 'border-violet-700/50 text-violet-400 hover:border-violet-500 hover:text-violet-300 hover:bg-violet-950/20'
            }`}
            title="Force pipeline ingest now"
            aria-label="Force pipeline ingest now"
          >
            <Zap className="w-3 h-3" />
            {ingesting ? 'INGESTING…' : 'FORCE INGEST'}
          </button>
          <button
            onClick={fetchStatus}
            className="flex items-center justify-center w-9 h-9 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 active:scale-95 transition-all"
            title="Refresh"
            aria-label="Refresh platform status"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-[10px] text-red-400 bg-red-900/20 px-2 py-1 rounded">{error}</div>
      )}

      {/* Missing env-var diagnostics */}
      {status && status.missingEnvVars && status.missingEnvVars.length > 0 && (
        <div className="flex items-start gap-2 px-3 py-2 rounded border border-red-700/50 bg-red-950/30 text-[9px]">
          <ShieldAlert className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-bold text-red-300 tracking-widest">MISSING ENV VARS — SET IN VERCEL PROJECT SETTINGS → ENVIRONMENT VARIABLES</div>
            <div className="font-mono text-red-400">{status.missingEnvVars.join('  ·  ')}</div>
          </div>
        </div>
      )}

      {/* Vercel Hobby plan cron throttle warning */}
      {status && (status as unknown as { cronNote?: string | null }).cronNote && (
        <div className="flex items-start gap-2 px-3 py-2 rounded border border-amber-700/50 bg-amber-950/30 text-[9px]">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-bold text-amber-300 tracking-widest">VERCEL CRON THROTTLED</div>
            <div className="text-amber-400">{(status as unknown as { cronNote: string }).cronNote}</div>
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !status && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-zinc-900/40 border border-zinc-800/40 rounded p-3 h-20 animate-pulse" />
          ))}
        </div>
      )}

      {/* Overall health banner */}
      {status && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded border text-[10px] font-bold tracking-widest ${HEALTH_BANNER[status.health] ?? HEALTH_BANNER['DEGRADED']}`}>
          <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
          PLATFORM STATUS: {status.health}
          <span className="ml-auto font-normal text-zinc-500">
            {new Date(status.generatedAt).toUTCString().slice(0, 22)} UTC
          </span>
        </div>
      )}

      {/* System cards grid */}
      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
          {status.systems.map((sys: SystemStatus) => {
            const level = sys.status as StatusLevel
            const Icon  = STATUS_ICON[level] ?? HelpCircle
            const isOnline = level === 'ONLINE'
            return (
              <div
                key={sys.name}
                className={`rounded border p-3 space-y-1.5 ${STATUS_BG[level]} ${STATUS_RING[level]}`}
              >
                <div className="flex items-center justify-between">
                  <div className="relative flex items-center">
                    <Icon className={`w-3.5 h-3.5 ${STATUS_COLOR[level]}`} />
                    {isOnline && (
                      <span className={`absolute inset-0 rounded-full ${STATUS_COLOR[level]} opacity-40 animate-ping`} />
                    )}
                  </div>
                  <span className={`text-[9px] font-bold tracking-widest ${STATUS_COLOR[level]}`}>
                    {sys.status}
                  </span>
                </div>
                <div className="text-[11px] font-bold text-zinc-200 leading-tight">{sys.name}</div>
                <div className="text-[9px] text-zinc-500 leading-relaxed">{sys.detail}</div>
                {sys.metric && (
                  <div className="text-[9px] text-zinc-400 font-mono">{sys.metric}</div>
                )}
                <div className="text-[9px] text-zinc-600 font-mono">
                  {timeAgo(sys.lastSeen)}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Callout row: top threat + oil price */}
      {status && (status.topThreat || status.oilPrice) && (
        <div className="flex gap-2 flex-wrap">
          {status.topThreat && (
            <div className="flex items-center gap-1.5 bg-red-950/20 border border-red-800/30 rounded px-2 py-1">
              <XCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
              <div>
                <div className="text-[8px] text-zinc-600 tracking-widest">TOP THREAT</div>
                <div className="text-[10px] text-red-300 font-mono truncate max-w-52">{status.topThreat}</div>
              </div>
            </div>
          )}
          {status.oilPrice !== null && status.oilPrice !== undefined && (
            <div className="flex items-center gap-1.5 bg-amber-950/20 border border-amber-800/30 rounded px-2 py-1">
              <Activity className="w-3 h-3 text-amber-400 flex-shrink-0" />
              <div>
                <div className="text-[8px] text-zinc-600 tracking-widest">BRENT CRUDE</div>
                <div className="text-[10px] text-amber-300 font-mono">${status.oilPrice.toFixed(2)}/bbl</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Stats row */}
      {status && (
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 pt-1 border-t border-zinc-800/50">
          {[
            { label: 'INTEL ROWS', value: status.intelTotal },
            { label: 'BY HERALD-3', value: status.intelHerald },
            { label: 'INGEST RUNS', value: status.ingestRuns },
            { label: 'BATCH RUNS',  value: status.batchRuns },
            { label: 'NEWS ITEMS',  value: status.newsItems },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-[9px] text-zinc-600 tracking-widest">{label}</div>
              <div className="text-sm font-bold font-mono text-zinc-300">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* ── Neural Circuit Map ─────────────────────────────────────────────── */}
      {healReport && (
        <div className="border-t border-zinc-800/50 pt-3 space-y-2">
          <div className="flex items-center gap-2">
            <Brain className="w-3.5 h-3.5 text-cyan-400" />
            <span className="tac-label text-cyan-300 tracking-widest text-[9px]">NEURAL CIRCUIT MAP</span>
            <span className={`ml-auto text-[9px] font-mono font-bold ${
              healReport.neuralHealthAfter >= 80 ? 'text-emerald-400'
              : healReport.neuralHealthAfter >= 50 ? 'text-amber-400'
              : 'text-red-400'
            }`}>
              {healReport.neuralHealthBefore} → {healReport.neuralHealthAfter} / 100
            </span>
          </div>

          {/* Neuron grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {healReport.neuronStates.map(n => {
              const circuit = n.circuit as 'CLOSED' | 'HALF_OPEN' | 'OPEN'
              return (
                <div key={n.id} className={`rounded border px-2 py-1.5 space-y-0.5 ${
                  CIRCUIT_BG[circuit]
                }`}>
                  <div className="flex items-center justify-between">
                    <CircleDot className={`w-2.5 h-2.5 ${
                      circuit === 'CLOSED' ? 'text-emerald-400 animate-pulse'
                      : circuit === 'HALF_OPEN' ? 'text-amber-400'
                      : 'text-red-400'
                    }`} />
                    <span className={`text-[8px] font-bold tracking-widest ${CIRCUIT_COLOR[circuit]}`}>
                      {circuit === 'CLOSED' ? 'CLOSED' : circuit === 'HALF_OPEN' ? '½ OPEN' : 'OPEN'}
                    </span>
                  </div>
                  <div className="text-[9px] text-zinc-300 font-bold leading-tight">{n.label}</div>
                  <div className="text-[8px] text-zinc-600 leading-tight truncate" title={n.diagnosis}>{n.diagnosis}</div>
                </div>
              )
            })}
          </div>

          {/* Heal probe results */}
          {healReport.probeResults.length > 0 && (
            <div className="space-y-1">
              <div className="text-[9px] text-zinc-600 tracking-widest">HEAL PROBES — {healReport.actionsAttempted} attempted · {healReport.actionsSucceeded} succeeded</div>
              {healReport.probeResults.map((p, i) => (
                <div key={i} className={`flex items-center gap-2 px-2 py-1 rounded text-[9px] ${
                  p.success
                    ? 'bg-emerald-950/20 border border-emerald-800/30'
                    : 'bg-red-950/20 border border-red-800/30'
                }`}>
                  {p.success
                    ? <Wifi className="w-2.5 h-2.5 text-emerald-400 flex-shrink-0" />
                    : <WifiOff className="w-2.5 h-2.5 text-red-400 flex-shrink-0" />}
                  <span className="text-zinc-300 font-bold">{p.label}</span>
                  <span className="text-zinc-600 font-mono ml-auto">{p.durationMs}ms</span>
                  {p.error && <span className="text-red-400 truncate max-w-32" title={p.error}>{p.error.slice(0, 30)}</span>}
                </div>
              ))}
            </div>
          )}

          {/* AI recovery assessment */}
          {healReport.aiAssessment && (
            <div className="flex items-start gap-2 px-2 py-2 rounded border border-cyan-800/30 bg-cyan-950/10">
              <Radio className="w-3 h-3 text-cyan-400 flex-shrink-0 mt-0.5 animate-pulse" />
              <div className="space-y-0.5">
                <div className="text-[8px] text-cyan-500 tracking-widest font-bold">NEXUS-HEAL AI TRIAGE</div>
                <div className="text-[9px] text-zinc-400">{healReport.aiAssessment.summary}</div>
                {healReport.aiAssessment.risks.length > 0 && (
                  <div className="text-[8px] text-amber-400">
                    ⚠ {healReport.aiAssessment.risks.join(' · ')}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="text-[8px] text-zinc-700 font-mono">
            Healed {new Date(healReport.generatedAt).toUTCString().slice(0, 22)} UTC
            {healReport.loggingOk ? ' · Logged to DB' : ''}
          </div>
        </div>
      )}
    </div>
  )
}
