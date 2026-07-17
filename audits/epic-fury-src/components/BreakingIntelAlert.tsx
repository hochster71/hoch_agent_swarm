'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { Zap, X, ChevronLeft, ChevronRight, ExternalLink, ShieldCheck } from 'lucide-react'
import type { BreakingItem } from '@/app/api/intel/breaking/route'

// Theater accent colors
const THEATER_COLOR: Record<string, string> = {
  Nuclear:    'text-yellow-400 border-yellow-500/40 bg-yellow-950/20',
  Air:        'text-sky-400    border-sky-500/40    bg-sky-950/20',
  Cyber:      'text-purple-400 border-purple-500/40 bg-purple-950/20',
  Maritime:   'text-cyan-400   border-cyan-500/40   bg-cyan-950/20',
  Land:       'text-orange-400 border-orange-500/40 bg-orange-950/20',
  Hormuz:     'text-red-400    border-red-500/40    bg-red-950/20',
  Gulf:       'text-amber-400  border-amber-500/40  bg-amber-950/20',
  Diplomatic: 'text-blue-400   border-blue-500/40   bg-blue-950/20',
  Economic:   'text-lime-400   border-lime-500/40   bg-lime-950/20',
  Homeland:   'text-rose-400   border-rose-500/40   bg-rose-950/20',
}
const defaultColor = 'text-emerald-400 border-emerald-500/40 bg-emerald-950/20'

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60)  return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

/** Key stored in sessionStorage to track dismissed item IDs */
const DISMISSED_KEY = 'breaking_dismissed'

function getDismissed(): Set<string> {
  try {
    const raw = sessionStorage.getItem(DISMISSED_KEY)
    return new Set(raw ? JSON.parse(raw) : [])
  } catch { return new Set() }
}

function dismissItem(id: string) {
  try {
    const set = getDismissed()
    set.add(id)
    sessionStorage.setItem(DISMISSED_KEY, JSON.stringify([...set]))
  } catch { /* ignore */ }
}

/**
 * BreakingIntelAlert
 * Polls /api/intel/breaking every 30s. When new high-confidence items exist
 * that haven't been dismissed, shows an animated red/amber banner across the top
 * of the dashboard with cycling items and per-item dismiss capability.
 */
export function BreakingIntelAlert() {
  const [items, setItems]       = useState<BreakingItem[]>([])
  const [idx, setIdx]           = useState(0)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())
  const [collapsed]         = useState(false)
  const [_tick, setTick]    = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load dismissed from sessionStorage on mount
  useEffect(() => {
    setDismissed(getDismissed())
  }, [])

  const fetchBreaking = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/breaking', { cache: 'no-store' })
      if (!res.ok) return
      const json = await res.json()
      if (json.ok && Array.isArray(json.items)) {
        setItems(json.items)
        setIdx(0)
      }
    } catch { /* ignore network errors */ }
  }, [])

  // Initial fetch + 30s polling
  useSmartPoll(fetchBreaking, 30_000)

  // Auto-advance through items every 8 seconds
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setIdx(prev => (prev + 1) % Math.max(1, visible.length))
      setTick(t => t + 1)
    }, 8_000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, dismissed])

  const visible = items.filter(it => !dismissed.has(it.id))

  const handleDismiss = (id: string) => {
    dismissItem(id)
    const next = new Set(dismissed)
    next.add(id)
    setDismissed(next)
    setIdx(0)
  }

  const handleDismissAll = () => {
    visible.forEach(it => dismissItem(it.id))
    const next = new Set(dismissed)
    visible.forEach(it => next.add(it.id))
    setDismissed(next)
  }

  if (visible.length === 0) return null

  const current = visible[idx % visible.length]
  if (!current) return null

  const colorClass = THEATER_COLOR[current.theater] ?? defaultColor

  return (
    <div className={`shrink-0 flex items-stretch border-b ${colorClass} transition-all duration-300`}>
      {/* Pulse indicator + label */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-r border-current/20 bg-red-900/10 shrink-0">
        <Zap size={13} className="text-red-400 animate-pulse shrink-0" />
        <span className="text-[10px] text-red-400 tracking-[0.2em] font-bold uppercase whitespace-nowrap">
          BREAKING
        </span>
        {visible.length > 1 && (
          <span className="text-[10px] text-zinc-500 ml-1">
            {(idx % visible.length) + 1}/{visible.length}
          </span>
        )}
      </div>

      {/* Theater badge */}
      <div className="flex items-center px-3 shrink-0">
        <span className="text-[10px] tracking-widest font-bold uppercase opacity-80">
          {current.theater}
        </span>
      </div>

      {/* Title / summary */}
      <div
        className={`flex-1 flex items-center gap-2.5 px-3 py-2.5 min-w-0 ${collapsed ? 'hidden' : ''}`}
      >
        {current.verified && (
          <ShieldCheck size={12} className="text-emerald-400 shrink-0" />
        )}
        <span className="text-[11px] text-zinc-100 font-medium truncate">
          {current.title}
        </span>
        <span className="hidden sm:block text-[10px] text-zinc-500 truncate max-w-xs">
          {current.summary}
        </span>
        <span className="text-[10px] text-zinc-600 shrink-0 ml-auto">
          {timeAgo(current.created_at)}
        </span>
        {current.source_url && (
          <a
            href={current.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 p-1.5 text-zinc-500 hover:text-emerald-400 active:scale-95 transition-all"
            aria-label="Source"
          >
            <ExternalLink size={13} />
          </a>
        )}
      </div>

      {/* Navigation + close controls — 44px touch targets */}
      <div className="flex items-center gap-1 px-2 shrink-0">
        {visible.length > 1 && (
          <>
            <button
              onClick={() => setIdx(prev => (prev - 1 + visible.length) % visible.length)}
              className="flex items-center justify-center w-9 h-9 rounded-md text-zinc-600 hover:text-zinc-300 hover:bg-zinc-800/50 active:scale-95 transition-all"
              aria-label="Previous alert"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setIdx(prev => (prev + 1) % visible.length)}
              className="flex items-center justify-center w-9 h-9 rounded-md text-zinc-600 hover:text-zinc-300 hover:bg-zinc-800/50 active:scale-95 transition-all"
              aria-label="Next alert"
            >
              <ChevronRight size={16} />
            </button>
          </>
        )}
        <button
          onClick={() => handleDismiss(current.id)}
          className="flex items-center justify-center w-9 h-9 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-950/30 active:scale-95 transition-all"
          aria-label="Dismiss this alert"
          title="Dismiss"
        >
          <X size={14} />
        </button>
        {visible.length > 1 && (
          <button
            onClick={handleDismissAll}
            className="text-[9px] text-zinc-700 hover:text-zinc-400 px-2 py-1.5 rounded-md hover:bg-zinc-800/40 tracking-wider active:scale-95 transition-all"
            title="Dismiss all"
          >
            ALL
          </button>
        )}
      </div>
    </div>
  )
}
