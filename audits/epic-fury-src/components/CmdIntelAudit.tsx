'use client'

/**
 * CmdIntelAudit
 *
 * Live intel audit stream — polls /api/intel/latest every 15 seconds.
 * Shows every intel item passing through the platform with:
 *   - Full source citation + URL
 *   - Confidence bar
 *   - HERALD-3 disinformation score (extracted from tags)
 *   - Verified / cross-ref status
 *   - Theater tag
 *   - AI verdict badge (from tags)
 *   - Timestamp (absolute + relative)
 *
 * Designed for the Command Authority Center — commander sees EVERYTHING.
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  ShieldCheck, ShieldAlert, ShieldX, ExternalLink,
  RefreshCw, Radio, CheckCircle2, AlertCircle, XCircle,
  Clock, Cpu, FlaskConical,
} from 'lucide-react'

// ─── Types from /api/intel/latest ─────────────────────────────────────────────
interface IntelRow {
  id:           string
  title:        string
  summary:      string
  theater:      string
  confidence:   number
  source_url:   string | null
  source_name:  string | null
  source_type:  string | null
  verified:     boolean
  tags:         string[]
  author:       string | null
  created_at:   string
}

interface LatestResponse {
  ok:    boolean
  items: IntelRow[]
  count: number
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const s  = Math.floor(ms / 1_000)
  if (s < 60)  return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  return `${h}h ${m % 60}m ago`
}

function absTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false,
  }) + 'Z'
}

function getHeraldScore(tags: string[]): number | null {
  const t = tags.find(t => t.startsWith('herald:'))
  if (!t) return null
  return parseInt((t ?? '').replace('herald:', ''), 10)
}

function getVerdict(tags: string[]): string | null {
  const t = tags.find(t => t.startsWith('verdict:'))
  if (!t) return null
  return (t ?? '').replace('verdict:', '')
}

function getSourceTierColor(type: string | null): string {
  switch (type) {
    case 'Official': return 'text-emerald-400 bg-emerald-950/30 border-emerald-800/40'
    case 'Wire':     return 'text-sky-400 bg-sky-950/30 border-sky-800/40'
    case 'Analysis': return 'text-blue-400 bg-blue-950/30 border-blue-800/40'
    case 'SIGINT':   return 'text-purple-400 bg-purple-950/30 border-purple-800/40'
    case 'OSINT':    return 'text-amber-400 bg-amber-950/30 border-amber-800/40'
    default:         return 'text-zinc-400 bg-zinc-900/30 border-zinc-700/30'
  }
}

function getConfidenceColor(c: number): string {
  if (c >= 80) return 'bg-emerald-500'
  if (c >= 60) return 'bg-amber-500'
  if (c >= 40) return 'bg-orange-500'
  return 'bg-red-600'
}

function getHeraldColor(score: number): string {
  if (score >= 75) return 'text-red-400'
  if (score >= 55) return 'text-orange-400'
  if (score >= 35) return 'text-amber-400'
  return 'text-emerald-400'
}

function getVerdictStyle(verdict: string | null): { bg: string; text: string; label: string } {
  switch (verdict) {
    case 'VERIFIED':     return { bg: 'bg-emerald-900/40 border-emerald-700/40', text: 'text-emerald-300', label: '✓ VERIFIED' }
    case 'DISINFORMATION': return { bg: 'bg-red-900/40 border-red-700/40',        text: 'text-red-300',     label: '✗ DISINFO' }
    case 'DECEPTIVE':    return { bg: 'bg-orange-900/40 border-orange-700/40',   text: 'text-orange-300',  label: '⚠ DECEPTIVE' }
    case 'SUSPICIOUS':   return { bg: 'bg-amber-900/40 border-amber-700/40',     text: 'text-amber-300',   label: '~ SUSPICIOUS' }
    case 'PENDING':      return { bg: 'bg-zinc-900/40 border-zinc-700/40',       text: 'text-zinc-400',    label: '○ PENDING' }
    default:             return { bg: 'bg-zinc-900/40 border-zinc-700/40',       text: 'text-zinc-500',    label: '– UNSCORED' }
  }
}

const THEATER_COLOR: Record<string, string> = {
  'Persian Gulf / Hormuz': 'text-blue-400',
  'Hormuz':                'text-blue-400',
  'Iran':                  'text-red-400',
  'Israel / Levant':       'text-amber-400',
  'Cyber':                 'text-purple-400',
  'Red Sea / Yemen':       'text-cyan-400',
  'GCC / Arabian Peninsula': 'text-orange-400',
  'CONUS':                 'text-emerald-400',
  'Air':                   'text-sky-400',
}

const POLL_MS = 15_000

interface Props {
  limit?: number
  compact?: boolean
}

// ─── Component ────────────────────────────────────────────────────────────────
export function CmdIntelAudit({ limit = 30, compact = false }: Props) {
  const [intel,     setIntel]     = useState<IntelRow[]>([])
  const [total,     setTotal]     = useState(0)
  const [loading,   setLoading]   = useState(true)
  const [lastFetch, setLastFetch] = useState<string | null>(null)
  const [error,     setError]     = useState<string | null>(null)
  const [countdown, setCountdown] = useState(POLL_MS / 1_000)
  const [newIds,    setNewIds]    = useState<Set<string>>(new Set())
  const prevIds                   = useRef<Set<string>>(new Set())

  const fetch_ = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/intel/latest?limit=${limit}&minConfidence=0`,
        { cache: 'no-store' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as LatestResponse
      const rows = data.items ?? []

      // Detect new items for flash effect
      const incoming = new Set(rows.map(r => r.id))
      const added    = new Set([...incoming].filter(id => !prevIds.current.has(id)))
      if (added.size > 0) setNewIds(added)
      prevIds.current = incoming
      setTimeout(() => setNewIds(new Set()), 3_000)

      setIntel(rows)
      setTotal(data.count ?? rows.length)
      setLastFetch(new Date().toISOString())
      setError(null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
      setCountdown(POLL_MS / 1_000)
    }
  }, [limit])

  useSmartPoll(fetch_, POLL_MS)
  useEffect(() => {
    const tickId = setInterval(() => setCountdown(c => Math.max(0, c - 1)), 1_000)
    return () => { clearInterval(tickId) }
  }, [fetch_])

  return (
    <div className="tac-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <Radio size={11} className="text-emerald-400 animate-pulse" />
        <span className="text-[10px] font-mono tracking-widest text-emerald-400 uppercase">
          Live Intel Audit Stream
        </span>
        <span className="text-[9px] text-zinc-600 ml-1">— all sources, all theaters, fully cited</span>
        <div className="ml-auto flex items-center gap-3">
          {total > 0 && (
            <span className="text-[9px] text-zinc-500 font-mono">{total.toLocaleString()} total rows</span>
          )}
          <span className="text-[9px] text-zinc-600 font-mono tabular-nums">
            refresh in {countdown}s
          </span>
          {lastFetch && (
            <span className="text-[9px] text-zinc-600">{timeAgo(lastFetch)}</span>
          )}
        </div>
      </div>

      {/* Legend */}
      {!compact && (
        <div className="flex items-center gap-4 text-[8px] text-zinc-600 border-b border-zinc-800/50 pb-2">
          <span className="flex items-center gap-1"><CheckCircle2 size={8} className="text-emerald-400" /> Verified</span>
          <span className="flex items-center gap-1"><ShieldCheck size={8} className="text-sky-400" /> Cross-ref confirmed</span>
          <span className="flex items-center gap-1"><ShieldAlert size={8} className="text-amber-400" /> HERALD scored</span>
          <span className="flex items-center gap-1"><ShieldX size={8} className="text-red-400" /> Disinformation flag</span>
          <span className="flex items-center gap-1"><Cpu size={8} className="text-purple-400" /> AI extracted</span>
          <span className="flex items-center gap-1"><FlaskConical size={8} className="text-zinc-500" /> Pending verification</span>
        </div>
      )}

      {/* Loading / Error */}
      {loading && (
        <div className="flex items-center gap-2 text-[10px] text-zinc-500 py-4">
          <RefreshCw size={10} className="animate-spin" />
          Connecting to Supabase intel stream...
        </div>
      )}
      {error && (
        <div className="text-[10px] text-red-400 flex items-center gap-2">
          <XCircle size={10} /> {error}
        </div>
      )}

      {/* Intel Feed */}
      {!loading && intel.length === 0 && !error && (
        <div className="text-[10px] text-zinc-600 py-4 text-center">
          No intel in Supabase yet — ingest pipeline writes every 5 min.
        </div>
      )}

      <div className={`space-y-2 ${compact ? 'max-h-64' : 'max-h-[580px]'} overflow-y-auto pr-1 scrollbar-thin`}>
        {intel.map(item => {
          const heraldScore = getHeraldScore(item.tags)
          const verdict     = getVerdict(item.tags)
          const verdictStyle = getVerdictStyle(verdict)
          const isNew       = newIds.has(item.id)
          const theaterColor = THEATER_COLOR[item.theater] ?? 'text-zinc-400'

          return (
            <div
              key={item.id}
              className={`
                border rounded-sm p-3 space-y-1.5 transition-all duration-700
                ${isNew ? 'border-emerald-700/70 bg-emerald-950/15 shadow-[0_0_8px_rgba(52,211,153,0.12)]' : 'border-zinc-800/40 bg-zinc-950/30'}
              `}
            >
              {/* Row 1: Title + verdict badge */}
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <span className="text-[11px] text-zinc-100 font-medium leading-snug line-clamp-2">
                    {item.title}
                  </span>
                </div>
                <div className={`shrink-0 text-[8px] font-bold px-1.5 py-0.5 rounded border ${verdictStyle.bg} ${verdictStyle.text}`}>
                  {verdictStyle.label}
                </div>
              </div>

              {/* Row 2: Summary */}
              {!compact && item.summary && (
                <p className="text-[9px] text-zinc-500 leading-relaxed line-clamp-2">
                  {item.summary}
                </p>
              )}

              {/* Row 3: Meta strip */}
              <div className="flex items-center gap-2 flex-wrap">
                {/* Theater */}
                <span className={`text-[8px] font-bold tracking-widest uppercase ${theaterColor}`}>
                  {item.theater}
                </span>

                {/* Source tier badge */}
                {item.source_type && (
                  <span className={`text-[8px] px-1.5 py-0 rounded border font-mono ${getSourceTierColor(item.source_type)}`}>
                    {item.source_type}
                  </span>
                )}

                {/* Source name + link */}
                {item.source_name && (
                  <span className="text-[8px] text-zinc-500">
                    {item.source_url ? (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-sky-400 transition-colors flex items-center gap-0.5"
                      >
                        {item.source_name}
                        <ExternalLink size={7} className="inline ml-0.5" />
                      </a>
                    ) : (
                      item.source_name
                    )}
                  </span>
                )}

                {/* Verified indicator */}
                {item.verified && (
                  <span className="flex items-center gap-0.5 text-[8px] text-emerald-400">
                    <CheckCircle2 size={8} /> verified
                  </span>
                )}

                {/* Author (AI engine) */}
                {item.author && (
                  <span className="flex items-center gap-0.5 text-[8px] text-purple-400">
                    <Cpu size={7} /> {item.author}
                  </span>
                )}

                {/* Timestamp */}
                <span className="ml-auto flex items-center gap-0.5 text-[8px] text-zinc-600 font-mono">
                  <Clock size={7} />
                  <span title={absTime(item.created_at)}>{timeAgo(item.created_at)}</span>
                </span>
              </div>

              {/* Row 4: Confidence bar + HERALD score */}
              <div className="flex items-center gap-3">
                {/* Confidence */}
                <div className="flex items-center gap-1.5 flex-1">
                  <span className="text-[8px] text-zinc-600 w-12 shrink-0">CONF</span>
                  <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${getConfidenceColor(item.confidence)}`}
                      style={{ width: `${item.confidence}%` }}
                    />
                  </div>
                  <span className="text-[8px] font-mono text-zinc-400 w-8 text-right tabular-nums">
                    {item.confidence}%
                  </span>
                </div>

                {/* HERALD IO score */}
                {heraldScore !== null && (
                  <div className="flex items-center gap-1">
                    <span className="text-[8px] text-zinc-600">HERALD</span>
                    <span className={`text-[8px] font-bold font-mono tabular-nums ${getHeraldColor(heraldScore)}`}>
                      {heraldScore}/100
                    </span>
                    {heraldScore >= 55 && (
                      <AlertCircle size={8} className={heraldScore >= 75 ? 'text-red-400' : 'text-amber-400'} />
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
