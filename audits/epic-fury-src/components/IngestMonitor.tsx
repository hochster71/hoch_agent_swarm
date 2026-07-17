'use client'

/**
 * IngestMonitor
 *
 * Displays the autonomous pipeline run history and provides a manual
 * trigger button.  Polls /api/ingest/status every 30 seconds.
 *
 * Shows:
 *  - Last run timestamp + how long ago
 *  - Total HERALD-3 intel rows written to Supabase
 *  - Per-run snapshot: conflict day, critical/high/total scored
 *  - Manual "Trigger Now" button (calls /api/ingest directly — works in dev)
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { Activity, RefreshCw, Zap } from 'lucide-react'

interface Snapshot {
  id:            string
  conflict_day:  number
  herald_summary: { total?: number; critical?: number; high?: number }
  created_at:    string
}

interface StatusResponse {
  ok:           boolean
  lastRun:      string | null
  runCount:     number
  intelWritten: number
  snapshots:    Snapshot[]
  error?:       string
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffS  = Math.floor(diffMs / 1000)
  if (diffS < 60)  return `${diffS}s ago`
  const diffM  = Math.floor(diffS / 60)
  if (diffM < 60)  return `${diffM}m ago`
  const diffH  = Math.floor(diffM / 60)
  return `${diffH}h ${diffM % 60}m ago`
}

export function IngestMonitor() {
  const [status,    setStatus]    = useState<StatusResponse | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [triggerMsg, setTriggerMsg] = useState<string>('')

  const fetchStatus = useCallback(async () => {
    try {
      const res  = await fetch('/api/ingest/status', { cache: 'no-store' })
      const data = await res.json() as StatusResponse
      setStatus(data)
    } catch {
      // non-fatal
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchStatus, 30_000)

  const triggerNow = async () => {
    setTriggering(true)
    setTriggerMsg('')
    try {
      const secret = ''  // no secret needed in dev; set CRON_SECRET in prod
      const res = await fetch('/api/ingest', {
        method: 'GET',
        headers: secret ? { Authorization: `Bearer ${secret}` } : {},
      })
      const data = await res.json() as { ok?: boolean; durationMs?: number; intel?: { inserted?: number }; news?: { critical?: number; high?: number } }
      if (data.ok) {
        setTriggerMsg(`✓ Run complete in ${data.durationMs}ms — ${data.intel?.inserted ?? 0} intel rows written`)
      } else {
        setTriggerMsg('✗ Pipeline returned error')
      }
      // Refresh status after a short delay
      setTimeout(fetchStatus, 1500)
    } catch {
      setTriggerMsg('✗ Failed to reach /api/ingest')
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="border border-zinc-800/60 rounded-sm bg-zinc-950/50 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[10px] font-mono tracking-widest text-emerald-400">
          <Activity size={12} className="animate-pulse" />
          AUTONOMOUS PIPELINE MONITOR — /api/ingest
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchStatus}
            title="Refresh status"
            className="flex items-center justify-center w-9 h-9 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 active:scale-95 transition-all"
          >
            <RefreshCw size={14} />
          </button>
          <button
            onClick={triggerNow}
            disabled={triggering}
            className="flex items-center gap-1.5 px-3 min-h-[36px] text-[9px] font-mono tracking-widest border border-amber-700/60 text-amber-400 hover:bg-amber-900/20 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg active:scale-95 transition-all duration-150"
          >
            <Zap size={10} />
            {triggering ? 'RUNNING…' : 'TRIGGER NOW'}
          </button>
        </div>
      </div>

      {triggerMsg && (
        <div className={`text-[9px] font-mono px-2 py-1 rounded-sm border ${triggerMsg.startsWith('✓') ? 'border-emerald-800/60 text-emerald-400 bg-emerald-950/30' : 'border-red-800/60 text-red-400 bg-red-950/30'}`}>
          {triggerMsg}
        </div>
      )}

      {/* Stats row */}
      {loading ? (
        <div className="text-[9px] font-mono text-zinc-600 tracking-widest">LOADING STATUS…</div>
      ) : status?.ok === false ? (
        <div className="text-[9px] font-mono text-red-400">PIPELINE OFFLINE — {status.error}</div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <div className="border border-zinc-800/40 rounded-sm p-2 text-center">
              <div className="text-[18px] font-mono font-bold text-emerald-400">{status?.runCount ?? 0}</div>
              <div className="text-[8px] font-mono tracking-widest text-zinc-500 mt-0.5">RUNS LOGGED</div>
            </div>
            <div className="border border-zinc-800/40 rounded-sm p-2 text-center">
              <div className="text-[18px] font-mono font-bold text-cyan-400">{status?.intelWritten ?? 0}</div>
              <div className="text-[8px] font-mono tracking-widest text-zinc-500 mt-0.5">INTEL WRITTEN</div>
            </div>
            <div className="border border-zinc-800/40 rounded-sm p-2 text-center">
              <div className="text-[18px] font-mono font-bold text-amber-400">5m</div>
              <div className="text-[8px] font-mono tracking-widest text-zinc-500 mt-0.5">CRON INTERVAL</div>
            </div>
          </div>

          {status?.lastRun && (
            <div className="text-[9px] font-mono text-zinc-500">
              Last run: <span className="text-emerald-400">{new Date(status.lastRun).toUTCString().replace('GMT', 'Z').replace(/ \d{4} /, ' ')}</span>
              {' '}· <span className="text-zinc-400">{timeAgo(status.lastRun)}</span>
            </div>
          )}

          {/* Run history table */}
          {(status?.snapshots?.length ?? 0) > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-[9px] font-mono">
                <thead>
                  <tr className="border-b border-zinc-800/60">
                    <th className="pb-1 text-zinc-500 tracking-widest text-left">UTC</th>
                    <th className="pb-1 text-zinc-500 tracking-widest text-center">DAY</th>
                    <th className="pb-1 text-zinc-500 tracking-widest text-center">SCORED</th>
                    <th className="pb-1 text-zinc-500 tracking-widest text-center">CRIT</th>
                    <th className="pb-1 text-zinc-500 tracking-widest text-center">HIGH</th>
                  </tr>
                </thead>
                <tbody>
                  {status!.snapshots.map((s) => (
                    <tr key={s.id} className="border-b border-zinc-900/60">
                      <td className="py-0.5 text-zinc-400">{new Date(s.created_at).toISOString().slice(11, 19)}Z</td>
                      <td className="py-0.5 text-center text-emerald-400">{s.conflict_day}</td>
                      <td className="py-0.5 text-center text-zinc-300">{s.herald_summary?.total ?? '—'}</td>
                      <td className="py-0.5 text-center text-red-400 font-bold">{s.herald_summary?.critical ?? '—'}</td>
                      <td className="py-0.5 text-center text-amber-400">{s.herald_summary?.high ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {status?.snapshots?.length === 0 && (
            <div className="text-[9px] font-mono text-zinc-600 border border-zinc-800/40 rounded-sm p-3 text-center">
              No pipeline runs logged yet.<br />
              <span className="text-zinc-500">Cron triggers every 5 min on Vercel, or click TRIGGER NOW above.</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
