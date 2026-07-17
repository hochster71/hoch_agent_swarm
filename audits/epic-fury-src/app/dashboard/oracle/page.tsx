'use client'

/**
 * /dashboard/oracle — ORACLE-9 Prediction Calibration Center
 *
 * Displays live ORACLE-9 threat probabilities alongside historical
 * prediction accuracy, Brier scores, and calibration metrics.
 *
 * "Snapshot ORACLE" logs current predictions to the calibration table.
 * "Evaluate Expired" triggers LLM-based auto-evaluation of predictions
 * whose time windows have elapsed.
 */

import { useCallback, useState } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Activity, AlertTriangle, CheckCircle2, Clock, RefreshCw,
  Target, TrendingUp, XCircle, Zap, BarChart3, HelpCircle,
} from 'lucide-react'

// ─── Types ──────────────────────────────────────────────────────────────────

type ThreatSeverity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'MINIMAL'

interface LiveThreat {
  id:          string
  label:       string
  domain:      string
  probability: number      // 0–1
  windowHours: number
  severity:    ThreatSeverity
  trend:       'UP' | 'DOWN' | 'STABLE'
  topSignal:   string
  ciLow:       number
  ciHigh:      number
  aiProbability: number | null
}

interface OracleResponse {
  threats:      LiveThreat[]
  conflictDay:  number
  modelVersion: string
  generatedAt:  string
}

interface CalibrationRow {
  id:               string
  prediction_key:   string
  conflict_day:     number
  threat_label:     string
  predicted_prob:   number
  window_hours:     number
  actual_outcome:   string | null
  accuracy_score:   number | null
  evaluation_notes: string | null
  expires_at:       string
  created_at:       string
}

interface CalibrationStats {
  total:         number
  evaluated:     number
  pending:       number
  expiredUneval: number
  occurred:      number
  didNotOccur:   number
  partial:       number
  unknown:       number
  brierScore:    number | null
  hitRate:       number | null
  avgAccuracy:   number | null
}

interface CalibrationResponse {
  predictions: CalibrationRow[]
  stats:       CalibrationStats
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const SEV_COLOR: Record<ThreatSeverity, string> = {
  CRITICAL: 'text-red-400',
  HIGH:     'text-orange-400',
  MODERATE: 'text-yellow-400',
  LOW:      'text-blue-400',
  MINIMAL:  'text-slate-400',
}

const SEV_BAR: Record<ThreatSeverity, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-500',
  MODERATE: 'bg-yellow-500',
  LOW:      'bg-blue-500',
  MINIMAL:  'bg-slate-600',
}

const OUTCOME_BADGE: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
  OCCURRED:      { label: 'OCCURRED',      cls: 'bg-red-950/60 text-red-400 border-red-700/40',     icon: <AlertTriangle size={10} /> },
  DID_NOT_OCCUR: { label: 'DID NOT OCCUR', cls: 'bg-green-950/60 text-green-400 border-green-700/40', icon: <CheckCircle2 size={10} /> },
  PARTIAL:       { label: 'PARTIAL',       cls: 'bg-yellow-950/60 text-yellow-400 border-yellow-700/40', icon: <Activity size={10} /> },
  UNKNOWN:       { label: 'UNKNOWN',       cls: 'bg-slate-900/60 text-slate-400 border-slate-700/40',  icon: <HelpCircle size={10} /> },
}

function brierColor(score: number): string {
  if (score < 0.10) return 'text-green-400'
  if (score < 0.20) return 'text-yellow-400'
  if (score < 0.30) return 'text-orange-400'
  return 'text-red-400'
}

function brierLabel(score: number): string {
  if (score < 0.10) return 'EXCELLENT'
  if (score < 0.20) return 'GOOD'
  if (score < 0.30) return 'FAIR'
  return 'POOR'
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function fmtProb(p: number): string {
  return `${Math.round(p)}%`
}

function fmtProbFraction(p: number): string {
  // p is stored as 0-100 in DB
  return `${Math.round(p)}%`
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000)  return `${Math.floor(diff / 1000)}s ago`
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return `${Math.floor(diff / 86_400_000)}d ago`
}

function isExpired(expires_at: string): boolean {
  return new Date(expires_at) < new Date()
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function OracleCalibrationPage() {
  const [oracle,     setOracle]     = useState<OracleResponse | null>(null)
  const [calibData,  setCalibData]  = useState<CalibrationResponse | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [snapLoading, setSnapLoading] = useState(false)
  const [evalLoading, setEvalLoading] = useState(false)
  const [snapMsg,    setSnapMsg]    = useState<string | null>(null)
  const [evalMsg,    setEvalMsg]    = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState('')

  const fetchAll = useCallback(async () => {
    try {
      const [oracleRes, calibRes] = await Promise.all([
        fetch('/api/oracle', { cache: 'no-store' }),
        fetch('/api/intel/calibration', { cache: 'no-store' }),
      ])

      if (oracleRes.ok) {
        const d = await oracleRes.json() as OracleResponse
        setOracle(d)
      }
      if (calibRes.ok) {
        const d = await calibRes.json() as CalibrationResponse
        setCalibData(d)
      }
      setLastRefresh(new Date().toLocaleTimeString('en-US', { hour12: false }) + 'Z')
    } catch { /* non-fatal */ } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchAll, 30_000)

  // Snapshot current oracle threats → calibration table
  const handleSnapshot = useCallback(async () => {
    if (!oracle?.threats.length) return
    setSnapLoading(true)
    setSnapMsg(null)
    try {
      const threats = oracle.threats.map(t => ({
        label:       t.label,
        probability: t.aiProbability ?? t.probability,
        windowHours: t.windowHours,
      }))
      const res = await fetch('/api/intel/calibration', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ threats }),
      })
      const d = await res.json() as { count?: number; error?: string }
      if (d.error) throw new Error(d.error)
      setSnapMsg(`Logged ${d.count ?? 0} predictions — Day ${oracle.conflictDay}`)
      void fetchAll()
    } catch (e) {
      setSnapMsg(`Error: ${e instanceof Error ? e.message : 'Snapshot failed'}`)
    } finally {
      setSnapLoading(false)
    }
  }, [oracle, fetchAll])

  // Trigger LLM evaluation of expired predictions
  const handleEvaluate = useCallback(async () => {
    setEvalLoading(true)
    setEvalMsg(null)
    try {
      const res = await fetch('/api/intel/calibration', { method: 'PATCH' })
      const d = await res.json() as { evaluated?: number; error?: string }
      if (d.error) throw new Error(d.error)
      setEvalMsg(`Evaluated ${d.evaluated ?? 0} expired predictions`)
      void fetchAll()
    } catch (e) {
      setEvalMsg(`Error: ${e instanceof Error ? e.message : 'Evaluation failed'}`)
    } finally {
      setEvalLoading(false)
    }
  }, [fetchAll])

  const stats = calibData?.stats
  const predictions = calibData?.predictions ?? []

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-64 bg-slate-800 animate-pulse rounded" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1,2,3,4].map(i => <div key={i} className="h-20 bg-slate-800/60 animate-pulse rounded" />)}
        </div>
        <div className="h-64 bg-slate-800/40 animate-pulse rounded" />
      </div>
    )
  }

  return (
    <div className="space-y-5">

      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-orange-400" />
          <h1 className="text-sm font-bold tracking-widest text-orange-300 uppercase">
            ORACLE-9 Calibration Center
          </h1>
          <span className="text-[10px] text-slate-500 font-mono">
            {oracle?.modelVersion ?? '—'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 font-mono">
            {lastRefresh ? `Updated ${lastRefresh}` : ''}
          </span>
          <button
            onClick={() => { void fetchAll() }}
            className="flex items-center justify-center w-10 h-10 text-slate-500 hover:text-emerald-300 border border-zinc-800/50 hover:border-emerald-800 rounded-lg active:scale-95 transition-all duration-150"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* ── Accuracy Stats Banner ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        {/* Brier Score */}
        <div className="bg-slate-900/70 border border-slate-700/50 rounded-sm p-3">
          <p className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mb-1">Brier Score</p>
          {stats?.brierScore != null ? (
            <>
              <p className={`text-xl font-mono font-bold ${brierColor(stats.brierScore)}`}>
                {stats.brierScore.toFixed(3)}
              </p>
              <p className={`text-[9px] font-mono ${brierColor(stats.brierScore)}`}>
                {brierLabel(stats.brierScore)}
              </p>
            </>
          ) : (
            <p className="text-slate-500 text-sm font-mono">—</p>
          )}
        </div>

        {/* Hit Rate */}
        <div className="bg-slate-900/70 border border-slate-700/50 rounded-sm p-3">
          <p className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mb-1">Hit Rate</p>
          {stats?.hitRate != null ? (
            <>
              <p className={`text-xl font-mono font-bold ${stats.hitRate >= 70 ? 'text-green-400' : stats.hitRate >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                {stats.hitRate}%
              </p>
              <p className="text-[9px] text-slate-500 font-mono">{stats.evaluated} evaluated</p>
            </>
          ) : (
            <p className="text-slate-500 text-sm font-mono">—</p>
          )}
        </div>

        {/* Avg Accuracy */}
        <div className="bg-slate-900/70 border border-slate-700/50 rounded-sm p-3">
          <p className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mb-1">Avg Accuracy</p>
          {stats?.avgAccuracy != null ? (
            <>
              <p className="text-xl font-mono font-bold text-emerald-400">{stats.avgAccuracy}/10</p>
              <p className="text-[9px] text-slate-500 font-mono">LLM-scored</p>
            </>
          ) : (
            <p className="text-slate-500 text-sm font-mono">—</p>
          )}
        </div>

        {/* Total Predictions */}
        <div className="bg-slate-900/70 border border-slate-700/50 rounded-sm p-3">
          <p className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mb-1">Total Logged</p>
          <p className="text-xl font-mono font-bold text-slate-300">{stats?.total ?? 0}</p>
          <p className="text-[9px] text-slate-500 font-mono">
            {stats?.pending ?? 0} pending · {stats?.expiredUneval ?? 0} expired
          </p>
        </div>

        {/* Outcome breakdown */}
        <div className="bg-slate-900/70 border border-slate-700/50 rounded-sm p-3">
          <p className="text-[9px] text-slate-500 uppercase tracking-widest font-mono mb-1">Outcomes</p>
          <div className="text-[10px] font-mono space-y-0.5">
            <div className="flex justify-between">
              <span className="text-red-400">OCCURRED</span>
              <span className="text-slate-300">{stats?.occurred ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-400">NOT OCC</span>
              <span className="text-slate-300">{stats?.didNotOccur ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-yellow-400">PARTIAL</span>
              <span className="text-slate-300">{stats?.partial ?? 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Actions ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => { void handleSnapshot() }}
          disabled={snapLoading || !oracle?.threats.length}
          className="flex items-center gap-2 px-4 min-h-[44px] text-[11px] font-mono font-bold
            bg-orange-950/50 border border-orange-700/50 text-orange-300
            hover:bg-orange-900/60 hover:border-orange-500/60
            disabled:opacity-40 disabled:cursor-not-allowed
            rounded-lg active:scale-95 transition-all duration-150"
        >
          <Target size={14} />
          {snapLoading ? 'Snapshotting…' : `Snapshot ORACLE (${oracle?.threats.length ?? 0} threats)`}
        </button>

        {(stats?.expiredUneval ?? 0) > 0 && (
          <button
            onClick={() => { void handleEvaluate() }}
            disabled={evalLoading}
            className="flex items-center gap-2 px-4 min-h-[44px] text-[11px] font-mono font-bold
              bg-blue-950/50 border border-blue-700/50 text-blue-300
              hover:bg-blue-900/60 hover:border-blue-500/60
              disabled:opacity-40 disabled:cursor-not-allowed
              rounded-lg active:scale-95 transition-all duration-150"
          >
            <Zap size={14} />
            {evalLoading ? 'Evaluating…' : `Evaluate Expired (${stats?.expiredUneval})`}
          </button>
        )}

        {snapMsg && (
          <span className={`text-[10px] font-mono ${snapMsg.startsWith('Error') ? 'text-red-400' : 'text-emerald-400'}`}>
            {snapMsg}
          </span>
        )}
        {evalMsg && (
          <span className={`text-[10px] font-mono ${evalMsg.startsWith('Error') ? 'text-red-400' : 'text-blue-300'}`}>
            {evalMsg}
          </span>
        )}
      </div>

      {/* ── Two-column layout: live threats + calibration history ─────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Live ORACLE Threats ─────────────────────────────────────────── */}
        <div className="bg-slate-900/60 border border-slate-700/50 rounded-sm overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
            <div className="flex items-center gap-1.5">
              <Activity size={11} className="text-orange-400" />
              <span className="text-[10px] font-mono font-bold text-orange-300 uppercase tracking-widest">
                Live Threat Probabilities
              </span>
            </div>
            {oracle?.conflictDay && (
              <span className="text-[9px] text-slate-500 font-mono">Day {oracle.conflictDay}</span>
            )}
          </div>

          {!oracle?.threats.length ? (
            <div className="p-4 text-center text-slate-500 text-xs font-mono">ORACLE offline</div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {oracle.threats
                .slice()
                .sort((a, b) => (b.aiProbability ?? b.probability) - (a.aiProbability ?? a.probability))
                .map(t => {
                  const p    = t.aiProbability ?? t.probability
                  const pPct = Math.round(p * 100)
                  return (
                    <div key={t.id} className="px-3 py-2">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <div>
                          <p className={`text-[11px] font-mono font-semibold ${SEV_COLOR[t.severity]}`}>
                            {t.label}
                          </p>
                          <p className="text-[9px] text-slate-500 font-mono truncate max-w-[220px]">
                            {t.domain} · {t.windowHours}h window
                          </p>
                        </div>
                        <span className={`text-sm font-mono font-bold tabular-nums shrink-0 ${SEV_COLOR[t.severity]}`}>
                          {pPct}%
                        </span>
                      </div>
                      <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${SEV_BAR[t.severity]}`}
                          style={{ width: `${pPct}%` }}
                        />
                      </div>
                      {t.aiProbability != null && (
                        <p className="text-[8px] text-slate-600 font-mono mt-0.5">
                          AI-adj: {Math.round(t.aiProbability * 100)}%  ·  Base: {Math.round(t.probability * 100)}%
                          · CI [{Math.round(t.ciLow * 100)}–{Math.round(t.ciHigh * 100)}%]
                        </p>
                      )}
                    </div>
                  )
                })}
            </div>
          )}
        </div>

        {/* Calibration Accuracy Chart ──────────────────────────────────── */}
        <div className="bg-slate-900/60 border border-slate-700/50 rounded-sm overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-slate-800">
            <BarChart3 size={11} className="text-blue-400" />
            <span className="text-[10px] font-mono font-bold text-blue-300 uppercase tracking-widest">
              Calibration Accuracy Chart
            </span>
          </div>

          {predictions.filter(p => p.actual_outcome).length === 0 ? (
            <div className="p-6 text-center">
              <Target size={24} className="text-slate-700 mx-auto mb-2" />
              <p className="text-slate-500 text-xs font-mono">No evaluated predictions yet</p>
              <p className="text-slate-600 text-[10px] font-mono mt-1">
                Snapshot ORACLE threats and wait for windows to expire
              </p>
            </div>
          ) : (
            <div className="p-3 space-y-2">
              {/* Bucket-based calibration bars: group by predicted probability decile */}
              {(() => {
                const buckets: Record<string, { pred: number; tot: number; hit: number }> = {
                  '0-20%':   { pred: 10,  tot: 0, hit: 0 },
                  '20-40%':  { pred: 30,  tot: 0, hit: 0 },
                  '40-60%':  { pred: 50,  tot: 0, hit: 0 },
                  '60-80%':  { pred: 70,  tot: 0, hit: 0 },
                  '80-100%': { pred: 90,  tot: 0, hit: 0 },
                }
                const evaluated = predictions.filter(p => p.actual_outcome && p.actual_outcome !== 'UNKNOWN')
                for (const p of evaluated) {
                  const pct = p.predicted_prob // 0-100
                  const key = pct < 20  ? '0-20%'
                            : pct < 40  ? '20-40%'
                            : pct < 60  ? '40-60%'
                            : pct < 80  ? '60-80%'
                            : '80-100%'
                  buckets[key].tot++
                  if (p.actual_outcome === 'OCCURRED') buckets[key].hit++
                  if (p.actual_outcome === 'PARTIAL')  buckets[key].hit += 0.5
                }
                return Object.entries(buckets).map(([label, b]) => {
                  const actualPct = b.tot > 0 ? Math.round((b.hit / b.tot) * 100) : null
                  return (
                    <div key={label}>
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-[9px] text-slate-400 font-mono w-14">{label}</span>
                        <span className="text-[9px] text-slate-500 font-mono">{b.tot} preds</span>
                        {actualPct != null ? (
                          <span className="text-[9px] font-mono text-emerald-300">{actualPct}% actual</span>
                        ) : (
                          <span className="text-[9px] text-slate-600 font-mono">no data</span>
                        )}
                      </div>
                      <div className="flex gap-1 h-2">
                        {/* Predicted (grey) */}
                        <div className="flex-1 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-slate-500 rounded-full"
                            style={{ width: `${b.pred}%` }}
                            title={`Predicted: ${b.pred}%`}
                          />
                        </div>
                        {/* Actual (orange) */}
                        <div className="flex-1 bg-slate-800 rounded-full overflow-hidden">
                          {actualPct != null && (
                            <div
                              className={`h-full rounded-full ${actualPct > b.pred ? 'bg-orange-500' : 'bg-emerald-500'}`}
                              style={{ width: `${actualPct}%` }}
                              title={`Actual: ${actualPct}%`}
                            />
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              })()}
              <div className="flex gap-4 pt-1 border-t border-slate-800">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-1.5 bg-slate-500 rounded-full" />
                  <span className="text-[8px] text-slate-500 font-mono">Predicted</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-1.5 bg-emerald-500 rounded-full" />
                  <span className="text-[8px] text-slate-500 font-mono">Actual (under)</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-1.5 bg-orange-500 rounded-full" />
                  <span className="text-[8px] text-slate-500 font-mono">Actual (over)</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Calibration History Table ─────────────────────────────────────── */}
      <div className="bg-slate-900/60 border border-slate-700/50 rounded-sm overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
          <div className="flex items-center gap-1.5">
            <TrendingUp size={11} className="text-emerald-400" />
            <span className="text-[10px] font-mono font-bold text-emerald-300 uppercase tracking-widest">
              Prediction History
            </span>
          </div>
          <span className="text-[9px] text-slate-500 font-mono">{predictions.length} records</span>
        </div>

        {predictions.length === 0 ? (
          <div className="p-6 text-center">
            <Clock size={24} className="text-slate-700 mx-auto mb-2" />
            <p className="text-slate-500 text-xs font-mono">No predictions logged yet</p>
            <p className="text-slate-600 text-[10px] font-mono mt-1">
              Click &ldquo;Snapshot ORACLE&rdquo; to log current threat predictions
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[10px] font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500">
                  <th className="text-left px-3 py-1.5 font-normal">Threat</th>
                  <th className="text-center px-2 py-1.5 font-normal">Day</th>
                  <th className="text-center px-2 py-1.5 font-normal">Predicted</th>
                  <th className="text-center px-2 py-1.5 font-normal">Window</th>
                  <th className="text-center px-2 py-1.5 font-normal">Outcome</th>
                  <th className="text-center px-2 py-1.5 font-normal">Accuracy</th>
                  <th className="text-right px-3 py-1.5 font-normal">Logged</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {predictions.map(p => {
                  const exp    = isExpired(p.expires_at)
                  const badge  = p.actual_outcome ? OUTCOME_BADGE[p.actual_outcome] : null

                  return (
                    <tr key={p.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-3 py-2 max-w-[200px]">
                        <p className="text-slate-200 truncate">{p.threat_label}</p>
                      </td>
                      <td className="px-2 py-2 text-center text-slate-400">
                        {p.conflict_day}
                      </td>
                      <td className="px-2 py-2 text-center">
                        <span className={`font-bold ${
                          p.predicted_prob >= 70 ? 'text-red-400' :
                          p.predicted_prob >= 50 ? 'text-orange-400' :
                          p.predicted_prob >= 30 ? 'text-yellow-400' : 'text-slate-400'
                        }`}>
                          {fmtProbFraction(p.predicted_prob)}
                        </span>
                      </td>
                      <td className="px-2 py-2 text-center text-slate-400">
                        {p.window_hours}h
                      </td>
                      <td className="px-2 py-2 text-center">
                        {badge ? (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] ${badge.cls}`}>
                            {badge.icon}
                            {badge.label}
                          </span>
                        ) : exp ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] bg-slate-900 text-orange-400 border-orange-800/50">
                            <XCircle size={9} />
                            EXPIRED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] bg-slate-900 text-slate-400 border-slate-700/40">
                            <Clock size={9} />
                            PENDING
                          </span>
                        )}
                      </td>
                      <td className="px-2 py-2 text-center">
                        {p.accuracy_score != null ? (
                          <span className={`${
                            p.accuracy_score >= 7 ? 'text-green-400' :
                            p.accuracy_score >= 4 ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {p.accuracy_score}/10
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-500">
                        {timeAgo(p.created_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Info footer ─────────────────────────────────────────────────── */}
      <div className="text-[9px] text-slate-600 font-mono border-t border-slate-800/50 pt-2 space-y-0.5">
        <p>
          <span className="text-slate-500">Brier Score</span>: (1/N)×Σ(predicted−actual)² · lower = better · 0.00 = perfect · 0.25 = no-skill baseline
        </p>
        <p>
          <span className="text-slate-500">Hit Rate</span>: % where predicted ≥50% and occurred, or &lt;50% and did not occur
        </p>
        <p>
          <span className="text-slate-500">Snapshot</span> logs current ORACLE probabilities — window expiry triggers auto-evaluation
        </p>
      </div>

    </div>
  )
}
