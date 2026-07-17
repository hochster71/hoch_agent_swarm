'use client'

/**
 * FreshnessGuard — Real-time content freshness indicator
 *
 * Tracks content age across all dashboard data sources and displays
 * a compact status badge. Turns from green → amber → red as content ages
 * past its SLA. Integrates with the freshness engine to provide 24/7
 * autonomous staleness detection.
 */

import { useEffect, useState, useCallback } from 'react'
import { cn } from '@/lib/utils'

interface FreshnessSource {
  label: string
  endpoint: string          // API endpoint to probe for freshness
  slaMs: number             // Max acceptable age in ms
  timestampKey?: string     // JSON key containing the timestamp (default: 'generatedAt')
}

const SOURCES: FreshnessSource[] = [
  { label: 'Intel Pipeline',    endpoint: '/api/platform/status', slaMs: 10 * 60_000,   timestampKey: 'generatedAt' },
  { label: 'Threat Model',      endpoint: '/api/oracle',          slaMs: 30 * 60_000,   timestampKey: 'generatedAt' },
  { label: 'Intel Digest',      endpoint: '/api/intel/digest',    slaMs: 30 * 60_000,   timestampKey: 'generatedAt' },
  { label: 'News Feed',         endpoint: '/api/news',            slaMs: 10 * 60_000,   timestampKey: 'generatedAt' },
]

type FreshnessLevel = 'FRESH' | 'AGING' | 'STALE'

interface SourceState {
  label: string
  level: FreshnessLevel
  ageMs: number
  lastChecked: number
}

function levelFromAge(ageMs: number, slaMs: number): FreshnessLevel {
  if (ageMs <= slaMs) return 'FRESH'
  if (ageMs <= slaMs * 2) return 'AGING'
  return 'STALE'
}

function ageLabel(ms: number): string {
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`
  if (ms < 3_600_000) return `${Math.round(ms / 60_000)}m`
  return `${(ms / 3_600_000).toFixed(1)}h`
}

const LEVEL_COLORS: Record<FreshnessLevel, string> = {
  FRESH: 'text-emerald-400',
  AGING: 'text-amber-400',
  STALE: 'text-red-400',
}

const LEVEL_DOT: Record<FreshnessLevel, string> = {
  FRESH: 'bg-emerald-400',
  AGING: 'bg-amber-400',
  STALE: 'bg-red-400',
}

export function FreshnessGuard({ compact = true }: { compact?: boolean }) {
  const [sources, setSources] = useState<SourceState[]>([])
  const [expanded, setExpanded] = useState(false)

  const probe = useCallback(async () => {
    const now = Date.now()
    const results: SourceState[] = []

    await Promise.allSettled(
      SOURCES.map(async (src) => {
        try {
          const ctrl = new AbortController()
          const timer = setTimeout(() => ctrl.abort(), 8000)
          const res = await fetch(src.endpoint, {
            cache: 'no-store',
            signal: ctrl.signal,
          })
          clearTimeout(timer)

          if (!res.ok) {
            results.push({ label: src.label, level: 'STALE', ageMs: Infinity, lastChecked: now })
            return
          }

          const json = await res.json()
          const ts = json[src.timestampKey ?? 'generatedAt'] as string | undefined
          const ageMs = ts ? now - new Date(ts).getTime() : Infinity
          results.push({
            label: src.label,
            level: levelFromAge(ageMs, src.slaMs),
            ageMs,
            lastChecked: now,
          })
        } catch {
          results.push({ label: src.label, level: 'STALE', ageMs: Infinity, lastChecked: now })
        }
      })
    )

    setSources(results)
  }, [])

  // Initial probe + interval (every 60s, respects visibility/network)
  useEffect(() => {
    probe()

    const interval = setInterval(() => {
      if (typeof navigator !== 'undefined' && !navigator.onLine) return
      if (typeof document !== 'undefined' && document.hidden) return
      probe()
    }, 60_000)

    // Re-probe on visibility / network return
    const onVisible = () => { if (!document.hidden) probe() }
    const onOnline = () => probe()
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('online', onOnline)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('online', onOnline)
    }
  }, [probe])

  // Compute overall level
  const overallLevel: FreshnessLevel = sources.some(s => s.level === 'STALE')
    ? 'STALE'
    : sources.some(s => s.level === 'AGING')
      ? 'AGING'
      : 'FRESH'

  const staleCount = sources.filter(s => s.level === 'STALE').length
  const agingCount = sources.filter(s => s.level === 'AGING').length

  if (compact && !expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className={cn(
          'flex items-center gap-1.5 px-2 py-1 rounded text-[9px] font-mono tracking-wider uppercase',
          'border transition-colors hover:bg-zinc-900/50',
          overallLevel === 'FRESH' && 'border-emerald-900/50 text-emerald-500',
          overallLevel === 'AGING' && 'border-amber-900/50 text-amber-500',
          overallLevel === 'STALE' && 'border-red-900/50 text-red-500 animate-pulse',
        )}
        title={`Content Freshness: ${overallLevel} · ${staleCount} stale, ${agingCount} aging`}
      >
        <span className={cn('w-1.5 h-1.5 rounded-full', LEVEL_DOT[overallLevel],
          overallLevel === 'FRESH' && 'animate-pulse'
        )} />
        {overallLevel}
        {staleCount > 0 && <span className="text-red-500">({staleCount})</span>}
      </button>
    )
  }

  return (
    <div className="relative">
      {/* Expanded panel */}
      <div className="absolute right-0 top-full mt-1 z-50 w-72 bg-zinc-950 border border-zinc-800 rounded-lg shadow-xl p-3">
        <div className="flex items-center justify-between mb-2">
          <span className={cn('text-[10px] font-bold tracking-widest uppercase', LEVEL_COLORS[overallLevel])}>
            Content Freshness: {overallLevel}
          </span>
          <button
            onClick={() => setExpanded(false)}
            className="text-zinc-500 hover:text-zinc-300 text-xs"
          >
            ✕
          </button>
        </div>

        <div className="space-y-1.5">
          {sources.map((s) => (
            <div
              key={s.label}
              className="flex items-center justify-between text-[9px] font-mono"
            >
              <span className="text-zinc-400">{s.label}</span>
              <span className={cn(LEVEL_COLORS[s.level])}>
                {s.level} · {s.ageMs === Infinity ? '—' : ageLabel(s.ageMs)}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-2 pt-2 border-t border-zinc-800">
          <button
            onClick={() => { probe(); }}
            className="text-[9px] text-cyan-500 hover:text-cyan-400 font-mono tracking-wider uppercase"
          >
            ↻ Refresh Now
          </button>
        </div>
      </div>

      {/* Compact badge (clickable to collapse) */}
      <button
        onClick={() => setExpanded(false)}
        className={cn(
          'flex items-center gap-1.5 px-2 py-1 rounded text-[9px] font-mono tracking-wider uppercase border',
          overallLevel === 'FRESH' && 'border-emerald-900/50 text-emerald-500',
          overallLevel === 'AGING' && 'border-amber-900/50 text-amber-500',
          overallLevel === 'STALE' && 'border-red-900/50 text-red-500 animate-pulse',
        )}
      >
        <span className={cn('w-1.5 h-1.5 rounded-full', LEVEL_DOT[overallLevel])} />
        {overallLevel}
      </button>
    </div>
  )
}
