'use client'

/**
 * LiveRefresher
 *
 * Two-layer autonomous update mechanism:
 *  1. Interval-based: calls router.refresh() on a fixed schedule (default 60s)
 *     so all Server Components re-render with fresh data.
 *  2. Supabase Realtime: subscribes to the `intel` table INSERT channel and
 *     triggers an immediate refresh whenever /api/ingest writes a new row —
 *     no polling lag, push-driven.
 *
 * A subtle "LIVE" indicator pulses in the corner when active.
 */

import { useEffect, useRef, useState, startTransition } from 'react'
import { useRouter } from 'next/navigation'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'

interface LiveRefresherProps {
  /** How often to silently refresh server state (ms). Default: 60 000 */
  intervalMs?: number
  /** Optionally show a visible indicator */
  showIndicator?: boolean
}

export function LiveRefresher({
  intervalMs = 60_000,
  showIndicator = true,
}: LiveRefresherProps) {
  const router   = useRouter()
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastRefreshAtRef = useRef<number>(0)
  const inFlightRef = useRef(false)
  const [tick, setTick]               = useState(0)
  const [lastRefresh, setLastRefresh] = useState<string>('')
  const [realtimeOk, setRealtimeOk]   = useState(false)

  useEffect(() => {
    const MIN_REFRESH_GAP_MS = 5_000

    const refresh = () => {
      if (document.visibilityState !== 'visible') return
      if (typeof navigator !== 'undefined' && navigator.onLine === false) return

      const now = Date.now()
      if (inFlightRef.current) return
      if (now - lastRefreshAtRef.current < MIN_REFRESH_GAP_MS) return

      inFlightRef.current = true
      lastRefreshAtRef.current = now
      startTransition(() => { router.refresh() })
      setTick((t) => t + 1)
      setLastRefresh(
        new Date().toLocaleTimeString('en-US', {
          hour12: false,
          timeZone: 'UTC',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }) + 'Z'
      )

      setTimeout(() => { inFlightRef.current = false }, 10_000)
    }

    // Layer 1 — interval polling at configured rate (default 20 s)
    timerRef.current = setInterval(refresh, intervalMs)

    // Layer 2 — immediate refresh when user switches back to tab
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', handleVisibility)

    // Layer 3 — immediate refresh when network reconnects
    window.addEventListener('online', refresh)

    // Layer 4 — Supabase Realtime: refresh on intel INSERT **and** UPDATE
    type RealtimeChannel = ReturnType<ReturnType<typeof createBrowserClient>['channel']>
    let channel: RealtimeChannel | null = null

    if (SUPABASE_CONFIGURED) {
      const supabase = createBrowserClient()
      channel = supabase
        .channel('intel-live-global')
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'intel' }, () => refresh())
        .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'intel' }, () => refresh())
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'model_snapshots' }, () => refresh())
        .subscribe((status) => {
          setRealtimeOk(status === 'SUBSCRIBED')
        })
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      document.removeEventListener('visibilitychange', handleVisibility)
      window.removeEventListener('online', refresh)
      if (channel) channel.unsubscribe()
    }
  }, [router, intervalMs])

  if (!showIndicator) return null

  return (
    <div
      title={`Auto-refreshing every ${intervalMs / 1000}s · Last: ${lastRefresh || '—'} · ${tick} updates${realtimeOk ? ' · Supabase Realtime connected' : ''}`}
      className="fixed bottom-3 right-3 z-50 flex items-center gap-1.5 px-2 py-1 rounded-sm border border-emerald-900/60 bg-zinc-950/80 backdrop-blur-sm text-[9px] tracking-widest text-emerald-600 select-none pointer-events-none"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
      LIVE{realtimeOk ? ' · RT' : ''} · {lastRefresh || '—'}
    </div>
  )
}
