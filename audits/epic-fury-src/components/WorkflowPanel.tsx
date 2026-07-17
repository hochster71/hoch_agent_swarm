'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import type { WorkflowRun, WorkflowMetrics, WorkflowTask, WorkflowEvent } from '@/lib/workflow-engine'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusColor(status: string): string {
  switch (status) {
    case 'RUNNING':   return 'text-cyan-400'
    case 'COMPLETED': return 'text-green-400'
    case 'FAILED':    return 'text-red-400'
    case 'RETRYING':  return 'text-yellow-400'
    case 'PAUSED':    return 'text-gray-400'
    default:          return 'text-gray-500'
  }
}

function statusDot(status: string): string {
  switch (status) {
    case 'RUNNING':   return 'bg-cyan-400 animate-pulse'
    case 'COMPLETED': return 'bg-green-400'
    case 'FAILED':    return 'bg-red-500'
    case 'RETRYING':  return 'bg-yellow-400 animate-pulse'
    default:          return 'bg-gray-600'
  }
}

function taskStatusColor(status: string): string {
  switch (status) {
    case 'COMPLETED': return 'text-green-400'
    case 'FAILED':    return 'text-red-400'
    case 'SKIPPED':   return 'text-gray-500'
    case 'RUNNING':   return 'text-cyan-400'
    default:          return 'text-gray-400'
  }
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return '—'
  if (ms < 1000)  return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function fmtAge(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  if (diff < 60_000)    return `${Math.floor(diff / 1000)}s ago`
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return `${Math.floor(diff / 86_400_000)}d ago`
}

function priorityBadge(p: number): string {
  if (p >= 9) return 'bg-red-900/60 text-red-300 border-red-700'
  if (p >= 7) return 'bg-orange-900/60 text-orange-300 border-orange-700'
  if (p >= 5) return 'bg-yellow-900/40 text-yellow-300 border-yellow-700'
  return 'bg-gray-800 text-gray-400 border-gray-700'
}

// ---------------------------------------------------------------------------
// Compact variant — 2-row metrics strip + 4 recent run badges
// ---------------------------------------------------------------------------

interface CompactProps { compact: true }

function WorkflowPanelCompact() {
  const [metrics, setMetrics] = useState<WorkflowMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/workflows?limit=4')
      if (!res.ok) return
      const data = await res.json() as { metrics: WorkflowMetrics }
      setMetrics(data.metrics)
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(load, 30_000)

  if (loading) return (
    <div className="border border-gray-800 rounded bg-black/40 p-3 animate-pulse h-20" />
  )

  if (!metrics) return null

  return (
    <div className="border border-cyan-900/40 rounded bg-black/60 p-3 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-cyan-500 tracking-widest uppercase">
          ⚡ Workflow Engine
        </span>
        <span className="text-[10px] text-gray-500 font-mono">
          Temporal-native • Vercel serverless
        </span>
      </div>

      {/* Metrics strip */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'TOTAL',      val: metrics.total,     color: 'text-gray-300' },
          { label: 'RUNNING',    val: metrics.running,   color: 'text-cyan-400' },
          { label: 'COMPLETED',  val: metrics.completed, color: 'text-green-400' },
          { label: 'FAILED',     val: metrics.failed,    color: 'text-red-400' },
        ].map(({ label, val, color }) => (
          <div key={label} className="bg-black/40 rounded px-2 py-1.5 text-center">
            <div className={`text-sm font-bold font-mono ${color}`}>{val}</div>
            <div className="text-[9px] text-gray-600 tracking-widest">{label}</div>
          </div>
        ))}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-[10px] font-mono">
        <span className="text-gray-500">
          SUCCESS: <span className="text-green-400">{metrics.successRate}%</span>
        </span>
        <span className="text-gray-500">
          AVG: <span className="text-cyan-300">{fmtDuration(metrics.avgDurationMs)}</span>
        </span>
        {metrics.retrying > 0 && (
          <span className="text-yellow-400 animate-pulse">
            {metrics.retrying} RETRYING
          </span>
        )}
      </div>

      {/* Recent runs */}
      {metrics.recentRuns.slice(0, 4).map(run => (
        <div key={run.id} className="flex items-center gap-2 text-[10px] font-mono">
          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${statusDot(run.status)}`} />
          <span className="text-gray-400 truncate flex-1">
            {(run.workflow_type ?? '').replace(/_/g, ' ')}
          </span>
          <span className={`${statusColor(run.status)} flex-shrink-0`}>
            {run.status}
          </span>
          <span className="text-gray-600 flex-shrink-0">{fmtAge(run.created_at)}</span>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Run detail sheet — task tree + event log
// ---------------------------------------------------------------------------

function RunDetail({
  run,
  onClose,
}: {
  run:     WorkflowRun
  onClose: () => void
}) {
  const [tasks,  setTasks]  = useState<WorkflowTask[]>([])
  const [events, setEvents] = useState<WorkflowEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const res  = await fetch(`/api/intel/workflows?run=${run.id}`)
        const data = await res.json() as { tasks: WorkflowTask[]; events: WorkflowEvent[] }
        setTasks(data.tasks)
        setEvents(data.events)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [run.id])

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-950 border border-cyan-900/50 rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div>
            <span className="text-cyan-400 font-mono text-sm font-bold">
              {(run.workflow_type ?? '').replace(/_/g, ' ')}
            </span>
            <span className="ml-2 text-[10px] text-gray-500 font-mono">{run.workflow_version}</span>
            <span className={`ml-2 text-xs font-mono ${statusColor(run.status)}`}>{run.status}</span>
          </div>
          <button onClick={onClose} className="text-gray-600 hover:text-gray-300 text-lg leading-none" aria-label="Close workflow detail">✕</button>
        </div>

        {/* Meta */}
        <div className="grid grid-cols-3 gap-3 px-4 py-2 border-b border-gray-800 text-[10px] font-mono">
          <div>
            <span className="text-gray-600">QUEUE: </span>
            <span className="text-gray-300">{run.task_queue}</span>
          </div>
          <div>
            <span className="text-gray-600">PRIORITY: </span>
            <span className={`${run.priority >= 8 ? 'text-red-400' : run.priority >= 6 ? 'text-yellow-400' : 'text-gray-300'}`}>
              {run.priority}/10
            </span>
          </div>
          <div>
            <span className="text-gray-600">DURATION: </span>
            <span className="text-cyan-300">{fmtDuration(run.duration_ms)}</span>
          </div>
          <div>
            <span className="text-gray-600">RETRIES: </span>
            <span className="text-gray-300">{run.retry_count}/{run.max_retries}</span>
          </div>
          <div>
            <span className="text-gray-600">NAMESPACE: </span>
            <span className="text-gray-300">{run.namespace}</span>
          </div>
          <div>
            <span className="text-gray-600">STARTED: </span>
            <span className="text-gray-300">{fmtAge(run.started_at)}</span>
          </div>
          {run.parent_run_id && (
            <div className="col-span-3">
              <span className="text-gray-600">NEXUS PARENT: </span>
              <span className="text-cyan-500 font-mono text-[9px]">{run.parent_run_id}</span>
            </div>
          )}
          {run.error && (
            <div className="col-span-3">
              <span className="text-red-400">ERROR: </span>
              <span className="text-red-300">{run.error}</span>
            </div>
          )}
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-gray-600 font-mono text-sm">
            loading task history…
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-0 divide-x divide-gray-800">
            {/* Task tree */}
            <div className="p-3 space-y-1">
              <div className="text-[10px] text-gray-600 font-mono tracking-widest mb-2">TASKS ({tasks.length})</div>
              {tasks.length === 0 && <div className="text-gray-700 text-xs">no tasks recorded</div>}
              {tasks.map(t => (
                <div key={t.id} className="flex items-center gap-2 text-[10px] font-mono">
                  <span className={`${taskStatusColor(t.status)}`}>
                    {t.status === 'COMPLETED' ? '✓' : t.status === 'FAILED' ? '✗' : t.status === 'SKIPPED' ? '—' : '•'}
                  </span>
                  <span className="text-gray-300 truncate">{t.task_name}</span>
                  <span className={`ml-auto flex-shrink-0 ${taskStatusColor(t.status)}`}>
                    {t.status}
                  </span>
                </div>
              ))}
            </div>

            {/* Event history */}
            <div className="p-3 space-y-1">
              <div className="text-[10px] text-gray-600 font-mono tracking-widest mb-2">EVENTS ({events.length})</div>
              {events.length === 0 && <div className="text-gray-700 text-xs">no events recorded</div>}
              {events.map(ev => (
                <div key={ev.id} className="text-[10px] font-mono">
                  <span className={`${
                    ev.event_type.includes('FAIL')       ? 'text-red-400'    :
                    ev.event_type.includes('COMPLETE')   ? 'text-green-400'  :
                    ev.event_type.includes('ESCALATION') ? 'text-yellow-400' :
                    ev.event_type.includes('NEXUS')      ? 'text-purple-400' :
                    'text-cyan-600'
                  }`}>
                    {ev.event_type}
                  </span>
                  <span className="text-gray-600 ml-2">{fmtAge(ev.created_at)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Full variant — table of workflow runs
// ---------------------------------------------------------------------------

interface FullProps { compact?: false }

function WorkflowPanelFull() {
  const [runs,    setRuns]    = useState<WorkflowRun[]>([])
  const [metrics, setMetrics] = useState<WorkflowMetrics | null>(null)
  const [selected, setSelected] = useState<WorkflowRun | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const res  = await fetch('/api/intel/workflows?limit=30')
      const data = await res.json() as { metrics: WorkflowMetrics; runs: WorkflowRun[] }
      setMetrics(data.metrics)
      setRuns(data.runs)
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(load, 15_000)

  return (
    <div className="space-y-4">
      {/* Metrics header */}
      {metrics && (
        <div className="grid grid-cols-6 gap-3">
          {[
            { label: 'TOTAL',     val: metrics.total,          color: 'text-gray-300' },
            { label: 'RUNNING',   val: metrics.running,        color: 'text-cyan-400' },
            { label: 'COMPLETED', val: metrics.completed,      color: 'text-green-400' },
            { label: 'FAILED',    val: metrics.failed,         color: 'text-red-400' },
            { label: 'SUCCESS %', val: `${metrics.successRate}%`, color: 'text-emerald-400' },
            { label: 'AVG TIME',  val: fmtDuration(metrics.avgDurationMs), color: 'text-cyan-300' },
          ].map(({ label, val, color }) => (
            <div key={label} className="bg-black/40 border border-gray-800 rounded p-3 text-center">
              <div className={`text-lg font-bold font-mono ${color}`}>{val}</div>
              <div className="text-[10px] text-gray-600 tracking-widest mt-1">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Workflow runs table */}
      <div className="border border-gray-800 rounded overflow-hidden">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-gray-800 text-gray-600">
              <th className="text-left px-3 py-2">STATUS</th>
              <th className="text-left px-3 py-2">TYPE</th>
              <th className="text-left px-3 py-2">VER</th>
              <th className="text-left px-3 py-2">PRI</th>
              <th className="text-left px-3 py-2">QUEUE</th>
              <th className="text-left px-3 py-2">DURATION</th>
              <th className="text-left px-3 py-2">RETRIES</th>
              <th className="text-left px-3 py-2">STARTED</th>
              <th className="text-left px-3 py-2">NEXUS</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9} className="text-center py-8 text-gray-700">loading…</td>
              </tr>
            )}
            {!loading && runs.length === 0 && (
              <tr>
                <td colSpan={9} className="text-center py-8 text-gray-700">
                  no workflow runs yet — governor cycles will appear here
                </td>
              </tr>
            )}
            {runs.map(run => (
              <tr
                key={run.id}
                className="border-b border-gray-900 hover:bg-gray-900/40 cursor-pointer transition-colors"
                onClick={() => setSelected(run)}
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${statusDot(run.status)}`} />
                    <span className={statusColor(run.status)}>{run.status}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-gray-300">
                  {(run.workflow_type ?? '').replace(/_/g, ' ')}
                </td>
                <td className="px-3 py-2 text-gray-500">{run.workflow_version}</td>
                <td className="px-3 py-2">
                  <span className={`px-1.5 py-0.5 rounded border text-[10px] ${priorityBadge(run.priority)}`}>
                    P{run.priority}
                  </span>
                </td>
                <td className="px-3 py-2 text-gray-400">{run.task_queue}</td>
                <td className="px-3 py-2 text-cyan-300">{fmtDuration(run.duration_ms)}</td>
                <td className="px-3 py-2 text-gray-400">
                  {run.retry_count}/{run.max_retries}
                </td>
                <td className="px-3 py-2 text-gray-500">{fmtAge(run.started_at)}</td>
                <td className="px-3 py-2">
                  {run.parent_run_id
                    ? <span className="text-purple-400">↑ child</span>
                    : <span className="text-gray-700">—</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <RunDetail run={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Exported component — switches between compact and full based on prop
// ---------------------------------------------------------------------------

export default function WorkflowPanel(props: CompactProps | FullProps) {
  if ('compact' in props && props.compact) {
    return <WorkflowPanelCompact />
  }
  return <WorkflowPanelFull />
}
