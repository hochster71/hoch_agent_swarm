'use client'

/**
 * CmdOpsCenter
 *
 * Unified autonomous operations dashboard for the Command Authority Center.
 * Polls 4 endpoints every 30 seconds and merges activity into a single
 * chronological log — every AI decision, cron trigger, and pipeline run.
 *
 * Surfaces:
 *  - Governor 9-layer cycles             /api/governor
 *  - AEC (Autonomous Enhancement Cycle)  /api/intel/autonomous
 *  - Workflow engine runs                /api/intel/workflows
 *  - Ingest pipeline history             /api/ingest/status (or /api/ingest — GET)
 *
 * Manual trigger strip lets the commander fire any cron on-demand.
 * Platform config panel shows auto_merge_enabled toggle and AEC status.
 */

import { useEffect, useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  GitBranch, Workflow, Radio, RefreshCw, Zap,
  Clock, AlertTriangle,
  ChevronDown, ChevronUp, ShieldCheck, Activity,
  BarChart3, Download, Globe, FileText, Terminal, FlaskConical,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────
// Actual shape from /api/governor GET
interface GovernorCycle {
  id:                    string
  conflict_day:          number
  trigger:               string
  layer_reached:         number     // 0-9 layers
  entities_extracted:    number
  claims_verified:       number
  mutations_proposed:    number
  mutations_applied:     number
  neural_health_before:  number
  neural_health_after:   number
  duration_ms:           number
  error:                 string | null
  created_at:            string
}

interface AECCycle {
  id:                  string
  cycle_number:        number
  enhancement_type:    string
  enhancement_proposed: string
  pr_url:              string | null
  deployment_status:   string
  auto_merged:         boolean
  duration_ms:         number
  created_at:          string
}

// Actual shape from /api/intel/workflows
interface WorkflowRun {
  id:            string
  workflow_type: string
  status:        string
  duration_ms:   number | null
  created_at:    string
  // task_count not returned by API — omit
}

// Actual shape from /api/ingest/status snapshots
interface IngestSnapshot {
  id:             string
  conflict_day:   number
  herald_summary: { total: number; critical: number; high: number } | null
  created_at:     string
}

// ─── Merged activity entry ────────────────────────────────────────────────────
type ActivityKind = 'governor' | 'aec' | 'workflow' | 'ingest'
interface ActivityEntry {
  id:         string
  kind:       ActivityKind
  ts:         string
  summary:    string
  status:     string
  detail:     string
  pr_url?:    string | null
  anomalies?: string[]
  duration_ms?: number
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const s = Math.floor(ms / 1_000)
  if (s < 60)  return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  return `${h}h ${m % 60}m ago`
}

function durationFmt(ms?: number): string {
  if (!ms) return '--'
  if (ms < 1_000) return `${ms}ms`
  return `${(ms / 1_000).toFixed(1)}s`
}

function statusColor(s: string): string {
  if (/success|complete|merged|verified/i.test(s)) return 'text-emerald-400'
  if (/warn|partial/i.test(s))                      return 'text-amber-400'
  if (/error|fail|anomaly/i.test(s))                return 'text-red-400'
  if (/running|active/i.test(s))                    return 'text-sky-400'
  return 'text-zinc-500'
}

const KIND_META: Record<ActivityKind, { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; color: string }> = {
  governor: { icon: ShieldCheck,  label: 'GOVERNOR',  color: 'text-purple-400' },
  aec:      { icon: GitBranch,    label: 'AEC',       color: 'text-sky-400'   },
  workflow: { icon: Workflow,     label: 'WORKFLOW',  color: 'text-amber-400' },
  ingest:   { icon: Download,     label: 'INGEST',    color: 'text-emerald-400' },
}

// ─── Manual trigger ops ───────────────────────────────────────────────────────
interface CronOp {
  label:    string
  endpoint: string
  method:   'GET' | 'POST'
  icon:     React.ComponentType<{ size?: number; className?: string }>
  desc:     string
}

const CRON_OPS: CronOp[] = [
  { label: 'Ingest',        endpoint: '/api/ingest',                method: 'POST', icon: Download,     desc: '5-min master pipeline' },
  { label: 'Analyze Batch', endpoint: '/api/analyze-batch',         method: 'POST', icon: FlaskConical, desc: 'AI batch analysis' },
  { label: 'Governor',      endpoint: '/api/governor',              method: 'POST', icon: ShieldCheck,  desc: '9-layer governance cycle' },
  { label: 'Auto Heal',     endpoint: '/api/platform/auto-heal',    method: 'POST', icon: Activity,     desc: 'Neural platform heal' },
  { label: 'Cross-Ref',     endpoint: '/api/intel/cross-ref',       method: 'POST', icon: ShieldCheck,  desc: 'NEXUS cross-reference' },
  { label: 'Forecast',      endpoint: '/api/intel/forecast',        method: 'POST', icon: BarChart3,    desc: '30-min scenario forecast' },
  { label: 'World Intel',   endpoint: '/api/intel/world',           method: 'POST', icon: Globe,        desc: '20-min world intel pull' },
  { label: 'Digest',        endpoint: '/api/intel/digest',          method: 'POST', icon: FileText,     desc: '30-min intel digest' },
  { label: 'Newsroom',      endpoint: '/api/newsroom/generate',     method: 'POST', icon: Terminal,     desc: 'Daily newsroom script' },
]

const POLL_MS = 30_000

// ─── Component ────────────────────────────────────────────────────────────────
export function CmdOpsCenter() {
  const [feed,       setFeed]       = useState<ActivityEntry[]>([])
  const [govStats,   setGovStats]   = useState<{ total: number; anomalies: number } | null>(null)
  const [aecStats,   setAecStats]   = useState<{ totalCycles: number; prCount: number; mergedCount: number } | null>(null)
  const [ingestStats,setIngestStats]= useState<{ lastRun: string | null; intelWritten: number; runCount: number } | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [lastFetch,  setLastFetch]  = useState<string | null>(null)
  const [countdown,  setCountdown]  = useState(POLL_MS / 1_000)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [triggering, setTriggering] = useState<string | null>(null)
  const [triggerLog, setTriggerLog] = useState<{ op: string; status: string; ts: string }[]>([])
  const [autoMerge,  setAutoMerge]  = useState<boolean | null>(null)

  const mergeActivity = useCallback((
    govCycles:  GovernorCycle[],
    aecCycles:  AECCycle[],
    wfRuns:     WorkflowRun[],
    snapshots:  IngestSnapshot[],
  ): ActivityEntry[] => {
    const entries: ActivityEntry[] = []

    govCycles.forEach(g => entries.push({
      id:         `gov-${g.id}`,
      kind:       'governor',
      ts:         g.created_at,
      summary:    `Governor cycle D${g.conflict_day} — ${g.layer_reached ?? 0}/9 layers`,
      status:     g.error ? 'error' : 'success',
      detail:     `Trigger: ${g.trigger} | NHA: ${g.neural_health_after?.toFixed(1) ?? '?'} | KG mutations: ${g.mutations_applied ?? 0} | Duration: ${durationFmt(g.duration_ms)}`,
      anomalies:  g.error ? [g.error] : [],
      duration_ms: g.duration_ms,
    }))

    aecCycles.forEach(a => entries.push({
      id:         `aec-${a.id}`,
      kind:       'aec',
      ts:         a.created_at,
      summary:    `AEC cycle #${a.cycle_number} — ${a.enhancement_type}`,
      status:     a.deployment_status,
      detail:     a.enhancement_proposed?.slice(0, 120) ?? 'no proposal',
      pr_url:     a.pr_url,
      duration_ms: a.duration_ms,
    }))

    wfRuns.forEach(w => entries.push({
      id:         `wf-${w.id}`,
      kind:       'workflow',
      ts:         w.created_at,
      summary:    `Workflow [${w.workflow_type}]`,
      status:     w.status,
      detail:     `Duration: ${durationFmt(w.duration_ms ?? undefined)}`,
      duration_ms: w.duration_ms ?? undefined,
    }))

    snapshots.forEach(s => entries.push({
      id:         `ing-${s.id}`,
      kind:       'ingest',
      ts:         s.created_at,
      summary:    `Ingest pipeline — D${s.conflict_day} — ${s.herald_summary?.total ?? 0} scored`,
      status:     (s.herald_summary?.total ?? 0) > 0 ? 'success' : 'empty',
      detail:     `HERALD critical: ${s.herald_summary?.critical ?? 0} | high: ${s.herald_summary?.high ?? 0}`,
      duration_ms: undefined,
    }))

    // Sort newest first
    return entries.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())
  }, [])

  const fetchAll = useCallback(async () => {
    try {
      const [govRes, aecRes, wfRes, ingRes] = await Promise.allSettled([
        fetch('/api/governor?limit=15',         { cache: 'no-store' }),
        fetch('/api/intel/autonomous?limit=15', { cache: 'no-store' }),
        fetch('/api/intel/workflows?limit=15',  { cache: 'no-store' }),
        fetch('/api/ingest/status',             { cache: 'no-store' }),
      ])

      const parse = async (r: PromiseSettledResult<Response>) =>
        r.status === 'fulfilled' && r.value.ok ? r.value.json().catch(() => ({})) : {}

      const [govData, aecData, wfData, ingData] = await Promise.all(
        [govRes, aecRes, wfRes, ingRes].map(parse)
      )

      const govCycles:  GovernorCycle[]    = govData.cycles  ?? []
      const aecCycles:  AECCycle[]         = aecData.cycles  ?? []
      const wfRuns:     WorkflowRun[]      = wfData.runs     ?? []
      const snapshots:  IngestSnapshot[]   = ingData.snapshots ?? []

      setFeed(mergeActivity(govCycles, aecCycles, wfRuns, snapshots))

      if (govCycles.length > 0) {
        const anomalies = govCycles.reduce((n, c) => n + (c.error ? 1 : 0), 0)
        setGovStats({ total: govCycles.length, anomalies })
      }
      if (aecData.stats) {
        setAecStats(aecData.stats)
      }
      if (ingData.lastRun !== undefined) {
        setIngestStats({
          lastRun:      ingData.lastRun,
          intelWritten: ingData.intelWritten ?? 0,
          runCount:     ingData.runCount ?? snapshots.length,
        })
      }

      // Pull auto_merge_enabled from platform_config via /api/platform/status
      try {
        const cfgRes = await fetch('/api/platform/status', { cache: 'no-store' })
        if (cfgRes.ok) {
          const cfgData = await cfgRes.json()
          const val = cfgData.config?.auto_merge_enabled
          setAutoMerge(val === true || val === 'true')
        }
      } catch { /* non-critical */ }

      setLastFetch(new Date().toISOString())
    } catch (e) {
      console.error('[CmdOpsCenter]', e)
    } finally {
      setLoading(false)
      setCountdown(POLL_MS / 1_000)
    }
  }, [mergeActivity])

  useSmartPoll(fetchAll, POLL_MS)
  useEffect(() => {
    const tickId = setInterval(() => setCountdown(c => Math.max(0, c - 1)), 1_000)
    return () => { clearInterval(tickId) }
  }, [fetchAll])

  // ─── Trigger handler ────────────────────────────────────────────────────────
  const handleTrigger = async (op: CronOp) => {
    setTriggering(op.label)
    try {
      const res = await fetch(op.endpoint, {
        method: op.method,
        headers: { 'Content-Type': 'application/json' },
      })
      const status = res.ok ? 'ok' : `HTTP ${res.status}`
      setTriggerLog(prev =>
        [{ op: op.label, status, ts: new Date().toISOString() }, ...prev].slice(0, 20)
      )
      if (res.ok) setTimeout(fetchAll, 3_000) // re-poll shortly after
    } catch (e) {
      setTriggerLog(prev =>
        [{ op: op.label, status: String(e), ts: new Date().toISOString() }, ...prev].slice(0, 20)
      )
    } finally {
      setTriggering(null)
    }
  }

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      {/* ── Stat bar ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {/* Governor */}
        <div className="tac-card p-3 space-y-1">
          <div className="flex items-center gap-1.5 text-[9px] text-purple-400 font-mono tracking-widest">
            <ShieldCheck size={9} /> GOVERNOR CYCLES
          </div>
          <div className="text-2xl font-bold font-mono text-zinc-100 tabular-nums">
            {loading ? '—' : (govStats?.total ?? 0)}
          </div>
          {govStats && govStats.anomalies > 0 && (
            <div className="text-[9px] text-amber-400 flex items-center gap-1">
              <AlertTriangle size={8} /> {govStats.anomalies} anomal{govStats.anomalies > 1 ? 'ies' : 'y'}
            </div>
          )}
        </div>

        {/* AEC */}
        <div className="tac-card p-3 space-y-1">
          <div className="flex items-center gap-1.5 text-[9px] text-sky-400 font-mono tracking-widest">
            <GitBranch size={9} /> AEC CYCLES
          </div>
          <div className="text-2xl font-bold font-mono text-zinc-100 tabular-nums">
            {loading ? '—' : (aecStats?.totalCycles ?? 0)}
          </div>
          {aecStats && (
            <div className="text-[9px] text-zinc-500">
              {aecStats.prCount} PRs · {aecStats.mergedCount} merged
            </div>
          )}
        </div>

        {/* Ingest */}
        <div className="tac-card p-3 space-y-1">
          <div className="flex items-center gap-1.5 text-[9px] text-emerald-400 font-mono tracking-widest">
            <Download size={9} /> INGEST RUNS
          </div>
          <div className="text-2xl font-bold font-mono text-zinc-100 tabular-nums">
            {loading ? '—' : (ingestStats?.runCount ?? 0)}
          </div>
          {ingestStats?.lastRun && (
            <div className="text-[9px] text-zinc-500">{timeAgo(ingestStats.lastRun)}</div>
          )}
        </div>

        {/* Auto-merge */}
        <div className="tac-card p-3 space-y-1">
          <div className="flex items-center gap-1.5 text-[9px] text-zinc-400 font-mono tracking-widest">
            <Zap size={9} /> AUTO MERGE
          </div>
          <div className={`text-lg font-bold font-mono tabular-nums ${autoMerge ? 'text-emerald-400' : 'text-red-400'}`}>
            {autoMerge === null ? '—' : autoMerge ? 'ENABLED' : 'DISABLED'}
          </div>
          <div className="text-[9px] text-zinc-600">
            {autoMerge ? 'AEC may deploy autonomously' : 'Commander approval required'}
          </div>
        </div>
      </div>

      {/* ── Manual Operations Strip ── */}
      <div className="tac-card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Terminal size={10} className="text-amber-400" />
          <span className="text-[10px] font-mono tracking-widest text-amber-400 uppercase">Manual Op Triggers</span>
          <span className="text-[9px] text-zinc-600 ml-1">— commander override</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {CRON_OPS.map(op => (
            <button
              key={op.label}
              onClick={() => handleTrigger(op)}
              disabled={triggering === op.label}
              title={op.desc}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-[9px] font-mono rounded border
                border-zinc-700/40 bg-zinc-900/40 text-zinc-400
                hover:bg-zinc-800/60 hover:text-zinc-200 hover:border-zinc-600/60
                disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {triggering === op.label
                ? <RefreshCw size={8} className="animate-spin" />
                : <op.icon size={8} />
              }
              {op.label}
            </button>
          ))}
        </div>

        {/* Trigger log */}
        {triggerLog.length > 0 && (
          <div className="space-y-1 border-t border-zinc-800/40 pt-2 max-h-28 overflow-y-auto">
            {triggerLog.map((t, i) => (
              <div key={i} className="flex items-center gap-2 text-[8px] font-mono">
                <Clock size={7} className="text-zinc-600" />
                <span className="text-zinc-500">{timeAgo(t.ts)}</span>
                <span className="text-zinc-300">▶ {t.op}</span>
                <span className={t.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}>
                  {t.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Unified Activity Log ── */}
      <div className="tac-card p-4 space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Radio size={9} className="text-sky-400 animate-pulse" />
          <span className="text-[10px] font-mono tracking-widest text-sky-400 uppercase">Autonomous Activity Log</span>
          <span className="text-[9px] text-zinc-600 ml-1">— governor · aec · workflows · ingest</span>
          <div className="ml-auto flex items-center gap-3 text-[8px] font-mono text-zinc-600">
            <span>refresh in {countdown}s</span>
            {lastFetch && <span>{timeAgo(lastFetch)}</span>}
            <button
              onClick={fetchAll}
              className="hover:text-zinc-400 transition-colors"
              title="Refresh now"
            >
              <RefreshCw size={9} />
            </button>
          </div>
        </div>

        {/* Kind legend */}
        <div className="flex items-center gap-4 text-[8px] text-zinc-600">
          {(Object.entries(KIND_META) as [ActivityKind, typeof KIND_META[ActivityKind]][]).map(([k, m]) => (
            <span key={k} className={`flex items-center gap-1 ${m.color}`}>
              <m.icon size={8} /> {m.label}
            </span>
          ))}
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-[10px] text-zinc-500 py-4">
            <RefreshCw size={10} className="animate-spin" /> Loading autonomous ops log…
          </div>
        )}

        {!loading && feed.length === 0 && (
          <div className="text-[10px] text-zinc-600 text-center py-4">
            No activity yet — crons run every 5–30 min.
          </div>
        )}

        <div className="space-y-1 max-h-[480px] overflow-y-auto pr-1 scrollbar-thin">
          {feed.map(entry => {
            const meta      = KIND_META[entry.kind]
            const expanded  = expandedId === entry.id
            const hasAnoms  = (entry.anomalies?.length ?? 0) > 0

            return (
              <div
                key={entry.id}
                className={`border rounded-sm p-2 transition-all ${
                  hasAnoms
                    ? 'border-amber-800/40 bg-amber-950/10'
                    : 'border-zinc-800/30 bg-zinc-950/20'
                }`}
              >
                <div
                  className="flex items-center gap-2 cursor-pointer"
                  onClick={() => setExpandedId(expanded ? null : entry.id)}
                >
                  <meta.icon size={9} className={meta.color} />
                  <span className={`text-[8px] font-bold font-mono w-16 shrink-0 ${meta.color}`}>
                    {meta.label}
                  </span>
                  <span className="text-[9px] text-zinc-300 flex-1 truncate">{entry.summary}</span>
                  <span className={`text-[8px] font-mono shrink-0 ${statusColor(entry.status)}`}>
                    {entry.status}
                  </span>
                  {entry.duration_ms !== undefined && (
                    <span className="text-[8px] text-zinc-600 font-mono shrink-0">
                      {durationFmt(entry.duration_ms)}
                    </span>
                  )}
                  <span className="text-[8px] text-zinc-600 shrink-0">{timeAgo(entry.ts)}</span>
                  {expanded ? <ChevronUp size={8} className="text-zinc-600 shrink-0" /> : <ChevronDown size={8} className="text-zinc-600 shrink-0" />}
                </div>

                {expanded && (
                  <div className="mt-2 ml-5 space-y-1 border-t border-zinc-800/30 pt-2">
                    <p className="text-[8px] text-zinc-500">{entry.detail}</p>
                    {entry.pr_url && (
                      <a
                        href={entry.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[8px] text-sky-400 hover:underline flex items-center gap-1"
                      >
                        <GitBranch size={8} /> View PR / Enhancement
                      </a>
                    )}
                    {hasAnoms && (
                      <div className="space-y-0.5">
                        {entry.anomalies!.map((a, i) => (
                          <div key={i} className="text-[8px] text-amber-400 flex items-center gap-1">
                            <AlertTriangle size={7} /> {a}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="text-[7px] text-zinc-700 font-mono">
                      {new Date(entry.ts).toISOString()}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
