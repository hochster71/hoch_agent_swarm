'use client'

/**
 * LiveIntelFeed — real-time AI-synthesized intel feed from Supabase
 * Groups intel rows by theater, rendered as live collection "streams".
 * Subscribes to Supabase Realtime so new rows flash in without a page reload.
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Radio, Satellite, Globe, Shield, Zap, Anchor, DollarSign,
  ExternalLink, CheckCircle2, AlertTriangle, Cpu, RefreshCw, ChevronDown, ChevronUp,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'
import type { Intel } from '@/lib/types'

// ── Theater → stream metadata ─────────────────────────────────────────────────

const THEATER_META: Record<string, {
  codename: string
  label:    string
  icon:     React.ReactNode
  color:    string          // text + border tokens
  bg:       string
}> = {
  // Short names (seeded / fallback data)
  Nuclear:    { codename: 'ATLAS',    label: 'SIGINT/GEOINT · Nuclear & Missile',      icon: <Zap    size={12} />, color: 'text-yellow-400 border-yellow-800',  bg: 'bg-yellow-950/10' },
  Air:        { codename: 'TRIDENT',  label: 'SIGINT · IRGCAF Air Operations',         icon: <Radio  size={12} />, color: 'text-emerald-400 border-emerald-800', bg: 'bg-emerald-950/10' },
  Cyber:      { codename: 'CERBERUS', label: 'SIGINT/CYBER · APT + IRGC Cyber',       icon: <Shield size={12} />, color: 'text-purple-400 border-purple-800',   bg: 'bg-purple-950/10' },
  Maritime:   { codename: 'MANTIS',   label: 'SIGINT/HUMINT · Maritime Theater',       icon: <Anchor size={12} />, color: 'text-cyan-400 border-cyan-800',       bg: 'bg-cyan-950/10' },
  Hormuz:     { codename: 'MANTIS',   label: 'SIGINT/HUMINT · Hormuz Strait',          icon: <Anchor size={12} />, color: 'text-red-400 border-red-800',         bg: 'bg-red-950/10' },
  Land:       { codename: 'NEXUS',    label: 'ALL-DOMAIN · Land / Ground Ops',         icon: <Globe  size={12} />, color: 'text-orange-400 border-orange-800',   bg: 'bg-orange-950/10' },
  Gulf:       { codename: 'NEXUS',    label: 'ALL-DOMAIN · Gulf Region',               icon: <Globe  size={12} />, color: 'text-amber-400 border-amber-800',     bg: 'bg-amber-950/10' },
  Diplomatic: { codename: 'NEXUS',    label: 'OSINT/ANALYSIS · Diplomatic Channel',    icon: <Globe  size={12} />, color: 'text-blue-400 border-blue-800',       bg: 'bg-blue-950/10' },
  Economic:   { codename: 'COMPASS',  label: 'ANALYSIS · Economic / Sanctions',        icon: <DollarSign size={12} />, color: 'text-lime-400 border-lime-800',   bg: 'bg-lime-950/10' },
  // Full names (HERALD-3 ingest pipeline output)
  'Persian Gulf / Hormuz':   { codename: 'MANTIS',   label: 'SIGINT/HUMINT · Persian Gulf / Hormuz', icon: <Anchor size={12} />, color: 'text-red-400 border-red-800',    bg: 'bg-red-950/10' },
  'Iran':                    { codename: 'ATLAS',    label: 'ALL-DOMAIN · Iran Theater',              icon: <Zap    size={12} />, color: 'text-yellow-400 border-yellow-800', bg: 'bg-yellow-950/10' },
  'Israel / Levant':         { codename: 'NEXUS',    label: 'ALL-DOMAIN · Israel / Levant',           icon: <Globe  size={12} />, color: 'text-amber-400 border-amber-800', bg: 'bg-amber-950/10' },
  'Red Sea / Yemen':         { codename: 'MANTIS',   label: 'SIGINT/HUMINT · Red Sea / Yemen',        icon: <Anchor size={12} />, color: 'text-cyan-400 border-cyan-800',   bg: 'bg-cyan-950/10' },
  'GCC / Arabian Peninsula': { codename: 'NEXUS',    label: 'ALL-DOMAIN · GCC / Arabian Peninsula',   icon: <Globe  size={12} />, color: 'text-orange-400 border-orange-800', bg: 'bg-orange-950/10' },
  'CONUS':                   { codename: 'CERBERUS', label: 'SIGINT · CONUS Homeland Defense',         icon: <Shield size={12} />, color: 'text-rose-400 border-rose-800',   bg: 'bg-rose-950/10' },
}

const DEFAULT_META = {
  codename: 'NEXUS', label: 'ALL-DOMAIN · Fusion', icon: <Globe size={12} />,
  color: 'text-zinc-400 border-zinc-700', bg: 'bg-zinc-900/20',
}

// ── Conf / source_type badges ─────────────────────────────────────────────────

function ConfBar({ v }: { v: number }) {
  const color = v >= 80 ? 'bg-emerald-500' : v >= 60 ? 'bg-amber-500' : v >= 40 ? 'bg-yellow-600' : 'bg-red-600'
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-[8px] text-zinc-500 tabular-nums w-6 shrink-0">{v}%</span>
      <span className="w-16 h-1 bg-zinc-800 rounded-full overflow-hidden inline-block">
        <span className={cn('h-full block rounded-full', color)} style={{ width: `${v}%` }} />
      </span>
    </span>
  )
}

function SourceTypeBadge({ t }: { t: string | null }) {
  const cfg: Record<string, string> = {
    SIGINT:   'text-sky-400 border-sky-800 bg-sky-950/40',
    Official: 'text-blue-400 border-blue-800 bg-blue-950/40',
    Wire:     'text-amber-400 border-amber-800 bg-amber-950/40',
    Analysis: 'text-violet-400 border-violet-800 bg-violet-950/40',
    OSINT:    'text-lime-400 border-lime-800 bg-lime-950/40',
    Media:    'text-zinc-400 border-zinc-700 bg-zinc-900/40',
  }
  const style = cfg[t ?? ''] ?? cfg.Media
  return (
    <span className={cn('px-1.5 py-0.5 text-[8px] font-bold tracking-widest border rounded-sm', style)}>
      {t ?? 'INT'}
    </span>
  )
}

function VerdictBadge({ tags }: { tags: string[] | null }) {
  if (!tags) return null
  const v = tags.find(t => t.startsWith('verdict:'))?.split(':')[1]?.toUpperCase()
  if (!v || v === 'PENDING') return null
  const cfg: Record<string, string> = {
    VERIFIED:   'text-emerald-400 border-emerald-700',
    DISINFO:    'text-red-400 border-red-700',
    DECEPTIVE:  'text-orange-400 border-orange-700',
    SUSPICIOUS: 'text-yellow-400 border-yellow-700',
  }
  return (
    <span className={cn('px-1 py-0.5 text-[7px] font-bold tracking-widest border rounded-sm', cfg[v] ?? 'text-zinc-500 border-zinc-700')}>
      {v}
    </span>
  )
}

// Extract key facts stored as kf0:, kf1:, kf2: tags
function parseKeyFacts(tags: string[] | null): string[] {
  if (!tags) return []
  return tags
    .filter(t => /^kf[0-2]:/.test(t))
    .sort()
    .map(t => t.replace(/^kf[0-2]:/, '').trim())
    .filter(f => f.length > 0)
}

// Parse corroboration count from corroboration:N tag
function parseCorrobCount(tags: string[] | null): number | null {
  if (!tags) return null
  const tag = tags.find(t => t.startsWith('corroboration:'))
  if (!tag) return null
  const n = parseInt(tag.split(':')[1] ?? '', 10)
  return isNaN(n) ? null : n
}

function timeAgo(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60)   return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

// ── Main component ────────────────────────────────────────────────────────────

interface LiveIntelFeedProps {
  /** Max items to show per theater group */
  perGroup?: number
  /** Total items to fetch */
  limit?: number
  /** Poll interval in ms */
  pollMs?: number
}

export function LiveIntelFeed({ perGroup = 4, limit = 80, pollMs = 60_000 }: LiveIntelFeedProps) {
  const [rows, setRows]             = useState<Intel[]>([])
  const [loading, setLoading]       = useState(true)
  const [err, setErr]               = useState<string | null>(null)
  const [lastFetch, setLastFetch]   = useState<Date | null>(null)
  const [newIds, setNewIds]         = useState<Set<string>>(new Set())
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const prevIds                     = useRef<Set<string>>(new Set())

  const fetchFeed = useCallback(async () => {
    try {
      const res = await fetch(`/api/intel/latest?limit=${limit}&minConfidence=0`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json() as { ok: boolean; items: Intel[]; count: number }
      const items = json.items ?? []
      const incoming = new Set(items.map(i => i.id))
      const fresh    = [...incoming].filter(id => !prevIds.current.has(id))
      if (fresh.length) {
        setNewIds(new Set(fresh))
        setTimeout(() => setNewIds(new Set()), 4000)
      }
      prevIds.current = incoming
      setRows(items)
      setErr(null)
      setLastFetch(new Date())
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'fetch failed')
    } finally {
      setLoading(false)
    }
  }, [limit])

  useSmartPoll(fetchFeed, pollMs)

  // Supabase Realtime — re-fetch on INSERT
  useEffect(() => {
    if (!SUPABASE_CONFIGURED) return
    const sb = createBrowserClient()
    const ch = sb
      .channel('live-intel-feed')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'intel' }, () => {
        void fetchFeed()
      })
      .subscribe()
    return () => { void sb.removeChannel(ch) }
  }, [fetchFeed])

  // Group by theater
  const byTheater = rows.reduce<Record<string, Intel[]>>((acc, r) => {
    const t = r.theater ?? 'Unknown'
    ;(acc[t] ??= []).push(r)
    return acc
  }, {})

  // Sort theaters by item count desc, then alpha
  const theaters = Object.keys(byTheater).sort((a, b) =>
    byTheater[b].length - byTheater[a].length || a.localeCompare(b)
  )

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="tac-card p-4 animate-pulse space-y-2">
            <div className="h-3 bg-zinc-800 rounded w-1/4" />
            <div className="h-2 bg-zinc-800 rounded w-3/4" />
            <div className="h-2 bg-zinc-800 rounded w-2/3" />
          </div>
        ))}
      </div>
    )
  }

  if (err || rows.length === 0) {
    return (
      <div className="tac-card p-5 border-zinc-800 text-center space-y-2">
        <Cpu size={20} className="text-zinc-700 mx-auto" />
        <p className="text-[10px] text-zinc-500 tracking-widest uppercase">
          {err ? `Feed error — ${err}` : 'Awaiting ingest cycle — no intel in database yet'}
        </p>
        <p className="text-[9px] text-zinc-700">
          Ingest cron fires every 5 min. Data will appear automatically once Vercel env vars are pushed.
        </p>
        <button
          onClick={() => { setLoading(true); void fetchFeed() }}
          className="inline-flex items-center gap-1.5 text-[9px] text-zinc-500 hover:text-emerald-400 tracking-widest uppercase transition-colors mt-1"
        >
          <RefreshCw size={9} /> Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {/* Header bar */}
      <div className="flex items-center gap-3 mb-3">
        <Radio size={11} className="text-emerald-400 animate-pulse shrink-0" />
        <span className="text-[10px] font-bold tracking-widest text-zinc-400 uppercase">
          Live Fused Intel — {rows.length} Reports · {theaters.length} Theaters Active
        </span>
        {lastFetch && (
          <span className="ml-auto text-[9px] text-zinc-600 font-mono normal-case font-normal">
            synced {timeAgo(lastFetch.toISOString())} · realtime on
          </span>
        )}
      </div>

      {/* Theater stream cards */}
      {theaters.map(theater => {
        const items = byTheater[theater]
        const meta  = THEATER_META[theater] ?? DEFAULT_META
        const shown = items.slice(0, perGroup)
        const hasMore = items.length > perGroup

        return (
          <div key={theater} className={cn('tac-card p-4 space-y-3', meta.bg, 'border', meta.color.split(' ')[1])}>
            {/* Stream header */}
            <div className="flex items-center justify-between gap-2 border-b border-zinc-800/60 pb-2">
              <div className="flex items-center gap-2">
                <span className={meta.color.split(' ')[0]}>{meta.icon}</span>
                <div>
                  <span className={cn('text-sm font-bold tracking-widest uppercase', meta.color.split(' ')[0])}>
                    {meta.codename}
                  </span>
                  <span className="text-[8px] text-zinc-500 ml-2 tracking-widest uppercase">{meta.label}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[8px] text-emerald-500 tracking-widest font-bold">ACTIVE ●</span>
                <span className="text-[8px] text-zinc-600 tracking-widest">{items.length} RPT{items.length !== 1 ? 'S' : ''}</span>
              </div>
            </div>

            {/* Intel rows */}
            <div className="space-y-2">
              {shown.map(item => {
                const isNew       = newIds.has(item.id)
                const keyFacts    = parseKeyFacts(item.tags)
                const corrobCount = parseCorrobCount(item.tags)
                const isAiPlus    = item.author === 'HERALD-3+AI'
                const isExpanded  = expandedIds.has(item.id)
                const toggleExpand = () => setExpandedIds(prev => {
                  const next = new Set(prev)
                  if (next.has(item.id)) next.delete(item.id)
                  else next.add(item.id)
                  return next
                })
                return (
                  <div
                    key={item.id}
                    className={cn(
                      'bg-zinc-900/60 border rounded p-3 space-y-1.5 transition-all duration-700',
                      isNew ? 'border-emerald-600/60 shadow-[0_0_8px_rgba(16,185,129,0.15)]' : 'border-zinc-800'
                    )}
                  >
                    {/* Row meta */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[9px] text-zinc-600 font-mono tracking-wider">{timeAgo(item.created_at)}</span>
                      <SourceTypeBadge t={item.source_type} />
                      <VerdictBadge tags={item.tags} />
                      {item.verified && (
                        <CheckCircle2 size={9} className="text-emerald-500" aria-label="Verified" />
                      )}
                      {isAiPlus && (
                        <span className="px-1 py-0.5 text-[7px] font-bold tracking-widest border border-violet-700 text-violet-400 rounded-sm">
                          ⬡ AI+
                        </span>
                      )}
                      {corrobCount !== null && corrobCount > 0 && (
                        <span className="px-1 py-0.5 text-[7px] font-bold tracking-widest border border-sky-800 text-sky-400 rounded-sm">
                          {corrobCount}× CORR
                        </span>
                      )}
                      <ConfBar v={item.confidence} />
                      {isNew && (
                        <span className="text-[7px] text-emerald-400 font-bold tracking-widest animate-pulse">NEW</span>
                      )}
                    </div>

                    {/* Title */}
                    <p className="text-[10px] font-bold text-zinc-200 leading-snug">{item.title}</p>

                    {/* Summary */}
                    {item.summary && (
                      <p className="text-[9px] text-zinc-400 leading-relaxed">{item.summary}</p>
                    )}

                    {/* Key facts toggle (only when AI-enhanced with kf: tags) */}
                    {keyFacts.length > 0 && (
                      <div>
                        <button
                          onClick={toggleExpand}
                          className="inline-flex items-center gap-1 text-[8px] text-violet-400 hover:text-violet-300 transition-colors tracking-wider"
                        >
                          {isExpanded ? <ChevronUp size={8} /> : <ChevronDown size={8} />}
                          KEY FACTS ({keyFacts.length})
                        </button>
                        {isExpanded && (
                          <ul className="mt-1 space-y-0.5 pl-2 border-l border-violet-900">
                            {keyFacts.map((f, i) => (
                              <li key={i} className="text-[8px] text-zinc-400 leading-relaxed">• {f}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}

                    {/* Source + citation */}
                    {(item.source_name || item.source_url) && (
                      <div className="flex items-center gap-1.5">
                        {item.source_name && (
                          <span className="text-[8px] text-zinc-600 tracking-wider">{item.source_name}</span>
                        )}
                        {item.source_url && (
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 text-[8px] text-emerald-700 hover:text-emerald-400 transition-colors"
                          >
                            <ExternalLink size={7} /> Source
                          </a>
                        )}
                      </div>
                    )}

                    {/* Action / ORACLE note from tags */}
                    {item.tags?.some(t => t.startsWith('action:')) && (
                      <div className="flex items-start gap-1.5">
                        <AlertTriangle size={8} className="text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-[8px] text-amber-400 leading-relaxed">
                          {item.tags.find(t => t.startsWith('action:'))!.slice(7)}
                        </p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {hasMore && (
              <p className="text-[9px] text-zinc-600 tracking-widest text-right">
                +{items.length - perGroup} more in this theater
              </p>
            )}
          </div>
        )
      })}

      {/* Live IMINT / GEOINT note */}
      <div className="flex items-center gap-2 pt-1">
        <Satellite size={10} className="text-sky-400 shrink-0" />
        <p className="text-[9px] text-zinc-600 leading-relaxed">
          IMINT assessments integrated into theater feeds above. Satellite imagery analysis via Maxar/Planet corroboration where available.
        </p>
      </div>
    </div>
  )
}
