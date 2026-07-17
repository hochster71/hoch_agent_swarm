'use client'

/**
 * LiveNewsBoard
 *
 * Real-time scored news feed. Polls /api/news every 90 seconds, then runs
 * each headline through /api/analyze on-demand when the user expands a card.
 *
 * Visual features:
 *  - Risk badge (CRITICAL / HIGH / MODERATE / CLEAN) colour-coded per HERALD-3
 *  - Source tier indicator (T1 / T2 / T3)
 *  - Inline Truth Score bar
 *  - Expandable deep-dive with claims, IO warnings, corroboration, citations
 *  - "VERIFIED / LIKELY TRUE / SUSPICIOUS / DISINFORMATION" verdict pill
 *  - Auto-filters to war-relevant headlines when filter is active
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Eye, ExternalLink,
  ChevronDown, ChevronUp, RefreshCw, Radio, Search, X,
} from 'lucide-react'
import type { AnalysisReport } from '@/app/api/analyze/route'

// ── Types ──────────────────────────────────────────────────────────────────
interface NewsItem {
  title:                string
  url:                  string
  pubDate:              string
  source:               string
  summary:              string
  tier:                 1 | 2 | 3
  // Multi-source corroboration fields
  corroborationCount?:   number
  corroborationSources?: string[]
  credibilityScore?:     number
  singleSource?:         boolean
  // Media bias fields (AllSides-derived)
  mediaBias?:            number
  biasLabel?:            string
  crossIdeological?:     boolean
  leftSources?:          number
  rightSources?:         number
}

interface VerificationMeta {
  totalStories:          number
  singleSourceCount:     number
  multiSourceCount:      number
  crossIdeologicalCount: number
  corroborationRate:     number
  biasSpread: {
    left:   number
    center: number
    right:  number
  }
}

// ── Constants ──────────────────────────────────────────────────────────────
const RISK_STYLES: Record<string, { badge: string; bar: string; glow: string }> = {
  CRITICAL: { badge: 'bg-red-900/80 text-red-300 border-red-700/60',    bar: 'bg-red-500',    glow: 'border-red-900/50' },
  HIGH:     { badge: 'bg-amber-900/70 text-amber-300 border-amber-700/60', bar: 'bg-amber-500', glow: 'border-amber-900/50' },
  MODERATE: { badge: 'bg-yellow-900/50 text-yellow-300 border-yellow-700/40', bar: 'bg-yellow-500', glow: 'border-yellow-900/30' },
  LOW:      { badge: 'bg-zinc-800/60 text-zinc-400 border-zinc-700/40',  bar: 'bg-zinc-500',   glow: 'border-zinc-800/40' },
  CLEAN:    { badge: 'bg-emerald-900/40 text-emerald-400 border-emerald-800/40', bar: 'bg-emerald-500', glow: 'border-zinc-800/30' },
}

const VERDICT_STYLES: Record<string, string> = {
  VERIFIED:      'bg-emerald-900/60 text-emerald-300 border-emerald-700/60',
  LIKELY_TRUE:   'bg-sky-900/60 text-sky-300 border-sky-700/60',
  UNCONFIRMED:   'bg-zinc-800/60 text-zinc-400 border-zinc-700/40',
  SUSPICIOUS:    'bg-amber-900/60 text-amber-300 border-amber-700/60',
  DISINFORMATION:'bg-red-900/80 text-red-300 border-red-700/60',
}

const WAR_KEYWORDS = [
  'iran', 'irgc', 'hormuz', 'israel', 'hezbollah', 'houthi', 'missile', 'nuclear',
  'military', 'strike', 'attack', 'war', 'conflict', 'sanction', 'ceasefire', 'drone',
  'navy', 'centcom', 'pentagon', 'biden', 'netanyahu', 'khamenei', 'uranium', 'iaea',
  'quds', 'ballistic', 'natanz', 'fordow', 'tanker', 'oil', 'brent', 'red sea',
  'strait', 'gulf', 'saudi', 'uae', 'oman', 'iraq', 'syria', 'lebanon', 'bahrain',
  'operation epic fury', 'idf', 'us forces', 'coalition', 'cyber', 'apt',
]

function isWarRelevant(item: NewsItem): boolean {
  const text = `${item.title} ${item.summary}`.toLowerCase()
  return WAR_KEYWORDS.some(k => text.includes(k))
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

// ── Bias helpers ───────────────────────────────────────────────────────────
function biasColor(lean: number): string {
  if (lean <= -1)   return '#60a5fa'   // blue  — Left
  if (lean <= -0.5) return '#93c5fd'   // sky   — Lean Left
  if (lean < 0.5)   return '#94a3b8'   // gray  — Center
  if (lean < 1)     return '#fca5a5'   // rose  — Lean Right
  return '#f87171'                     // red   — Right
}

function biasLabelText(lean: number): string {
  if (lean <= -1)   return 'LEFT'
  if (lean <= -0.5) return 'LEAN LEFT'
  if (lean < 0.5)   return 'CENTER'
  if (lean < 1)     return 'LEAN RIGHT'
  return 'RIGHT'
}

// ── Sub-components ─────────────────────────────────────────────────────────
function TruthScoreBar({ score, verdict }: { score: number; verdict: string }) {
  const color = score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-sky-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-zinc-900 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className={`text-[9px] font-mono font-bold tracking-widest px-1.5 py-0.5 rounded-sm border ${VERDICT_STYLES[verdict] ?? VERDICT_STYLES.UNCONFIRMED}`}>
        {(verdict ?? '').replace('_', ' ')}
      </span>
    </div>
  )
}

function DeepDivePanel({ report }: { report: AnalysisReport }) {
  return (
    <div className="mt-2 border-t border-zinc-800/60 pt-3 space-y-3">
      {/* IO Warnings */}
      {report.ioWarnings.length > 0 && (
        <div className="space-y-1">
          <div className="text-[8px] font-mono tracking-widest text-amber-500">HERALD-3 IO FLAGS ({report.heraldFlags.length})</div>
          {report.heraldFlags.map((f, i) => (
            <div key={i} className="flex items-start gap-2 text-[9px] font-mono">
              <span className="text-amber-400 shrink-0 mt-0.5">⚑</span>
              <span className="text-amber-300/80">[{f.category}]</span>
              <span className="text-zinc-400">[{f.matched}]</span>
              <span className="ml-auto text-zinc-600 shrink-0">+{f.weight}pts</span>
            </div>
          ))}
        </div>
      )}

      {/* Claims */}
      <div className="space-y-1">
        <div className="text-[8px] font-mono tracking-widest text-cyan-500">EXTRACTED CLAIMS ({report.claims.length})</div>
        {report.claims.map((c, i) => (
          <div key={i} className="flex items-center gap-2 text-[9px] font-mono">
            <span className={c.verified ? 'text-emerald-400' : 'text-zinc-500'}>
              {c.verified ? '✓' : '?'}
            </span>
            <span className="text-zinc-300 flex-1">{c.text}</span>
            <span className={`text-[8px] font-bold ${c.confidence >= 70 ? 'text-emerald-400' : c.confidence >= 50 ? 'text-amber-400' : 'text-zinc-500'}`}>
              {c.confidence}%
            </span>
          </div>
        ))}
      </div>

      {/* Corroboration */}
      <div className="space-y-1">
        <div className="text-[8px] font-mono tracking-widest text-violet-400">
          INTEL CORROBORATION — {report.corroboration.count} HIT{report.corroboration.count !== 1 ? 'S' : ''}
        </div>
        {report.corroboration.items.length === 0 ? (
          <div className="text-[9px] font-mono text-zinc-600">No corroborating intel entries found in database.</div>
        ) : (
          report.corroboration.items.slice(0, 3).map((item, i) => (
            <div key={i} className="text-[9px] font-mono flex gap-2">
              <span className="text-violet-400 shrink-0">◆</span>
              <span className="text-zinc-400 flex-1">{item.title.slice(0, 70)}</span>
              <span className="text-violet-400 shrink-0">[{item.theater}]</span>
            </div>
          ))
        )}
      </div>

      {/* ORACLE threat context */}
      {(report.relatedThreats?.length ?? 0) > 0 && (
        <div className="space-y-1">
          <div className="text-[8px] font-mono tracking-widest text-red-400">ORACLE-9 THREAT CONTEXT</div>
          {(report.relatedThreats ?? []).filter(t => t != null).map((t, i) => (
            <div key={i} className="flex items-center gap-2 text-[9px] font-mono">
              <span className="text-red-400 shrink-0">▲</span>
              <span className="text-zinc-300 flex-1">{t.label}</span>
              <span className="text-amber-400">{t.probability != null ? (t.probability * 100).toFixed(1) : '?'}%</span>
            </div>
          ))}
        </div>
      )}

      {/* Verdict & reason */}
      <div className={`rounded-sm border p-2 ${VERDICT_STYLES[report.verdict] ?? VERDICT_STYLES.UNCONFIRMED}`}>
        <div className="text-[8px] tracking-widest font-bold">VERDICT: {(report.verdict ?? '').replace('_', ' ')}</div>
        <div className="text-[9px] mt-1 opacity-90 leading-relaxed">{report.verdictReason}</div>
      </div>

      {/* Citations */}
      <div className="space-y-0.5">
        <div className="text-[8px] font-mono tracking-widest text-zinc-500">CITATIONS ({report.citations.length})</div>
        {report.citations.map((c, i) => (
          <div key={i} className="text-[9px] font-mono text-zinc-500 flex gap-1">
            <span className="text-zinc-700 shrink-0">[{i + 1}]</span>
            <span>{c}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── News card ──────────────────────────────────────────────────────────────
function NewsCard({ item }: { item: NewsItem }) {
  const [expanded,  setExpanded]  = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [report,    setReport]    = useState<AnalysisReport | null>(null)

  // Quick score from title alone (instant, no fetch needed)
  const tierLabel = `T${item.tier}`
  const tierColor = item.tier === 1 ? 'text-emerald-400' : item.tier === 2 ? 'text-sky-400' : 'text-zinc-500'

  const handleExpand = async () => {
    if (!expanded && !report) {
      setAnalyzing(true)
      try {
        const params = new URLSearchParams({
          url:     item.url,
          title:   item.title,
          summary: item.summary,
          source:  item.source,
          tier:    String(item.tier),
        })
        const res  = await fetch(`/api/analyze?${params}`, { cache: 'no-store' })
        const data = await res.json() as AnalysisReport
        setReport(data)
      } catch {
        // Non-fatal
      } finally {
        setAnalyzing(false)
      }
    }
    setExpanded(e => !e)
  }

  const riskStyle = RISK_STYLES[report?.heraldRisk ?? 'CLEAN']

  return (
    <div className={`border rounded-sm p-3 transition-all duration-200 ${riskStyle.glow} hover:bg-zinc-900/40 bg-zinc-950/60`}>
      {/* Header row */}
      <div className="flex items-start gap-2">
        {/* Risk badge (shows after analysis) */}
        {report ? (
          <span className={`shrink-0 text-[7px] font-bold tracking-widest px-1.5 py-0.5 rounded-sm border ${riskStyle.badge}`}>
            {report.heraldRisk}
          </span>
        ) : (
          <span className={`shrink-0 text-[7px] font-bold tracking-widest px-1.5 py-0.5 rounded-sm border border-zinc-700/40 text-zinc-600`}>
            {tierLabel}
          </span>
        )}

        {/* Title */}
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-mono font-semibold text-zinc-200 leading-snug line-clamp-2">
            {item.title}
          </p>
          <div className="flex items-center flex-wrap gap-x-2 gap-y-0.5 mt-1">
            {/* Bias dot */}
            {item.mediaBias !== undefined && (
              <span
                className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                style={{ backgroundColor: biasColor(item.mediaBias) }}
                title={`AllSides: ${biasLabelText(item.mediaBias)}`}
              />
            )}
            <span className={`text-[8px] font-mono ${tierColor}`}>{item.source}</span>
            <span className="text-[8px] text-zinc-600">·</span>
            <span className="text-[8px] text-zinc-600">{relativeTime(item.pubDate)}</span>
            {/* Corroboration badge */}
            {item.crossIdeological ? (
              <span className="text-[7px] font-bold tracking-widest px-1.5 py-0.5 rounded-sm border border-violet-600/60 bg-violet-950/50 text-violet-300">
                ◆ CROSS-VERIFIED L+R
              </span>
            ) : item.singleSource ? (
              <span className="text-[7px] font-bold tracking-widest px-1.5 py-0.5 rounded-sm border border-amber-700/60 bg-amber-950/40 text-amber-400">
                ⚠ SINGLE SOURCE
              </span>
            ) : item.corroborationCount !== undefined && item.corroborationCount > 0 ? (
              <span className="text-[7px] font-bold tracking-widest px-1.5 py-0.5 rounded-sm border border-emerald-700/50 bg-emerald-950/30 text-emerald-400">
                ✓ {item.corroborationCount + 1} SOURCES
              </span>
            ) : null}
            {/* Pre-analysis credibility */}
            {item.credibilityScore !== undefined && !report && (
              <span className={`text-[7px] font-mono ${
                item.credibilityScore >= 70 ? 'text-emerald-500' :
                item.credibilityScore >= 45 ? 'text-sky-400' :
                item.credibilityScore >= 25 ? 'text-amber-400' : 'text-red-400'
              }`}>
                CRED {item.credibilityScore}%
              </span>
            )}
            {report && (
              <>
                <span className="text-[8px] text-zinc-600">·</span>
                <span className="text-[8px] font-mono text-violet-400">Truth {report.truthScore}%</span>
              </>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-600 hover:text-zinc-400"
            onClick={e => e.stopPropagation()}
          >
            <ExternalLink size={10} />
          </a>
          <button
            onClick={handleExpand}
            className="text-zinc-600 hover:text-zinc-300 p-0.5"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
      </div>

      {/* Truth score bar (after analysis) */}
      {report && (
        <div className="mt-2">
          <TruthScoreBar score={report.truthScore} verdict={report.verdict} />
        </div>
      )}

      {/* Summary */}
      {item.summary && !expanded && (
        <p className="text-[9px] font-mono text-zinc-600 mt-1.5 line-clamp-1">{item.summary}</p>
      )}

      {/* Analyzing spinner */}
      {analyzing && (
        <div className="mt-2 flex items-center gap-1.5 text-[9px] font-mono text-cyan-400">
          <div className="w-2 h-2 rounded-full border border-cyan-400 border-t-transparent animate-spin" />
          NEXUS analyzing…
        </div>
      )}

      {/* Deep dive */}
      {expanded && report && <DeepDivePanel report={report} />}
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────
interface LiveNewsBoardProps {
  /** Max items to show (default 40) */
  limit?: number
  /** Whether to pre-filter to war-relevant headlines */
  warFilter?: boolean
  /** Show compact single-column layout */
  compact?: boolean
}

export function LiveNewsBoard({
  limit    = 40,
  warFilter = true,
  compact  = false,
}: LiveNewsBoardProps) {
  const [items,        setItems]        = useState<NewsItem[]>([])
  const [loading,      setLoading]      = useState(true)
  const [lastFetch,    setLastFetch]    = useState<string>('')
  const [filter,       setFilter]       = useState(warFilter)
  const [search,       setSearch]       = useState('')
  const [biasFilter,   setBiasFilter]   = useState<'all' | 'left' | 'center' | 'right'>('all')
  const [sourceCount,  setSourceCount]  = useState(0)
  const [verification, setVerification] = useState<VerificationMeta | null>(null)

  const fetchNews = useCallback(async () => {
    try {
      const res  = await fetch('/api/news', { cache: 'no-store' })
      const data = await res.json() as {
        items:        NewsItem[]
        sources:      string[]
        verification: VerificationMeta
      }
      setItems(data.items ?? [])
      setSourceCount(data.sources?.length ?? 0)
      if (data.verification) setVerification(data.verification)
      setLastFetch(
        new Date().toLocaleTimeString('en-US', { hour12: false, timeZone: 'UTC', hour: '2-digit', minute: '2-digit' }) + 'Z'
      )
    } catch {
      // Non-fatal
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchNews, 30_000)

  // Filtered + searched items
  const displayed = items
    .filter(item => !filter || isWarRelevant(item))
    .filter(item => {
      if (biasFilter === 'all' || item.mediaBias === undefined) return true
      if (biasFilter === 'left')   return item.mediaBias <= -0.5
      if (biasFilter === 'right')  return item.mediaBias >= 0.5
      if (biasFilter === 'center') return item.mediaBias > -0.5 && item.mediaBias < 0.5
      return true
    })
    .filter(item => {
      if (!search) return true
      const q = search.toLowerCase()
      return item.title.toLowerCase().includes(q) || item.source.toLowerCase().includes(q)
    })
    .slice(0, limit)

  const tierCounts = { T1: items.filter(i => i.tier === 1).length, T2: items.filter(i => i.tier === 2).length, T3: items.filter(i => i.tier === 3).length }

  return (
    <div className="space-y-3">
      {/* Control bar */}
      <div className="flex items-center flex-wrap gap-2">
        <div className="flex items-center gap-1.5 text-[9px] font-mono text-emerald-400">
          <Radio size={10} className="animate-pulse" />
          LIVE FEED · {sourceCount} SOURCES · {items.length} HEADLINES
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Source tier counts */}
          <span className="text-[8px] font-mono text-emerald-400">T1:{tierCounts.T1}</span>
          <span className="text-[8px] font-mono text-sky-400">T2:{tierCounts.T2}</span>
          <span className="text-[8px] font-mono text-zinc-500">T3:{tierCounts.T3}</span>

          {/* Bias filters */}
          {(['all', 'left', 'center', 'right'] as const).map((b) => {
            const labels = { all: 'ALL LEAN', left: '◄ LEFT', center: '● CENTER', right: 'RIGHT ►' }
            const active = biasFilter === b
            const colors = {
              all:    active ? 'border-zinc-500 text-zinc-200 bg-zinc-800/60'    : 'border-zinc-800/40 text-zinc-600 hover:text-zinc-400',
              left:   active ? 'border-blue-600 text-blue-300 bg-blue-950/40'    : 'border-zinc-800/40 text-zinc-600 hover:text-blue-400',
              center: active ? 'border-zinc-500 text-zinc-200 bg-zinc-800/60'    : 'border-zinc-800/40 text-zinc-600 hover:text-zinc-300',
              right:  active ? 'border-red-700 text-red-300 bg-red-950/40'       : 'border-zinc-800/40 text-zinc-600 hover:text-red-400',
            }
            return (
              <button key={b} onClick={() => setBiasFilter(b)}
                aria-label={`Filter by ${labels[b]} bias`}
                aria-pressed={active}
                className={`text-[9px] font-mono tracking-widest px-3 min-h-[36px] rounded-lg border transition-all duration-150 active:scale-95 ${colors[b]}`}>
                {labels[b]}
              </button>
            )
          })}

          {/* War filter toggle */}
          <button
            onClick={() => setFilter(f => !f)}
            aria-label={filter ? 'Disable war filter' : 'Enable war filter'}
            aria-pressed={filter}
            className={`text-[9px] font-mono tracking-widest px-3 min-h-[36px] rounded-lg border transition-all duration-150 active:scale-95 ${
              filter
                ? 'border-amber-700/60 text-amber-400 bg-amber-950/30'
                : 'border-zinc-700/40 text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {filter ? '⚑ WAR FILTER ON' : 'ALL SOURCES'}
          </button>

          {/* Manual refresh */}
          <button onClick={fetchNews} className="flex items-center justify-center w-9 h-9 rounded-lg text-zinc-600 hover:text-zinc-300 hover:bg-zinc-800/50 active:scale-95 transition-all" title="Refresh now" aria-label="Refresh news">
            <RefreshCw size={14} />
          </button>
        </div>

        {/* Search */}
        <div className="w-full relative">
          <Search size={10} className="absolute left-2 top-1/2 -translate-y-1/2 text-zinc-600" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search headlines, sources…"
            aria-label="Search headlines and sources"
            className="w-full bg-zinc-900/60 border border-zinc-800/60 rounded-lg pl-7 pr-8 py-2.5 text-[11px] font-mono text-zinc-300 placeholder:text-zinc-700 focus:outline-none focus:border-zinc-600 focus:ring-1 focus:ring-zinc-700"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center justify-center w-8 h-8 rounded-md text-zinc-600 hover:text-zinc-400 hover:bg-zinc-800/50 active:scale-95 transition-all" aria-label="Clear search">
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Verification stats bar */}
      {verification && (
        <div className="border border-zinc-800/60 bg-zinc-950/60 rounded-sm p-2 space-y-2">
          {/* Stat tiles */}
          <div className="grid grid-cols-5 gap-1">
            <div className="text-center">
              <div className="text-[10px] font-mono font-bold text-zinc-200">{verification.totalStories}</div>
              <div className="text-[7px] font-mono tracking-widest text-zinc-600 mt-0.5">TOTAL</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] font-mono font-bold text-emerald-400">{verification.multiSourceCount}</div>
              <div className="text-[7px] font-mono tracking-widest text-emerald-700 mt-0.5">CORROBORATED</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] font-mono font-bold text-violet-400">{verification.crossIdeologicalCount}</div>
              <div className="text-[7px] font-mono tracking-widest text-violet-700 mt-0.5">CROSS-VERIFIED</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] font-mono font-bold text-amber-400">{verification.singleSourceCount}</div>
              <div className="text-[7px] font-mono tracking-widest text-amber-700 mt-0.5">SINGLE SRC</div>
            </div>
            <div className="text-center">
              <div className={`text-[10px] font-mono font-bold ${
                verification.corroborationRate >= 50 ? 'text-emerald-400' :
                verification.corroborationRate >= 30 ? 'text-sky-400' : 'text-amber-400'
              }`}>{verification.corroborationRate}%</div>
              <div className="text-[7px] font-mono tracking-widest text-zinc-600 mt-0.5">CORR RATE</div>
            </div>
          </div>

          {/* Bias spectrum bar */}
          {verification.biasSpread && verification.totalStories > 0 && (() => {
            const total = verification.biasSpread.left + verification.biasSpread.center + verification.biasSpread.right
            if (total === 0) return null
            const lPct = Math.round((verification.biasSpread.left   / total) * 100)
            const cPct = Math.round((verification.biasSpread.center / total) * 100)
            const rPct = 100 - lPct - cPct
            return (
              <div className="space-y-1">
                <div className="text-[7px] font-mono tracking-widest text-zinc-600">SOURCE SPECTRUM (AllSides) — {verification.biasSpread.left}L · {verification.biasSpread.center}C · {verification.biasSpread.right}R</div>
                <div className="flex h-1.5 rounded-full overflow-hidden gap-px">
                  <div className="bg-blue-500 rounded-l-full transition-all" style={{ width: `${lPct}%` }} title={`Left-leaning: ${lPct}%`} />
                  <div className="bg-zinc-500 transition-all" style={{ width: `${cPct}%` }} title={`Center: ${cPct}%`} />
                  <div className="bg-red-500 rounded-r-full transition-all" style={{ width: `${rPct}%` }} title={`Right-leaning: ${rPct}%`} />
                </div>
                <div className="flex justify-between text-[7px] font-mono">
                  <span className="text-blue-400">◄ LEFT {lPct}%</span>
                  <span className="text-zinc-500">CENTER {cPct}%</span>
                  <span className="text-red-400">RIGHT {rPct}% ►</span>
                </div>
              </div>
            )
          })()}

          <div className="text-[7px] font-mono text-zinc-700 pt-0.5">
            ◆ CROSS-VERIFIED = story confirmed by BOTH left-leaning AND right-leaning independent sources — highest truth confidence
          </div>
        </div>
      )}

      {/* Stats bar */}
      <div className="flex items-center gap-4 text-[8px] font-mono text-zinc-600 border-b border-zinc-800/40 pb-2">
        <span>Showing <span className="text-zinc-400">{displayed.length}</span> of {items.length}</span>
        {filter && <span className="text-amber-400">War-relevant filter active</span>}
        {lastFetch && <span className="ml-auto">Last fetch: <span className="text-zinc-400">{lastFetch}</span></span>}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 text-[8px] font-mono text-zinc-600">
        <span className="flex items-center gap-1"><Eye size={8} className="text-zinc-600" /> Click card to run NEXUS deep analysis · results include HERALD IO score, fact-check, ORACLE threat context, full citations</span>
      </div>

      {/* Cards grid */}
      {loading ? (
        <div className="flex items-center gap-2 text-[9px] font-mono text-zinc-600 py-4">
          <div className="w-3 h-3 rounded-full border border-zinc-600 border-t-transparent animate-spin" />
          Fetching headlines from {sourceCount || 20} sources…
        </div>
      ) : displayed.length === 0 ? (
        <div className="text-[9px] font-mono text-zinc-600 py-4 text-center border border-zinc-800/40 rounded-sm">
          No headlines match{filter ? ' the war filter' : ''}. Toggle filter or try a different search.
        </div>
      ) : (
        <div className={compact ? 'space-y-2' : 'grid grid-cols-1 xl:grid-cols-2 gap-2'}>
          {displayed.map((item, i) => (
            <NewsCard key={`${item.url}-${i}`} item={item} />
          ))}
        </div>
      )}

      {/* Disclaimer */}
      <div className="text-[8px] font-mono text-zinc-700 border-t border-zinc-800/30 pt-2 leading-relaxed">
        All headlines are sourced from publicly available RSS feeds. HERALD-3 analysis, truth scores, and verdicts are
        AI-generated assessments based on source credibility, linguistic pattern analysis, and cross-referencing
        against the Intel database. They are informational tools — not legal or certified intelligence judgments.
        Always verify critical information with official primary sources.
      </div>
    </div>
  )
}
