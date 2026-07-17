'use client'

import { useCallback, useState } from 'react'
import { GitBranch, ShieldCheck, ExternalLink } from 'lucide-react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { useRouter } from 'next/navigation'
import type { IntelStats } from '@/app/api/intel/stats/route'

interface IntelProvenanceGraphProps {
  limit?: number
}

function normalize(count: number, max: number): number {
  if (max <= 0) return 8
  return Math.max(8, Math.round((count / max) * 100))
}

function verdictTone(verdict: string): string {
  const key = verdict.toUpperCase()
  if (key.includes('VERIFIED') || key.includes('CONFIRMED')) return 'text-emerald-300 border-emerald-800/50 bg-emerald-950/20'
  if (key.includes('LIKELY') || key.includes('DEVELOP')) return 'text-sky-300 border-sky-800/50 bg-sky-950/20'
  if (key.includes('SUSPICIOUS') || key.includes('DISPUT')) return 'text-amber-300 border-amber-800/50 bg-amber-950/20'
  if (key.includes('RETRACT')) return 'text-red-300 border-red-800/50 bg-red-950/20'
  return 'text-zinc-300 border-zinc-700/50 bg-zinc-900/20'
}

export function IntelProvenanceGraph({ limit = 6 }: IntelProvenanceGraphProps) {
  const [stats, setStats] = useState<IntelStats | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/stats', { cache: 'no-store' })
      if (!res.ok) return
      const json: IntelStats = await res.json()
      setStats(json)
    } catch {
      // silent fail to preserve dashboard stability
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchStats, 2 * 60_000)

  if (loading) {
    return (
      <div className="tac-card p-4 animate-pulse">
        <div className="h-3 w-40 bg-zinc-800 rounded mb-3" />
        <div className="h-2 w-full bg-zinc-800 rounded mb-2" />
        <div className="h-2 w-11/12 bg-zinc-800 rounded mb-2" />
        <div className="h-2 w-9/12 bg-zinc-800 rounded" />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="tac-card p-4">
        <p className="text-[10px] tracking-[0.18em] uppercase text-zinc-600">Provenance graph unavailable</p>
      </div>
    )
  }

  const theaters = Object.entries(stats.byTheater ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)

  const verdicts = Object.entries(stats.byVerdict ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)

  const maxTheater = theaters.length > 0 ? theaters[0][1] : 1
  const maxVerdict = verdicts.length > 0 ? verdicts[0][1] : 1

  return (
    <div className="tac-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitBranch size={12} className="text-cyan-400" />
          <p className="text-[9px] tracking-[0.22em] uppercase text-cyan-400">Intel Provenance Graph</p>
        </div>
        <span className="text-[8px] text-zinc-600 tracking-widest uppercase">Auto 2m</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="rounded border border-zinc-800 bg-zinc-950/45 p-2.5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[8px] tracking-[0.2em] uppercase text-zinc-500">Source Theater Flow</p>
            <span className="text-[7px] text-zinc-700 flex items-center gap-0.5"><ExternalLink size={8} />tap to drill</span>
          </div>
          <div className="space-y-1.5">
            {theaters.map(([name, count]) => (
              <button
                key={name}
                className="flex items-center gap-2 w-full group hover:bg-zinc-800/30 rounded px-1 py-0.5 transition-colors"
                onClick={() => router.push(`/dashboard/intel?theater=${encodeURIComponent(name)}`)}
                title={`Drill into ${name} intel feed`}
              >
                <span className="text-[9px] text-zinc-400 w-20 truncate text-left group-hover:text-cyan-400 transition-colors">{name}</span>
                <div className="h-2 rounded bg-zinc-800/70 flex-1 overflow-hidden">
                  <div
                    className="h-full rounded bg-gradient-to-r from-cyan-700/80 to-emerald-500/70 group-hover:from-cyan-500/90 group-hover:to-emerald-400/80 transition-all"
                    style={{ width: `${normalize(count, maxTheater)}%` }}
                  />
                </div>
                <span className="text-[9px] tabular-nums text-zinc-500 w-6 text-right">{count}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded border border-zinc-800 bg-zinc-950/45 p-2.5">
          <p className="text-[8px] tracking-[0.2em] uppercase text-zinc-500 mb-2">Verification Verdict Flow</p>
          <div className="space-y-1.5">
            {verdicts.map(([name, count]) => (
              <div key={name} className="flex items-center gap-2">
                <div className={`text-[8px] tracking-wider uppercase px-1.5 py-0.5 rounded border ${verdictTone(name)}`}>
                  {name}
                </div>
                <div className="h-2 rounded bg-zinc-800/70 flex-1 overflow-hidden">
                  <div
                    className="h-full rounded bg-gradient-to-r from-emerald-700/70 via-amber-600/70 to-red-700/70"
                    style={{ width: `${normalize(count, maxVerdict)}%` }}
                  />
                </div>
                <span className="text-[9px] tabular-nums text-zinc-500 w-6 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-[9px] text-zinc-500 border-t border-zinc-800/70 pt-2">
        <ShieldCheck size={10} className="text-zinc-600" />
        Trust posture: {stats.verified} verified of {stats.total} total reports ({stats.total > 0 ? Math.round((stats.verified / stats.total) * 100) : 0}%).
      </div>
    </div>
  )
}
