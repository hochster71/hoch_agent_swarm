'use client'

import { useEffect, useState } from 'react'
import { Bot, GitPullRequest, Zap, CheckCircle2, Clock, RefreshCw, Play } from 'lucide-react'

interface AECStats {
  totalCycles:  number
  lastCycleAt:  string | null
  byType:       Record<string, number>
  mergedCount:  number
  pendingPRs:   number
}

interface AECCycle {
  cycle_number:        number
  enhancement_type:    string
  enhancement_proposed: string
  pr_url:              string | null
  deployment_status:   string
  auto_merged:         boolean
  duration_ms:         number
  created_at:          string
}

const TYPE_COLOR: Record<string, string> = {
  CODE_MUTATION:  'bg-blue-500/20 text-blue-300 border-blue-500/30',
  PROMPT_UPDATE:  'bg-purple-500/20 text-purple-300 border-purple-500/30',
  SECURITY_PATCH: 'bg-red-500/20 text-red-300 border-red-500/30',
  MONETIZATION:   'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  FORESIGHT:      'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  WORKFLOW:       'bg-green-500/20 text-green-300 border-green-500/30',
}

const STATUS_COLOR: Record<string, string> = {
  MERGED:  'text-green-400',
  PASSED:  'text-blue-400',
  PENDING: 'text-yellow-400',
  FAILED:  'text-red-400',
  SKIPPED: 'text-zinc-500',
}

export default function AutonomousPanel({ compact }: { compact?: boolean }) {
  const [stats,   setStats]   = useState<AECStats | null>(null)
  const [cycles,  setCycles]  = useState<AECCycle[]>([])
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null)

  const triggerHeartbeat = async () => {
    setTriggering(true)
    setTriggerMsg('Triggering governor heartbeat… this may take 1–3 min.')
    try {
      const res  = await fetch('/api/platform/heartbeat')
      const data = await res.json()
      if (res.ok) {
        setTriggerMsg('Heartbeat complete. Refreshing cycles…')
        // Reload cycle data
        const r2   = await fetch('/api/intel/autonomous?limit=8')
        const d2   = await r2.json()
        if (d2.stats)  setStats(d2.stats)
        if (d2.cycles) setCycles(d2.cycles)
        setTriggerMsg(null)
      } else {
        setTriggerMsg(`Error: ${data.error ?? res.status}`)
      }
    } catch (e) {
      setTriggerMsg(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setTriggering(false)
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        const res  = await fetch('/api/intel/autonomous?limit=8')
        const data = await res.json()
        if (data.stats)  setStats(data.stats)
        if (data.cycles) setCycles(data.cycles)
      } catch {}
      setLoading(false)
    }
    load()
    const t = setInterval(load, 60_000)
    return () => clearInterval(t)
  }, [])

  if (compact) {
    return (
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-semibold text-white">Autonomous Enhancement</span>
          </div>
          <span className="text-xs text-zinc-500">AEC</span>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Cycles',  value: stats?.totalCycles ?? '—'  },
            { label: 'Merged',  value: stats?.mergedCount  ?? '—'  },
            { label: 'Pending', value: stats?.pendingPRs   ?? '—'  },
            { label: 'Types',   value: Object.keys(stats?.byType ?? {}).length || '—' },
          ].map(m => (
            <div key={m.label} className="rounded-lg bg-zinc-800/60 p-2 text-center">
              <p className="text-base font-bold text-violet-300">{m.value}</p>
              <p className="text-[10px] text-zinc-500 uppercase tracking-wide">{m.label}</p>
            </div>
          ))}
        </div>

        {/* Recent cycles */}
        <div className="space-y-1">
          {loading && <p className="text-xs text-zinc-600 text-center py-2">Loading…</p>}
          {!loading && cycles.length === 0 && (
            <div className="text-center py-2 space-y-2">
              <p className="text-xs text-zinc-600">No cycles yet</p>
              <button
                onClick={triggerHeartbeat}
                disabled={triggering}
                className="inline-flex items-center gap-1.5 rounded border border-violet-700 bg-violet-950/40 px-2.5 py-1 text-xs text-violet-300 hover:bg-violet-900/40 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="h-3 w-3" />{triggering ? 'Running…' : 'Trigger Heartbeat'}
              </button>
              {triggerMsg && <p className="text-[10px] text-amber-400">{triggerMsg}</p>}
            </div>
          )}
          {cycles.slice(0, 3).map(c => (
            <div key={c.cycle_number} className="flex items-center justify-between gap-2 text-xs">
              <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase font-medium ${TYPE_COLOR[c.enhancement_type] ?? 'bg-zinc-800 text-zinc-400'}`}>
                {(c.enhancement_type ?? '').replace('_', ' ')}
              </span>
              <span className="flex-1 truncate text-zinc-400">{c.enhancement_proposed}</span>
              <span className={`font-mono ${STATUS_COLOR[c.deployment_status] ?? 'text-zinc-500'}`}>
                {c.deployment_status}
              </span>
            </div>
          ))}
        </div>

        {stats?.lastCycleAt && (
          <p className="text-[10px] text-zinc-600">
            Last cycle: {new Date(stats.lastCycleAt).toLocaleTimeString()}
          </p>
        )}
      </section>
    )
  }

  // ── Full panel ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-violet-500/10 p-2 border border-violet-500/30">
            <Bot className="h-5 w-5 text-violet-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Autonomous Enhancement Cycles</h2>
            <p className="text-xs text-zinc-500">Governor self-improves every N heartbeats via Grok research → GPT-4o proposal → GitHub PR</p>
          </div>
        </div>
        <RefreshCw className="h-4 w-4 text-zinc-600 cursor-pointer hover:text-zinc-400" onClick={() => window.location.reload()} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { icon: Zap,            label: 'Total Cycles',   value: stats?.totalCycles ?? '—',  color: 'text-violet-300' },
          { icon: GitPullRequest, label: 'PRs Merged',     value: stats?.mergedCount  ?? '—',  color: 'text-green-300'  },
          { icon: Clock,          label: 'Pending PRs',    value: stats?.pendingPRs   ?? '—',  color: 'text-yellow-300' },
          { icon: CheckCircle2,   label: 'Enhancement Types', value: Object.keys(stats?.byType ?? {}).length || '—', color: 'text-cyan-300' },
          { icon: Bot,            label: 'Last Cycle',     value: stats?.lastCycleAt ? new Date(stats.lastCycleAt).toLocaleTimeString() : '—', color: 'text-zinc-300' },
        ].map(m => (
          <div key={m.label} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3 text-center">
            <m.icon className={`h-4 w-4 mx-auto mb-1 ${m.color}`} />
            <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
            <p className="text-[10px] text-zinc-500 uppercase tracking-wide mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>

      {/* Enhancement type breakdown */}
      {stats && Object.keys(stats.byType).length > 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
          <p className="text-xs text-zinc-500 uppercase tracking-wide mb-3">Enhancement Distribution</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.byType).map(([type, count]) => (
              <span key={type} className={`rounded border px-2 py-1 text-xs font-medium ${TYPE_COLOR[type] ?? 'bg-zinc-800 text-zinc-400'}`}>
                {(type ?? '').replace('_', ' ')} · {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cycle log */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800">
          <p className="text-xs text-zinc-400 uppercase tracking-wide font-medium">Recent Cycles</p>
        </div>
        {loading && <p className="text-sm text-zinc-600 text-center py-8">Loading…</p>}
        {!loading && cycles.length === 0 && (
          <div className="text-center py-8 space-y-3">
            <p className="text-sm text-zinc-600">No autonomous cycles yet.</p>
            <button
              onClick={triggerHeartbeat}
              disabled={triggering}
              className="inline-flex items-center gap-2 rounded border border-violet-700 bg-violet-950/40 px-4 py-2 text-sm text-violet-300 hover:bg-violet-900/40 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Play className="h-4 w-4" />{triggering ? 'Running Governor Cycle…' : 'Trigger Heartbeat'}
            </button>
            {triggerMsg && (
              <p className="text-xs text-amber-400 max-w-sm mx-auto">{triggerMsg}</p>
            )}
          </div>
        )}
        <div className="divide-y divide-zinc-800/60">
          {cycles.map(c => (
            <div key={c.cycle_number} className="px-4 py-3 hover:bg-zinc-800/30 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs font-mono text-zinc-600">#{c.cycle_number}</span>
                  <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase font-medium shrink-0 ${TYPE_COLOR[c.enhancement_type] ?? 'bg-zinc-800 text-zinc-400'}`}>
                    {c.enhancement_type?.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs font-medium ${STATUS_COLOR[c.deployment_status] ?? 'text-zinc-500'}`}>
                    {c.deployment_status}
                  </span>
                  {c.auto_merged && <span className="text-[10px] text-green-400 bg-green-500/10 border border-green-500/20 rounded px-1">AUTO-MERGED</span>}
                  <span className="text-[10px] text-zinc-600">{c.duration_ms}ms</span>
                </div>
              </div>
              <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{c.enhancement_proposed}</p>
              <div className="flex items-center justify-between mt-1">
                {c.pr_url
                  ? <a href={c.pr_url} target="_blank" rel="noreferrer" className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-1"><GitPullRequest className="h-3 w-3" /> View PR</a>
                  : <span className="text-[10px] text-zinc-700">No PR (prompt/foresight update)</span>
                }
                <span className="text-[10px] text-zinc-600">{new Date(c.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
