'use client'

import { useCallback, useState } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import type { HeraldRisk, IOCategory } from '@/lib/herald-engine'

interface HeraldScoredItem {
  title:   string
  url:     string
  source:  string
  herald: {
    score:         number
    risk:          HeraldRisk
    flags:         Array<{ category: IOCategory; matched: string; weight: number; description: string }>
    categories:    IOCategory[]
    sourcePenalty: number
    uniqueness:    boolean
  }
}

interface HeraldSummary {
  total:    number
  critical: number
  high:     number
  moderate: number
  clean:    number
  topFlag:  string | null
}

interface HeraldResponse {
  scored:       HeraldScoredItem[]
  summary:      HeraldSummary
  generatedAt:  string
  modelVersion: string
}

const RISK_BADGE: Record<HeraldRisk, string> = {
  CRITICAL: 'bg-red-900/50 text-red-300 border-red-700/50',
  HIGH:     'bg-orange-900/40 text-orange-300 border-orange-700/40',
  MODERATE: 'bg-yellow-900/30 text-yellow-300 border-yellow-700/30',
  LOW:      'bg-blue-900/30 text-blue-300 border-blue-700/30',
  CLEAN:    'bg-slate-900/30 text-slate-400 border-slate-700/30',
}

const RISK_DOT: Record<HeraldRisk, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-500',
  MODERATE: 'bg-yellow-500',
  LOW:      'bg-blue-500',
  CLEAN:    'bg-slate-600',
}

export function HeraldFeed({ limit = 10 }: { limit?: number }) {
  const [data,    setData]    = useState<HeraldResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [showClean, setShowClean] = useState(false)
  const [lastRefresh, setLastRefresh] = useState('')

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/herald', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json() as HeraldResponse
      setData(json)
      setError(null)
      setLastRefresh(new Date().toLocaleTimeString('en-US', { hour12: false }) + 'Z')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fetch error')
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchData, 300_000)

  if (loading) {
    return (
      <div className="bg-slate-900/60 border border-slate-700/50 rounded-sm p-4 animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-64 mb-3" />
        {[1, 2, 3, 4].map(i => <div key={i} className="h-10 bg-slate-800 rounded mb-2" />)}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-slate-900/60 border border-red-900/40 rounded-sm p-4">
        <p className="text-red-400 text-xs font-mono">HERALD-3 OFFLINE — {error ?? 'No data'}</p>
      </div>
    )
  }

  const { summary } = data
  const visibleItems = data.scored
    .filter(s => showClean || s.herald.risk !== 'CLEAN')
    .slice(0, limit)

  return (
    <div className="bg-slate-950/80 border border-slate-700/40 rounded-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-700/40">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${summary.critical > 0 ? 'bg-red-500 animate-pulse' : 'bg-orange-500'}`} />
          <span className="text-xs font-mono font-bold text-slate-200 tracking-widest">HERALD-3</span>
          <span className="text-xs font-mono text-slate-500">{data.modelVersion}</span>
        </div>
        <span className="text-xs font-mono text-slate-600">{lastRefresh}</span>
      </div>

      {/* Summary bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-800/60 text-xs font-mono">
        <span className="text-slate-400">{summary.total} items scored</span>
        {summary.critical > 0 && <span className="text-red-400 font-bold">{summary.critical} CRITICAL</span>}
        {summary.high     > 0 && <span className="text-orange-400">{summary.high} HIGH</span>}
        {summary.moderate > 0 && <span className="text-yellow-400">{summary.moderate} MOD</span>}
        <span className="text-slate-600 ml-auto">{summary.clean} clean</span>
      </div>

      {/* Top flag */}
      {summary.topFlag && (
        <div className="px-4 py-1.5 border-b border-slate-800/40 bg-red-950/20">
          <p className="text-xs font-mono text-red-400">
            ⚡ {summary.topFlag}
          </p>
        </div>
      )}

      {/* Items */}
      <div className="divide-y divide-slate-800/50">
        {visibleItems.map((item, idx) => (
          <div key={idx} className="px-4 py-2.5">
            <div className="flex items-start gap-2">
              <span className={`mt-1 flex-shrink-0 w-1.5 h-1.5 rounded-full ${RISK_DOT[item.herald.risk]}`} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono text-slate-200 leading-snug line-clamp-2">
                  {item.url
                    ? <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-400">
                        {item.title}
                      </a>
                    : item.title
                  }
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-slate-500 font-mono">{item.source}</span>
                  <span className={`text-xs font-mono font-bold px-1.5 border rounded-sm ${RISK_BADGE[item.herald.risk]}`}>
                    {item.herald.risk}
                  </span>
                  <span className="text-xs font-mono text-slate-600">D:{item.herald.score}</span>
                  {item.herald.uniqueness && (
                    <span className="text-xs font-mono text-amber-500">⚠ singleton</span>
                  )}
                </div>
                {/* Top flag for this item */}
                {item.herald.flags[0] && item.herald.risk !== 'CLEAN' && (
                  <p className="text-xs font-mono text-slate-600 mt-0.5 line-clamp-1">
                    {item.herald.flags[0].category.replace(/_/g, ' ')}
                    &nbsp;·&nbsp;
                    <span className="text-slate-500">[{item.herald.flags[0].matched}]</span>
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-slate-800/40 flex items-center justify-between">
        <button
          onClick={() => setShowClean(s => !s)}
          className="text-xs font-mono text-slate-600 hover:text-slate-400 transition-colors"
        >
          {showClean ? 'Hide clean items' : 'Show all items'}
        </button>
        <button
          onClick={() => { void fetchData() }}
          className="text-xs font-mono text-slate-600 hover:text-slate-400 transition-colors"
        >
          ↻ refresh
        </button>
      </div>
    </div>
  )
}
