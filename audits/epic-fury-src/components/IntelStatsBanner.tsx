'use client'

/**
 * IntelStatsBanner
 *
 * Compact stats strip showing live aggregate counts from the intel database.
 * Polls /api/intel/stats every 90 seconds.
 *
 * Shows: total items, verified count, HERALD-3 authored, last 24h, top theaters.
 */

import { useEffect, useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { DatabaseZap, ShieldCheck, Cpu, Clock, RefreshCw, TrendingUp } from 'lucide-react'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'
import type { IntelStats } from '@/app/api/intel/stats/route'

const THEATER_DOT: Record<string, string> = {
  Nuclear:    'bg-yellow-500',
  Air:        'bg-sky-500',
  Cyber:      'bg-purple-500',
  Maritime:   'bg-cyan-500',
  Land:       'bg-orange-500',
  Hormuz:     'bg-red-500',
  Gulf:       'bg-amber-500',
  Diplomatic: 'bg-blue-500',
  Economic:   'bg-lime-500',
  Homeland:   'bg-rose-500',
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never'
  const ms = Date.now() - new Date(iso).getTime()
  const m  = Math.floor(ms / 60_000)
  if (m < 1)  return 'Just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`
}

export function IntelStatsBanner() {
  const [stats, setStats]     = useState<IntelStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/stats', { cache: 'no-store' })
      if (!res.ok) return
      const data = await res.json() as IntelStats
      setStats(data)
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [])

  useSmartPoll(fetchStats, 30_000)

  // Supabase Realtime: re-count immediately when a new intel row is inserted
  useEffect(() => {
    if (!SUPABASE_CONFIGURED) return
    const supabase = createBrowserClient()
    const channel  = supabase
      .channel('intel-stats-trigger')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'intel' }, () => {
        void fetchStats()
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [fetchStats])

  if (loading && !stats) {
    return (
      <div className="flex items-center gap-3 text-[9px] text-zinc-700 animate-pulse">
        <DatabaseZap className="w-3 h-3" />
        <span className="tracking-widest">LOADING INTEL STATS…</span>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex items-center gap-2 text-[9px] text-zinc-600">
        <DatabaseZap className="w-3 h-3" />
        <span className="tracking-widest">INTEL DB — AWAITING FIRST INGEST CYCLE</span>
        <button onClick={fetchStats} className="ml-2 text-zinc-700 hover:text-zinc-500" aria-label="Refresh intel stats">
          <RefreshCw className="w-2.5 h-2.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4 flex-wrap">
      {/* Total */}
      <div className="flex items-center gap-1.5">
        <DatabaseZap className="w-3 h-3 text-violet-400" />
        <span className="text-[9px] text-zinc-500 tracking-widest">INTEL DB</span>
        <span className="text-[10px] font-bold font-mono text-violet-300">{stats.total.toLocaleString()}</span>
      </div>

      {/* Divider */}
      <div className="h-3 w-px bg-zinc-800" />

      {/* Verified */}
      <div className="flex items-center gap-1">
        <ShieldCheck className="w-3 h-3 text-emerald-400" />
        <span className="text-[10px] font-mono text-emerald-300">{stats.verified}</span>
        <span className="text-[9px] text-zinc-600">verified</span>
      </div>

      {/* HERALD-3 */}
      <div className="flex items-center gap-1">
        <Cpu className="w-3 h-3 text-sky-400" />
        <span className="text-[10px] font-mono text-sky-300">{stats.heraldAuthored}</span>
        <span className="text-[9px] text-zinc-600">AI-authored</span>
      </div>

      {/* Last 24h */}
      <div className="flex items-center gap-1">
        <TrendingUp className="w-3 h-3 text-amber-400" />
        <span className="text-[10px] font-mono text-amber-300">+{stats.last24h}</span>
        <span className="text-[9px] text-zinc-600">24h</span>
      </div>

      {/* Last added */}
      <div className="flex items-center gap-1">
        <Clock className="w-3 h-3 text-zinc-600" />
        <span className="text-[9px] text-zinc-500 font-mono">{timeAgo(stats.lastAdded)}</span>
      </div>

      {/* Top theatres */}
      {stats.topTheaters.slice(0, 5).map(({ theater, count }) => (
        <div key={theater} className="flex items-center gap-1">
          <div className={`w-1.5 h-1.5 rounded-full ${THEATER_DOT[theater] ?? 'bg-zinc-600'}`} />
          <span className="text-[9px] text-zinc-500">{theater}</span>
          <span className="text-[9px] font-mono text-zinc-400">{count}</span>
        </div>
      ))}

      {/* Refresh */}
      <button
        onClick={fetchStats}
        className="ml-auto text-zinc-700 hover:text-zinc-500 transition-colors"
        title="Refresh intel stats"
      >
        <RefreshCw className="w-2.5 h-2.5" />
      </button>
    </div>
  )
}
