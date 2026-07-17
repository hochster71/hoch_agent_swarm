'use client'

/**
 * TheaterIntelFeed
 *
 * Live-polling feed of intel items filtered to a specific theater.
 * Polls /api/intel/latest?theater=X every 45 seconds.
 *
 * Props:
 *   theater        — e.g. "Nuclear", "Cyber", "Air", "Maritime"
 *   limit          — max items to show (default 15)
 *   minConfidence  — filter threshold (default 0)
 *   compact        — smaller card variant
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { RefreshCw, ShieldCheck, ShieldAlert, ExternalLink, DatabaseZap, Clock, Radio } from 'lucide-react'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'
import type { IntelItem } from '@/app/api/intel/latest/route'

interface TheaterIntelFeedProps {
  theater:       string
  limit?:        number
  minConfidence?: number
  compact?:      boolean
}

const THEATER_COLOR: Record<string, string> = {
  Nuclear:    'text-yellow-400',
  Air:        'text-sky-400',
  Cyber:      'text-purple-400',
  Maritime:   'text-cyan-400',
  Land:       'text-orange-400',
  Hormuz:     'text-red-400',
  Gulf:       'text-amber-400',
  Diplomatic: 'text-blue-400',
  Economic:   'text-lime-400',
  Homeland:   'text-rose-400',
  'Persian Gulf / Hormuz':   'text-red-400',
  'Iran':                    'text-yellow-400',
  'Israel / Levant':         'text-amber-400',
  'Red Sea / Yemen':         'text-cyan-400',
  'GCC / Arabian Peninsula': 'text-orange-400',
  'CONUS':                   'text-rose-400',
}

const THEATER_BADGE: Record<string, string> = {
  Nuclear:    'bg-yellow-950/40 border-yellow-800/40 text-yellow-400',
  Air:        'bg-sky-950/40 border-sky-800/40 text-sky-400',
  Cyber:      'bg-purple-950/40 border-purple-800/40 text-purple-400',
  Maritime:   'bg-cyan-950/40 border-cyan-800/40 text-cyan-400',
  Land:       'bg-orange-950/40 border-orange-800/40 text-orange-400',
  Hormuz:     'bg-red-950/40 border-red-800/40 text-red-400',
  Gulf:       'bg-amber-950/40 border-amber-800/40 text-amber-400',
  Diplomatic: 'bg-blue-950/40 border-blue-800/40 text-blue-400',
  Economic:   'bg-lime-950/40 border-lime-800/40 text-lime-400',
  Homeland:   'bg-rose-950/40 border-rose-800/40 text-rose-400',
  'Persian Gulf / Hormuz':   'bg-red-950/40 border-red-800/40 text-red-400',
  'Iran':                    'bg-yellow-950/40 border-yellow-800/40 text-yellow-400',
  'Israel / Levant':         'bg-amber-950/40 border-amber-800/40 text-amber-400',
  'Red Sea / Yemen':         'bg-cyan-950/40 border-cyan-800/40 text-cyan-400',
  'GCC / Arabian Peninsula': 'bg-orange-950/40 border-orange-800/40 text-orange-400',
  'CONUS':                   'bg-rose-950/40 border-rose-800/40 text-rose-400',
}

const SOURCE_TYPE_COLOR: Record<string, string> = {
  wire:     'text-amber-400',
  official: 'text-blue-400',
  analysis: 'text-violet-400',
  regional: 'text-emerald-400',
  blog:     'text-zinc-400',
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const m  = Math.floor(ms / 60_000)
  if (m < 1)  return 'Just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function getVerdict(tags: string[] | null): string | null {
  if (!tags) return null
  const t = tags.find(x => x.startsWith('verdict:'))
  return t ? t.replace('verdict:', '') : null
}

const VERDICT_STYLE: Record<string, string> = {
  VERIFIED:       'bg-emerald-900/60 text-emerald-300 border-emerald-700/40',
  LIKELY_TRUE:    'bg-sky-900/60 text-sky-300 border-sky-700/40',
  UNCONFIRMED:    'bg-zinc-800/60 text-zinc-400 border-zinc-700/40',
  SUSPICIOUS:     'bg-amber-900/60 text-amber-300 border-amber-700/40',
  DISINFORMATION: 'bg-red-900/60 text-red-300 border-red-700/40',
}

export function TheaterIntelFeed({
  theater,
  limit = 15,
  minConfidence = 0,
  compact = false,
}: TheaterIntelFeedProps) {
  const [items, setItems]         = useState<IntelItem[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)
  const [realtimeOk, setRealtimeOk] = useState(false)
  const latestItemsRef = useRef<IntelItem[]>([])

  const fetchItems = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        theater,
        limit:         String(limit),
        minConfidence: String(minConfidence),
      })
      const res = await fetch(`/api/intel/latest?${params}`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as { ok: boolean; items: IntelItem[]; error?: string }
      if (!data.ok) throw new Error(data.error ?? 'API error')
      latestItemsRef.current = data.items
      setItems(data.items)
      setLastFetch(new Date())
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [theater, limit, minConfidence])

  // ── Supabase Realtime: instant push on INSERT/UPDATE for this theater ──────
  useSmartPoll(fetchItems, 30_000)

  useEffect(() => {
    if (!SUPABASE_CONFIGURED) return

    const supabase = createBrowserClient()
    const channel = supabase
      .channel(`theater-intel-${theater.toLowerCase()}`)
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'intel', filter: `theater=eq.${theater}` },
        (payload) => {
          const newItem = payload.new as IntelItem
          if ((newItem.confidence ?? 0) < minConfidence) return
          // Prepend — no re-fetch needed
          const next = [newItem, ...latestItemsRef.current].slice(0, limit)
          latestItemsRef.current = next
          setItems(next)
          setLastFetch(new Date())
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'intel', filter: `theater=eq.${theater}` },
        () => {
          // Updated row (e.g. verified flag flipped by cross-ref cron) → re-fetch to get latest state
          void fetchItems()
        }
      )
      .subscribe((status) => setRealtimeOk(status === 'SUBSCRIBED'))

    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchItems, theater, limit, minConfidence])

  const theaterColor = THEATER_COLOR[theater] ?? 'text-zinc-400'
  const theaterBadge = THEATER_BADGE[theater] ?? 'bg-zinc-900/40 border-zinc-700/40 text-zinc-400'

  if (compact) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1.5">
            <DatabaseZap className={`w-3 h-3 ${theaterColor}`} />
            <span className={`text-[9px] font-bold tracking-widest ${theaterColor}`}>
              {theater.toUpperCase()} INTEL
            </span>
            <span className="text-[9px] text-zinc-600">({items.length})</span>
          </div>
          <button onClick={fetchItems} className="text-zinc-600 hover:text-zinc-400" aria-label="Refresh theater intel">
            <RefreshCw className={`w-2.5 h-2.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        {items.slice(0, 5).map(item => (
          <div key={item.id} className="flex items-start gap-1.5 text-[10px]">
            {item.verified
              ? <ShieldCheck className="w-2.5 h-2.5 text-emerald-400 mt-0.5 flex-shrink-0" />
              : <ShieldAlert className="w-2.5 h-2.5 text-amber-400 mt-0.5 flex-shrink-0" />
            }
            <span className="text-zinc-300 leading-tight line-clamp-2">{item.title}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="tac-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <DatabaseZap className={`w-4 h-4 ${theaterColor}`} />
          <span className={`tac-label tracking-widest ${theaterColor}`}>
            {theater.toUpperCase()} INTEL FEED
          </span>
          {!loading && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded border font-mono ${theaterBadge}`}>
              {items.length} items
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {realtimeOk && (
            <span className="flex items-center gap-1 text-[8px] text-emerald-500 font-mono tracking-widest">
              <Radio className="w-2.5 h-2.5 animate-pulse" />
              LIVE
            </span>
          )}
          {lastFetch && (
            <span className="text-[9px] text-zinc-600 font-mono">
              {timeAgo(lastFetch.toISOString())}
            </span>
          )}
          <button
            onClick={fetchItems}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-[10px] text-red-400 bg-red-900/20 px-2 py-1 rounded">{error}</div>
      )}

      {/* Loading skeleton */}
      {loading && items.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-zinc-900/40 rounded animate-pulse" />
          ))}
        </div>
      )}

      {/* Intel items */}
      <div className="space-y-2 max-h-96 overflow-y-auto pr-1 scrollbar-thin scrollbar-track-zinc-950 scrollbar-thumb-zinc-800">
        {items.map(item => {
          const verdict = getVerdict(item.tags)
          return (
            <div
              key={item.id}
              className="bg-zinc-900/30 border border-zinc-800/40 rounded p-2.5 space-y-1.5 hover:bg-zinc-900/50 transition-colors"
            >
              {/* Title row */}
              <div className="flex items-start gap-2">
                {item.verified
                  ? <ShieldCheck className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                  : <ShieldAlert className="w-3 h-3 text-amber-500 mt-0.5 flex-shrink-0" />
                }
                <p className="text-[11px] text-zinc-200 leading-snug font-medium line-clamp-2 flex-1">
                  {item.title}
                </p>
              </div>

              {/* Summary */}
              {item.summary && (
                <p className="text-[10px] text-zinc-500 leading-relaxed line-clamp-2 pl-5">
                  {item.summary}
                </p>
              )}

              {/* Meta row */}
              <div className="flex items-center gap-2 flex-wrap pl-5">
                {item.source_name && (
                  <span className={`text-[9px] font-mono ${SOURCE_TYPE_COLOR[item.source_type ?? ''] ?? 'text-zinc-500'}`}>
                    {item.source_name}
                  </span>
                )}
                {item.confidence !== null && item.confidence !== undefined && (
                  <span className="text-[9px] text-zinc-600 font-mono">
                    CONF {item.confidence}%
                  </span>
                )}
                {verdict && (
                  <span className={`text-[8px] px-1 rounded border ${VERDICT_STYLE[verdict] ?? 'bg-zinc-800/50 text-zinc-400 border-zinc-700/40'}`}>
                    {(verdict ?? '').replace('_', ' ')}
                  </span>
                )}
                <div className="ml-auto flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5 text-zinc-700" />
                  <span className="text-[9px] text-zinc-600 font-mono">{timeAgo(item.created_at)}</span>
                  {item.source_url && (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-zinc-600 hover:text-zinc-400 ml-1"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Empty state */}
      {!loading && items.length === 0 && (
        <div className="text-center py-6 text-zinc-600 text-[10px] tracking-widest">
          NO {theater.toUpperCase()} INTEL INGESTED YET
        </div>
      )}
    </div>
  )
}
