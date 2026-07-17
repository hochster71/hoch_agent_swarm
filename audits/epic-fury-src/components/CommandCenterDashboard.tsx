'use client'

/**
 * CommandCenterDashboard.tsx
 *
 * Full-platform operator remote — polls ALL autonomous subsystems every 30s.
 * Displays every engine layer in a live grid with quick-action controls.
 *
 * Data sources:
 *   GET /api/governor?limit=5           — governor cycles + KG/visual/revenue stats
 *   GET /api/platform/status            — 7-system health matrix + circuit breakers
 *   GET /api/intel/autonomous?limit=6   — AEC enhancement cycles
 *   GET /api/intel/stats                — intel DB aggregate
 *   GET /api/intel/debate?limit=5       — neural truth debate stats
 *   GET /api/intel/workflows?limit=5    — workflow engine metrics
 *   GET /api/intel/foresight?mode=gea   — GEA memory stats
 *   GET /api/oracle                     — ORACLE-9 threat matrix
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Brain, Bot, DollarSign, GitBranch,
  Telescope, Database, Activity, RefreshCw,
  CheckCircle2, XCircle, Target,
  Clock, Film, Globe2,
  Wifi,
} from 'lucide-react'

// ─── Conflict Day ──────────────────────────────────────────────────────────
const CONFLICT_START_UTC = Date.UTC(2026, 2, 1)
function conflictDay() {
  return Math.max(1, Math.floor((Date.now() - CONFLICT_START_UTC) / 86_400_000) + 1)
}

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return 'Never'
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60_000)  return `${Math.round(ms / 1000)}s ago`
  if (ms < 3600_000) return `${Math.round(ms / 60_000)}m ago`
  if (ms < 86_400_000) return `${Math.round(ms / 3600_000)}h ago`
  return `${Math.round(ms / 86_400_000)}d ago`
}

function fmt(n: number | undefined | null, fallback = '—') {
  if (n == null) return fallback
  return n.toLocaleString()
}

// ─── Types from API responses ──────────────────────────────────────────────

interface GovernorCycle {
  id: string
  conflict_day: number
  trigger: string
  layer_reached: number
  entities_extracted: number
  claims_verified: number
  mutations_applied: number
  duration_ms: number
  error: string | null
  created_at: string
}
interface GovernorSummary {
  cyclesReturned: number
  avgLayersCompleted: number
  totalEntitiesExtracted: number
  totalClaimsVerified: number
  totalMutationsApplied: number
  avgDurationMs: number
}
interface KGStats { totalEntities: number; totalRelations: number; pendingMutations: number; appliedMutations: number }
interface VisualStats { totalAssets: number; generatedToday: number; pendingGeneration: number; videoCount: number }
interface RevenueStats { activeStreams: number; proposedStreams: number; totalRevenueLedger: number; monthlyRevenue: number; projectedAnnualUsd: number }
interface GovernorAPIResponse { cycles: GovernorCycle[]; kgStats: KGStats; visualStats: VisualStats; revenueStats: RevenueStats; summary: GovernorSummary }

interface SystemStatus { name: string; status: string; lastSeen: string | null; detail: string; metric: string }
interface PlatformAPIResponse { ok: boolean; systems: SystemStatus[]; health: string; aiAvailable: boolean }

interface AECCycle { cycle_number: number; enhancement_type: string; enhancement_proposed: string; pr_url: string | null; deployment_status: string; auto_merged: boolean; duration_ms: number; created_at: string }
interface AECStats { totalCycles: number; lastCycleAt: string | null; byType: Record<string, number>; mergedCount: number; pendingPRs: number }
interface AECAPIResponse { stats: AECStats; cycles: AECCycle[] }

interface IntelStats { total: number; verified: number; heraldAuthored: number; last24h: number; lastAdded: string | null }

interface DebateStats { totalSessions: number; verifiedCount: number; contradictedCount: number; unverifiableCount: number; avgConsensusScore: number; lastSessionAt: string | null }
interface DebateAPIResponse { ok: boolean; stats: DebateStats }

interface WorkflowMetrics { total: number; running: number; completed: number; failed: number; avgDurationMs: number }
interface WorkflowRun { id: string; workflow_type: string; status: string; started_at: string; completed_at: string | null; duration_ms: number | null }
interface WorkflowAPIResponse { metrics: WorkflowMetrics; runs: WorkflowRun[] }

interface GEAStats { totalExperiences: number; successRate: number; topInnovations: string[]; recentFailures: string[] }
interface GEAAPIResponse { stats: GEAStats }

interface OracleThreat { label: string; domain: string; probability: number; severity: string; trend: string; topSignal: string; windowHours: number }
interface OracleAPIResponse { threats: OracleThreat[]; conflictDay: number; generatedAt: string; aiAvailable: boolean }

// ─── Cron Schedule ────────────────────────────────────────────────────────
const CRON_SCHEDULE = [
  { name: 'INGEST',          schedule: '*/10 min',  path: '/api/ingest',   layer: 'L1' },
  { name: 'HERALD',          schedule: '*/15 min',  path: '/api/herald',   layer: 'L1' },
  { name: 'ANALYZE-BATCH',   schedule: '*/20 min',  path: '/api/analyze-batch', layer: 'L2' },
  { name: 'GOVERNOR',        schedule: '*/25 min',  path: '/api/governor/heartbeat', layer: 'L1–10' },
  { name: 'ORACLE',          schedule: '*/30 min',  path: '/api/oracle',   layer: 'L3' },
  { name: 'COMPASS',         schedule: '*/30 min',  path: '/api/compass',  layer: 'L3' },
  { name: 'NEXUS',           schedule: '*/45 min',  path: '/api/intel/synthesis', layer: 'L10' },
  { name: 'PLATFORM HEALTH', schedule: '*/15 min',  path: '/api/platform/status', layer: 'L5' },
  { name: 'HEAL',            schedule: '*/30 min',  path: '/api/platform/heal',   layer: 'L5' },
  { name: 'DEBATE',          schedule: '*/60 min',  path: '/api/intel/debate',    layer: 'L2' },
  { name: 'FORESIGHT',       schedule: '*/60 min',  path: '/api/intel/foresight', layer: 'L9' },
  { name: 'REVENUE',         schedule: '*/120 min', path: '/api/revenue',         layer: 'L8' },
  { name: 'WORKFLOWS',       schedule: '*/60 min',  path: '/api/intel/workflows', layer: 'L7' },
  { name: 'NEWS',            schedule: '*/20 min',  path: '/api/news',            layer: 'L1' },
]

// ─── Severity / Status helpers ────────────────────────────────────────────
const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'text-red-400 border-red-700/40 bg-red-950/20',
  HIGH:     'text-orange-400 border-orange-700/40 bg-orange-950/20',
  MODERATE: 'text-amber-400 border-amber-700/40 bg-amber-950/20',
  LOW:      'text-emerald-400 border-emerald-700/40 bg-emerald-950/20',
  MINIMAL:  'text-zinc-400 border-zinc-700/40 bg-zinc-900/20',
}
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const STATUS_COLOR: Record<string, string> = {
  ONLINE:   'text-emerald-400',
  DEGRADED: 'text-amber-400',
  OFFLINE:  'text-red-400',
  UNKNOWN:  'text-zinc-500',
}
const STATUS_DOT: Record<string, string> = {
  ONLINE:   'bg-emerald-400',
  DEGRADED: 'bg-amber-400',
  OFFLINE:  'bg-red-400',
  UNKNOWN:  'bg-zinc-500',
}
const HEALTH_BANNER: Record<string, string> = {
  'ALL GREEN': 'border-emerald-700/50 bg-emerald-950/20 text-emerald-300',
  'DEGRADED':  'border-amber-700/50 bg-amber-950/20 text-amber-300',
  'PARTIAL':   'border-red-700/50 bg-red-950/20 text-red-300',
}

// ─── Sub-components ───────────────────────────────────────────────────────

function Panel({ title, icon: Icon, borderColor = 'border-zinc-800', children, badge }: {
  title: string
  icon: React.ElementType
  borderColor?: string
  children: React.ReactNode
  badge?: React.ReactNode
}) {
  return (
    <div className={`rounded-lg border ${borderColor} bg-zinc-900/60 p-4 flex flex-col gap-3`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-3.5 h-3.5 text-zinc-400" />
          <span className="text-[9px] tracking-[0.2em] uppercase text-zinc-400 font-bold">{title}</span>
        </div>
        {badge}
      </div>
      {children}
    </div>
  )
}

function Stat({ label, value, accent = 'text-zinc-100' }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[8px] text-zinc-600 tracking-widest uppercase">{label}</span>
      <span className={`text-sm font-bold font-mono ${accent}`}>{value}</span>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const level = (status ?? 'UNKNOWN').toUpperCase()
  return (
    <span className={`text-[8px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded border ${
      level === 'ONLINE' || level === 'COMPLETED' || level === 'MERGED'
        ? 'border-emerald-700/40 bg-emerald-950/20 text-emerald-400'
        : level === 'DEGRADED' || level === 'RUNNING' || level === 'PENDING'
        ? 'border-amber-700/40 bg-amber-950/20 text-amber-400'
        : level === 'OFFLINE' || level === 'FAILED'
        ? 'border-red-700/40 bg-red-950/20 text-red-400'
        : 'border-zinc-700/40 bg-zinc-900/20 text-zinc-400'
    }`}>{level}</span>
  )
}

function LayerBar({ reached, total = 10 }: { reached: number; total?: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: total }, (_, i) => i + 1).map(n => (
        <div
          key={n}
          className={`h-1.5 flex-1 rounded-sm ${n <= reached ? 'bg-emerald-500' : 'bg-zinc-800'}`}
          title={`Layer ${n}`}
        />
      ))}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────

export default function CommandCenterDashboard() {
  const [gov,       setGov]       = useState<GovernorAPIResponse | null>(null)
  const [platform,  setPlatform]  = useState<PlatformAPIResponse | null>(null)
  const [aec,       setAec]       = useState<AECAPIResponse | null>(null)
  const [intel,     setIntel]     = useState<IntelStats | null>(null)
  const [debate,    setDebate]    = useState<DebateAPIResponse | null>(null)
  const [workflows, setWorkflows] = useState<WorkflowAPIResponse | null>(null)
  const [gea,       setGea]       = useState<GEAAPIResponse | null>(null)
  const [oracle,    setOracle]    = useState<OracleAPIResponse | null>(null)

  const [loading,   setLoading]   = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [actionStatus, setActionStatus] = useState<Record<string, string>>({})

  const fetchAll = useCallback(async () => {
    try {
      const [govR, platR, aecR, intelR, debateR, wfR, geaR, oracleR] = await Promise.allSettled([
        fetch('/api/governor?limit=5',              { cache: 'no-store' }),
        fetch('/api/platform/status',               { cache: 'no-store' }),
        fetch('/api/intel/autonomous?limit=6',      { cache: 'no-store' }),
        fetch('/api/intel/stats',                   { cache: 'no-store' }),
        fetch('/api/intel/debate?limit=5',          { cache: 'no-store' }),
        fetch('/api/intel/workflows?limit=5',       { cache: 'no-store' }),
        fetch('/api/intel/foresight?mode=gea',      { cache: 'no-store' }),
        fetch('/api/oracle',                        { cache: 'no-store' }),
      ])

      try { if (govR.status === 'fulfilled' && govR.value.ok)       setGov(await govR.value.json())       } catch { /* skip on parse error */ }
      try { if (platR.status === 'fulfilled' && platR.value.ok)     setPlatform(await platR.value.json()) } catch { /* skip on parse error */ }
      try { if (aecR.status === 'fulfilled' && aecR.value.ok)       setAec(await aecR.value.json())       } catch { /* skip on parse error */ }
      try { if (intelR.status === 'fulfilled' && intelR.value.ok)   setIntel(await intelR.value.json())   } catch { /* skip on parse error */ }
      try { if (debateR.status === 'fulfilled' && debateR.value.ok) setDebate(await debateR.value.json()) } catch { /* skip on parse error */ }
      try { if (wfR.status === 'fulfilled' && wfR.value.ok)         setWorkflows(await wfR.value.json())  } catch { /* skip on parse error */ }
      try { if (geaR.status === 'fulfilled' && geaR.value.ok)       setGea(await geaR.value.json())       } catch { /* skip on parse error */ }
      try { if (oracleR.status === 'fulfilled' && oracleR.value.ok) setOracle(await oracleR.value.json()) } catch { /* skip on parse error */ }
    } finally {
      setLoading(false)
      setLastRefresh(new Date())
    }
  }, [])

  useSmartPoll(fetchAll, 30_000)

  // ─── Action triggers ─────────────────────────────────────────────────
  const trigger = useCallback(async (label: string, url: string, method = 'POST', body?: object) => {
    setActionStatus(s => ({ ...s, [label]: 'FIRING…' }))
    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
        cache: 'no-store',
      })
      const ok = res.ok
      setActionStatus(s => ({ ...s, [label]: ok ? 'OK ✓' : `ERR ${res.status}` }))
      if (ok) setTimeout(() => { fetchAll(); setActionStatus(s => ({ ...s, [label]: '' })) }, 2000)
    } catch (_e) {
      setActionStatus(s => ({ ...s, [label]: 'FAILED' }))
    }
  }, [fetchAll])

  // ─── Derived ─────────────────────────────────────────────────────────
  const healthText = platform?.health ?? '…'
  const healthClass = HEALTH_BANNER[healthText] ?? 'border-zinc-700/40 bg-zinc-900/20 text-zinc-400'
  const lastGov = gov?.cycles?.[0]
  const day = conflictDay()

  const onlineSystems  = platform?.systems?.filter(s => s.status === 'ONLINE').length ?? 0
  const totalSystems   = platform?.systems?.length ?? 0
  const offlineSystems = platform?.systems?.filter(s => s.status === 'OFFLINE').length ?? 0

  const ACTIONS: Array<{ label: string; url: string; method: 'POST' | 'GET'; body?: object }> = [
    { label: 'GOVERNOR',   url: '/api/governor/trigger',   method: 'POST' as const },
    { label: 'HEAL',       url: '/api/platform/auto-heal', method: 'GET'  as const },
    { label: 'INGEST',     url: '/api/ingest/trigger',     method: 'POST' as const },
    { label: 'ORACLE',     url: '/api/oracle',             method: 'GET'  as const },
    { label: 'HERALD',     url: '/api/herald',             method: 'GET'  as const },
  ]

  return (
    <div className="space-y-5">

      {/* ── MASTER STATUS BAR ─────────────────────────────────────────── */}
      <div className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-2.5 ${healthClass}`}>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className={`inline-block w-2 h-2 rounded-full animate-pulse ${offlineSystems > 0 ? 'bg-red-500' : onlineSystems < totalSystems ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            <span className="text-[10px] font-bold tracking-widest uppercase">Platform: {healthText}</span>
          </div>
          <span className="text-[9px] text-zinc-500">|</span>
          <span className="text-[9px] tracking-widest text-zinc-400 uppercase">Day {day}</span>
          <span className="text-[9px] text-zinc-500">|</span>
          <span className="text-[9px] tracking-widest text-zinc-400 uppercase">
            Systems {onlineSystems}/{totalSystems} Online
          </span>
          {lastGov && (
            <>
              <span className="text-[9px] text-zinc-500">|</span>
              <span className="text-[9px] tracking-widest text-zinc-400 uppercase">
                Last Gov {timeAgo(lastGov.created_at)} · L{lastGov.layer_reached}/10
              </span>
            </>
          )}
          <span className="text-[9px] text-zinc-500">|</span>
          <span className="text-[9px] tracking-widest text-zinc-500 uppercase">
            AI: {platform?.aiAvailable ? <span className="text-emerald-400">ONLINE</span> : <span className="text-red-400">OFFLINE</span>}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={fetchAll}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-zinc-700 bg-zinc-800 text-zinc-300 text-[9px] tracking-widest uppercase hover:bg-zinc-700 transition-colors"
          >
            <RefreshCw className={`w-2.5 h-2.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {lastRefresh && <span className="text-[8px] text-zinc-600">{lastRefresh.toLocaleTimeString()}</span>}
        </div>
      </div>

      {/* ── QUICK ACTIONS ─────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-[8px] tracking-widest text-zinc-600 uppercase mr-1">Quick Actions:</span>
        {ACTIONS.map(({ label, url, method, body }) => {
          const status = actionStatus[label]
          return (
            <button
              key={label}
              onClick={() => trigger(label, url, method ?? 'POST', body)}
              disabled={status === 'FIRING…'}
              className={`px-3 py-1.5 rounded border text-[9px] tracking-widest font-bold uppercase transition-all
                ${status === 'OK ✓'     ? 'border-emerald-600 bg-emerald-950/30 text-emerald-400' :
                  status === 'FIRING…' ? 'border-amber-600 bg-amber-950/30 text-amber-400 animate-pulse' :
                  status?.startsWith('ERR') || status === 'FAILED' ? 'border-red-700 bg-red-950/20 text-red-400' :
                  'border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-emerald-700 hover:text-emerald-300'}
              `}
            >
              {status || `▶ ${label}`}
            </button>
          )
        })}
      </div>

      {/* ── GRID ROW 1: CORE AUTONOMOUS ───────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* GOVERNOR ENGINE */}
        <Panel title="Governor Engine — 10 Layers" icon={Brain} borderColor="border-emerald-900/50">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Total Cycles"    value={fmt(gov?.summary?.cyclesReturned)} />
            <Stat label="Avg Layers"      value={gov?.summary?.avgLayersCompleted != null ? gov.summary.avgLayersCompleted.toFixed(1) : '—'} />
            <Stat label="Entities Ext."   value={fmt(gov?.summary?.totalEntitiesExtracted)} accent="text-emerald-300" />
            <Stat label="Claims Verified" value={fmt(gov?.summary?.totalClaimsVerified)}    accent="text-emerald-300" />
            <Stat label="Mutations"       value={fmt(gov?.summary?.totalMutationsApplied)} />
            <Stat label="Avg Duration"    value={gov?.summary?.avgDurationMs != null ? `${(gov.summary.avgDurationMs / 1000).toFixed(0)}s` : '—'} />
          </div>
          {/* Recent cycles */}
          <div className="space-y-1.5">
            <span className="text-[8px] tracking-widest text-zinc-600 uppercase">Recent Cycles</span>
            {gov?.cycles?.slice(0, 3).map(c => (
              <div key={c.id} className="rounded border border-zinc-800/60 bg-zinc-900/40 px-2 py-1.5 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[8px] text-zinc-400 font-mono">{timeAgo(c.created_at)}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[8px] text-zinc-500">{c.trigger}</span>
                    {c.error
                      ? <XCircle className="w-2.5 h-2.5 text-red-400" />
                      : <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                    }
                  </div>
                </div>
                <LayerBar reached={c.layer_reached} />
                <div className="flex gap-2 text-[8px] text-zinc-500">
                  <span>L{c.layer_reached}/10</span>
                  <span>·</span>
                  <span>{c.entities_extracted} ent</span>
                  <span>·</span>
                  <span>{c.claims_verified} claims</span>
                  <span>·</span>
                  <span>{(c.duration_ms / 1000).toFixed(0)}s</span>
                </div>
              </div>
            )) ?? <span className="text-[9px] text-zinc-600">No cycles yet</span>}
          </div>
        </Panel>

        {/* PLATFORM HEALTH */}
        <Panel title="Platform Health — 7 Systems" icon={Activity} borderColor="border-zinc-800">
          <div className="space-y-1.5">
            {platform?.systems?.map(s => {
              const level = (s.status ?? 'UNKNOWN').toUpperCase() as keyof typeof STATUS_COLOR
              return (
                <div key={s.name} className="flex items-center justify-between rounded border border-zinc-800/50 bg-zinc-900/30 px-2 py-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${STATUS_DOT[level] ?? 'bg-zinc-500'}`} />
                    <span className="text-[9px] text-zinc-300 font-mono truncate">{s.name}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[8px] text-zinc-600 truncate max-w-[80px]">{s.metric}</span>
                    <StatusBadge status={s.status} />
                  </div>
                </div>
              )
            }) ?? <span className="text-[9px] text-zinc-600">Loading…</span>}
          </div>
          {platform && (
            <div className="flex items-center gap-2 pt-1 border-t border-zinc-800/40">
              <Wifi className={`w-3 h-3 ${platform.aiAvailable ? 'text-emerald-400' : 'text-zinc-600'}`} />
              <span className="text-[9px] text-zinc-500">
                AI Pipeline: {platform.aiAvailable ? 'Available' : 'Unavailable'}
              </span>
            </div>
          )}
        </Panel>

        {/* AEC — AUTONOMOUS ENHANCEMENT */}
        <Panel title="AEC — Autonomous Enhancement" icon={Bot} borderColor="border-violet-900/40">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Total Cycles" value={fmt(aec?.stats?.totalCycles)} accent="text-violet-300" />
            <Stat label="Merged PRs"   value={fmt(aec?.stats?.mergedCount)}  accent="text-emerald-300" />
            <Stat label="Pending PRs"  value={fmt(aec?.stats?.pendingPRs)}   accent={aec?.stats?.pendingPRs ? 'text-amber-300' : 'text-zinc-400'} />
            <Stat label="Last Cycle"   value={timeAgo(aec?.stats?.lastCycleAt)} />
          </div>
          {/* Type breakdown */}
          {aec?.stats?.byType && Object.keys(aec.stats.byType).length > 0 && (
            <div className="space-y-1">
              <span className="text-[8px] tracking-widest text-zinc-600 uppercase">By Type</span>
              <div className="flex flex-wrap gap-1">
                {Object.entries(aec.stats.byType).map(([type, count]) => (
                  <span key={type} className="text-[8px] px-1.5 py-0.5 rounded border border-violet-800/30 bg-violet-950/20 text-violet-300 font-mono">
                    {type}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
          {/* Recent cycles */}
          <div className="space-y-1">
            <span className="text-[8px] tracking-widest text-zinc-600 uppercase">Recent</span>
            {aec?.cycles?.slice(0, 3).map((c, i) => (
              <div key={i} className="rounded border border-zinc-800/50 bg-zinc-900/30 px-2 py-1 flex items-center justify-between gap-2">
                <span className="text-[8px] text-zinc-400 truncate flex-1">{c.enhancement_type}</span>
                <StatusBadge status={c.deployment_status} />
                <span className="text-[8px] text-zinc-600 flex-shrink-0">{timeAgo(c.created_at)}</span>
              </div>
            )) ?? <span className="text-[9px] text-zinc-600">No cycles yet</span>}
          </div>
        </Panel>
      </div>

      {/* ── GRID ROW 2: INTELLIGENCE PIPELINE ────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* INTEL DB STATS */}
        <Panel title="Intel Stream — DB Stats" icon={Database} borderColor="border-zinc-800">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Total Intel"     value={fmt(intel?.total)}          accent="text-zinc-100" />
            <Stat label="Verified"        value={fmt(intel?.verified)}        accent="text-emerald-300" />
            <Stat label="HERALD Authored" value={fmt(intel?.heraldAuthored)} accent="text-blue-300" />
            <Stat label="Last 24h"        value={fmt(intel?.last24h)}         accent="text-amber-300" />
          </div>
          {intel?.lastAdded && (
            <div className="text-[9px] text-zinc-500 pt-1 border-t border-zinc-800/40">
              Last item: {timeAgo(intel.lastAdded)}
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-2 border-t border-zinc-800/40">
            <Stat label="KG Entities"    value={fmt(gov?.kgStats?.totalEntities)}   accent="text-cyan-300" />
            <Stat label="KG Relations"   value={fmt(gov?.kgStats?.totalRelations)}  accent="text-cyan-300" />
            <Stat label="Pending Muts."  value={fmt(gov?.kgStats?.pendingMutations)} accent={gov?.kgStats?.pendingMutations ? 'text-amber-300' : 'text-zinc-400'} />
            <Stat label="Applied Muts."  value={fmt(gov?.kgStats?.appliedMutations)} />
          </div>
        </Panel>

        {/* NEURAL TRUTH — DEBATE ENGINE */}
        <Panel title="Neural Truth — Debate Engine" icon={Brain} borderColor="border-purple-900/40">
          {debate?.stats ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                <Stat label="Sessions"    value={fmt(debate.stats.totalSessions)} accent="text-purple-300" />
                <Stat label="Verified"    value={fmt(debate.stats.verifiedCount)} accent="text-emerald-300" />
                <Stat label="Contradicted" value={fmt(debate.stats.contradictedCount)} accent="text-red-400" />
                <Stat label="Unverifiable" value={fmt(debate.stats.unverifiableCount)} />
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[8px] text-zinc-600 uppercase tracking-widest">Consensus Score</span>
                  <span className="text-[10px] font-bold text-purple-300 font-mono">
                    {debate.stats.avgConsensusScore?.toFixed(1) ?? '—'}/10
                  </span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-1.5">
                  <div
                    className="bg-purple-500 h-1.5 rounded-full"
                    style={{ width: `${((debate.stats.avgConsensusScore ?? 0) / 10) * 100}%` }}
                  />
                </div>
              </div>
              <div className="text-[9px] text-zinc-500">Last: {timeAgo(debate.stats.lastSessionAt)}</div>
            </div>
          ) : (
            <span className="text-[9px] text-zinc-600">Loading debate stats…</span>
          )}
        </Panel>

        {/* VISUAL ENGINE */}
        <Panel title="Visual Engine — L4 Generation" icon={Film} borderColor="border-zinc-800">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Total Assets"    value={fmt(gov?.visualStats?.totalAssets)}       accent="text-zinc-100" />
            <Stat label="Generated Today" value={fmt(gov?.visualStats?.generatedToday)}    accent="text-emerald-300" />
            <Stat label="Pending Gen."    value={fmt(gov?.visualStats?.pendingGeneration)} accent={gov?.visualStats?.pendingGeneration ? 'text-amber-300' : 'text-zinc-400'} />
            <Stat label="Video Assets"    value={fmt(gov?.visualStats?.videoCount)}        accent="text-blue-300" />
          </div>
        </Panel>
      </div>

      {/* ── GRID ROW 3: ENGINES ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* REVENUE ENGINE */}
        <Panel title="Revenue Engine — Layer 8" icon={DollarSign} borderColor="border-emerald-900/40">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <Stat label="Active Streams"   value={fmt(gov?.revenueStats?.activeStreams)}   accent="text-emerald-300" />
            <Stat label="Proposed"         value={fmt(gov?.revenueStats?.proposedStreams)} accent="text-amber-300" />
            <Stat label="Revenue Ledger"   value={gov?.revenueStats?.totalRevenueLedger != null ? `$${gov.revenueStats.totalRevenueLedger.toFixed(2)}` : '—'} accent="text-emerald-300" />
            <Stat label="Monthly"          value={gov?.revenueStats?.monthlyRevenue != null ? `$${gov.revenueStats.monthlyRevenue.toFixed(2)}` : '—'} />
          </div>
          {gov?.revenueStats?.projectedAnnualUsd != null && (
            <div className="rounded border border-emerald-800/30 bg-emerald-950/10 px-2 py-1.5">
              <span className="text-[8px] text-zinc-500 uppercase tracking-widest">Projected Annual</span>
              <div className="text-sm font-bold text-emerald-300 font-mono">
                ${gov.revenueStats.projectedAnnualUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
          )}
        </Panel>

        {/* WORKFLOW ENGINE */}
        <Panel title="Workflow Engine — Temporal" icon={GitBranch} borderColor="border-cyan-900/40">
          {workflows?.metrics ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                <Stat label="Total Runs"  value={fmt(workflows.metrics.total)}     accent="text-zinc-100" />
                <Stat label="Running"     value={fmt(workflows.metrics.running)}   accent="text-cyan-300" />
                <Stat label="Completed"   value={fmt(workflows.metrics.completed)} accent="text-emerald-300" />
                <Stat label="Failed"      value={fmt(workflows.metrics.failed)}    accent={workflows.metrics.failed ? 'text-red-400' : 'text-zinc-400'} />
              </div>
              {workflows.metrics.avgDurationMs > 0 && (
                <div className="text-[9px] text-zinc-500">
                  Avg duration: {(workflows.metrics.avgDurationMs / 1000).toFixed(0)}s
                </div>
              )}
              <div className="space-y-1">
                <span className="text-[8px] tracking-widest text-zinc-600 uppercase">Recent Runs</span>
                {workflows.runs?.slice(0, 3).map(r => (
                  <div key={r.id} className="flex items-center justify-between rounded border border-zinc-800/50 bg-zinc-900/30 px-2 py-1">
                    <span className="text-[8px] text-zinc-400 font-mono truncate flex-1">{r.workflow_type}</span>
                    <StatusBadge status={r.status} />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <span className="text-[9px] text-zinc-600">Loading workflow data…</span>
          )}
        </Panel>

        {/* FORESIGHT + GEA */}
        <Panel title="Foresight — GEA Memory Layer 9" icon={Telescope} borderColor="border-indigo-900/40">
          {gea?.stats ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                <Stat label="Experiences"  value={fmt(gea.stats.totalExperiences)} accent="text-indigo-300" />
                <Stat label="Success Rate" value={gea.stats.successRate != null ? `${(gea.stats.successRate * 100).toFixed(0)}%` : '—'} accent="text-emerald-300" />
              </div>
              {gea.stats.topInnovations?.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[8px] tracking-widest text-zinc-600 uppercase">Top Innovations</span>
                  {gea.stats.topInnovations.slice(0, 2).map((inn, i) => (
                    <div key={i} className="text-[8px] text-indigo-300 font-mono bg-indigo-950/20 border border-indigo-900/30 rounded px-2 py-1 truncate">
                      {inn}
                    </div>
                  ))}
                </div>
              )}
              {gea.stats.recentFailures?.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[8px] tracking-widest text-zinc-600 uppercase">Recent Failures</span>
                  {gea.stats.recentFailures.slice(0, 1).map((f, i) => (
                    <div key={i} className="text-[8px] text-red-400 font-mono bg-red-950/20 border border-red-900/30 rounded px-2 py-1 truncate">
                      {f}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <span className="text-[9px] text-zinc-600">Loading GEA data…</span>
          )}
        </Panel>
      </div>

      {/* ── ORACLE-9 THREAT MATRIX ────────────────────────────────────── */}
      <Panel title="ORACLE-9 — Live Threat Matrix" icon={Target} borderColor="border-red-900/40">
        {oracle?.threats ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
            {oracle.threats.slice(0, 5).map((t, i) => (
              <div key={i} className={`rounded border px-3 py-2 space-y-1.5 ${SEVERITY_COLOR[t.severity] ?? 'border-zinc-700/40 bg-zinc-900/20 text-zinc-400'}`}>
                <div className="flex items-center justify-between">
                  <span className="text-[8px] font-bold tracking-widest uppercase text-current">{t.severity}</span>
                  <span className={`text-[8px] ${t.trend === 'UP' ? 'text-red-400' : t.trend === 'DOWN' ? 'text-emerald-400' : 'text-zinc-500'}`}>
                    {t.trend === 'UP' ? '↑' : t.trend === 'DOWN' ? '↓' : '→'}
                  </span>
                </div>
                <div className="text-[9px] font-bold text-zinc-100 leading-tight">{t.label}</div>
                <div className="space-y-0.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[8px] text-zinc-500">P(event) {t.windowHours}h</span>
                    <span className="text-[10px] font-bold font-mono text-current">{(t.probability * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1">
                    <div
                      className={`h-1 rounded-full ${
                        t.severity === 'CRITICAL' ? 'bg-red-500' :
                        t.severity === 'HIGH' ? 'bg-orange-500' :
                        t.severity === 'MODERATE' ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${t.probability * 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-[7px] text-zinc-600 font-mono leading-tight truncate" title={t.topSignal}>
                  {t.topSignal}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <span className="text-[9px] text-zinc-600">Loading threat matrix…</span>
        )}
        {oracle && (
          <div className="text-[8px] text-zinc-600 pt-1 border-t border-zinc-800/40">
            Day {oracle.conflictDay} · Generated {timeAgo(oracle.generatedAt)} · AI: {oracle.aiAvailable ? 'Enhanced' : 'Bayesian'}
          </div>
        )}
      </Panel>

      {/* ── CRON SCHEDULE TABLE ───────────────────────────────────────── */}
      <Panel title="Autonomous Cron Schedule — 14 Jobs" icon={Clock} borderColor="border-zinc-800">
        <div className="overflow-x-auto">
          <table className="w-full text-[8px] font-mono">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left text-zinc-600 uppercase tracking-widest pb-2 pr-4">Job</th>
                <th className="text-left text-zinc-600 uppercase tracking-widest pb-2 pr-4">Layer</th>
                <th className="text-left text-zinc-600 uppercase tracking-widest pb-2 pr-4">Schedule</th>
                <th className="text-left text-zinc-600 uppercase tracking-widest pb-2">Endpoint</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {CRON_SCHEDULE.map(c => (
                <tr key={c.name} className="hover:bg-zinc-900/40">
                  <td className="py-1.5 pr-4 text-zinc-300 font-bold">{c.name}</td>
                  <td className="py-1.5 pr-4">
                    <span className="px-1.5 py-0.5 rounded border border-emerald-800/30 bg-emerald-950/10 text-emerald-400">{c.layer}</span>
                  </td>
                  <td className="py-1.5 pr-4 text-amber-400">{c.schedule}</td>
                  <td className="py-1.5 text-zinc-500 truncate max-w-xs">{c.path}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* ── PLATFORM SEPARATION NOTE ─────────────────────────────────── */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4">
        <div className="flex items-start gap-3">
          <Globe2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-[9px] font-bold tracking-widest text-emerald-300 uppercase">
              Epic Fury AI News Platform — Public vs. Command Separation
            </p>
            <p className="text-[9px] text-zinc-500 leading-relaxed">
              <span className="text-zinc-300">Public Platform</span> (visible to all US Citizens):{' '}
              Live Feed · SITREP · Homeland · Timeline · World Intel · Newsroom · ORBAT · BDA · HVA ·
              Threats · Ceasefire · Intel · Logistics · Econ War · COP · DMO Sim · ORACLE-9
            </p>
            <p className="text-[9px] text-zinc-500 leading-relaxed">
              <span className="text-zinc-300">Command Center</span> (operator only — this page):{' '}
              Governor · Platform Health · AEC · Revenue Engine · Workflow Engine · Neural Truth ·
              Foresight/GEA · Visual Engine · KG/NEXUS · ORACLE-9 internals · Cron Schedule
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}
