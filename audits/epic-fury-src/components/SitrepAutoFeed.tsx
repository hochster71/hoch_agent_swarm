'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  FileText, ShieldCheck, TrendingUp, TrendingDown, Minus,
  Globe, DollarSign, Activity, Clock, Cpu,
} from 'lucide-react'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'
import type { IntelDigest } from '@/app/api/intel/digest/route'

// ── Color helpers ────────────────────────────────────────────────────────────
const ASSESSMENT_STYLE: Record<string, { border: string; text: string; bg: string; pulse: boolean }> = {
  CRITICAL: { border: 'border-red-600/60',    text: 'text-red-400',    bg: 'bg-red-950/20',    pulse: true  },
  HIGH:     { border: 'border-amber-600/50',  text: 'text-amber-400',  bg: 'bg-amber-950/15',  pulse: false },
  ELEVATED: { border: 'border-yellow-600/40', text: 'text-yellow-400', bg: 'bg-yellow-950/10', pulse: false },
  MODERATE: { border: 'border-emerald-800/40',text: 'text-emerald-400', bg: 'bg-emerald-950/10', pulse: false },
}

const THEATER_DOT: Record<string, string> = {
  Nuclear:    'bg-yellow-400',
  Air:        'bg-sky-400',
  Cyber:      'bg-purple-400',
  Maritime:   'bg-cyan-400',
  Land:       'bg-orange-400',
  Hormuz:     'bg-red-500',
  Gulf:       'bg-amber-400',
  Diplomatic: 'bg-blue-400',
  Economic:   'bg-lime-400',
  Homeland:   'bg-rose-400',
  // Ingest pipeline theater names
  'Persian Gulf / Hormuz':   'bg-red-500',
  'Iran':                    'bg-yellow-400',
  'Israel / Levant':         'bg-amber-400',
  'Red Sea / Yemen':         'bg-cyan-400',
  'GCC / Arabian Peninsula': 'bg-orange-400',
  'CONUS':                   'bg-rose-400',
}
const defaultDot = 'bg-zinc-500'

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'text-red-400',
  HIGH:     'text-amber-400',
  MODERATE: 'text-yellow-300',
  LOW:      'text-zinc-400',
  MINIMAL:  'text-zinc-600',
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'UP')   return <TrendingUp   size={10} className="text-red-400"    />
  if (trend === 'DOWN') return <TrendingDown size={10} className="text-emerald-400" />
  return <Minus size={10} className="text-zinc-500" />
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60)   return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

// ── Main component ───────────────────────────────────────────────────────────
interface SitrepAutoFeedProps {
  /** Poll interval in ms (default 90 s — was 5 min) */
  pollMs?: number
  /** Show collapsed mini-mode */
  compact?: boolean
}

export function SitrepAutoFeed({ pollMs = 90_000, compact = false }: SitrepAutoFeedProps) {
  const [data, setData]       = useState<IntelDigest | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr]         = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)
  const [_expanded, setExpanded]  = useState(false)

  const fetchDigest = useCallback(async () => {
    try {
      const res = await fetch('/api/intel/digest', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json: IntelDigest = await res.json()
      setData(json)
      setErr(null)
      setLastFetch(new Date())
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Fetch failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useSmartPoll(fetchDigest, pollMs)

  // Supabase Realtime — re-run digest on INSERT
  useEffect(() => {
    if (!SUPABASE_CONFIGURED) return
    const supabase = createBrowserClient()
    const channel  = supabase
      .channel('sitrep-digest-trigger')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'intel' }, () => {
        void fetchDigest()
      })
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [fetchDigest])

  if (loading) {
    return (
      <div className="tac-card p-4 animate-pulse">
        <div className="h-3 bg-zinc-800 rounded w-1/3 mb-2" />
        <div className="h-2 bg-zinc-800 rounded w-2/3" />
      </div>
    )
  }

  if (err || !data) {
    return (
      <div className="tac-card p-3 border-zinc-800">
        <p className="text-[10px] text-zinc-600 tracking-wider">SITREP digest unavailable — {err}</p>
      </div>
    )
  }

  const style = ASSESSMENT_STYLE[data.assessmentLevel] ?? ASSESSMENT_STYLE.MODERATE

  // ── Compact mode ─────────────────────────────────────────────────────────
  if (compact) {
    return (
      <div
        className={`tac-card p-3 flex items-center gap-3 cursor-pointer border min-h-[44px] rounded-lg active:scale-[0.98] transition-all duration-150 ${style.border} ${style.bg}`}
        onClick={() => setExpanded(e => !e)}
      >
        <FileText size={12} className={style.text} />
        <span className={`text-[9px] tracking-widest font-bold uppercase ${style.text}`}>
          {data.assessmentLevel}
        </span>
        <span className="text-[9px] text-zinc-500 flex-1 truncate">
          {data.assessmentReason}
        </span>
        <span className="text-[8px] text-zinc-700">
          {lastFetch ? timeAgo(lastFetch.toISOString()) : ''}
        </span>
      </div>
    )
  }

  // ── Full mode ─────────────────────────────────────────────────────────────
  return (
    <div className={`tac-card space-y-4 p-4 border ${style.border} ${style.bg}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <FileText size={13} className={`${style.text} shrink-0 mt-0.5 ${style.pulse ? 'animate-pulse' : ''}`} />
          <div>
            <p className="text-[9px] text-zinc-500 tracking-[0.2em] uppercase mb-0.5">
              NEXUS AI Situation Report — Day {data.conflictDay} · {data.dtg}
            </p>
            <h2 className={`text-xs font-bold tracking-widest uppercase ${style.text}`}>
              ASSESSMENT: {data.assessmentLevel}
            </h2>
            <p className="text-[10px] text-zinc-400 mt-0.5 leading-relaxed max-w-xl">
              {data.assessmentReason}
            </p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[8px] text-zinc-600 tracking-widest">AUTO-UPDATED</p>
          <div className="flex items-center gap-1 justify-end mt-0.5">
            <Clock size={8} className="text-zinc-700" />
            <span className="text-[8px] text-zinc-600 tabular-nums">
              {lastFetch ? timeAgo(lastFetch.toISOString()) : '--'}
            </span>
          </div>
        </div>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { label: '24h INTEL',    value: String(data.total24h),    icon: Activity,    color: 'text-zinc-300' },
          { label: 'VERIFIED',     value: `${data.verified24h} (${data.verifyRate}%)`, icon: ShieldCheck, color: 'text-emerald-400' },
          { label: 'SOURCES',      value: String(data.sourceCount), icon: Globe,       color: 'text-sky-400' },
          { label: 'oil BRENT',    value: `$${data.economics.brentUsd.toFixed(0)}/bbl`,icon: DollarSign, color: 'text-amber-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="tac-card bg-zinc-900/50 p-2 text-center">
            <Icon size={10} className={`${color} mx-auto mb-1`} />
            <p className="text-[8px] text-zinc-600 tracking-widest">{label}</p>
            <p className={`text-xs font-bold tabular-nums ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Theater activity */}
      {data.theaters.length > 0 && (
        <div>
          <p className="text-[8px] text-zinc-600 tracking-[0.2em] uppercase mb-2">Theater Activity</p>
          <div className="flex flex-wrap gap-2">
            {data.theaters.map(t => (
              <div key={t.name} className="flex items-center gap-1.5 bg-zinc-900/60 rounded px-2 py-1">
                <span className={`w-1.5 h-1.5 rounded-full ${THEATER_DOT[t.name] ?? defaultDot}`} />
                <span className="text-[9px] text-zinc-300 font-medium">{t.name}</span>
                <span className="text-[8px] text-zinc-600">{t.count}</span>
                {t.verified > 0 && (
                  <span className="text-[8px] text-emerald-500">✓{t.verified}</span>
                )}
                <span className="text-[8px] text-zinc-700">{t.avgConf}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key developments */}
      {data.keyDevelopments.length > 0 && (
        <div>
          <p className="text-[8px] text-zinc-600 tracking-[0.2em] uppercase mb-2">Key Developments</p>
          <ul className="space-y-1.5">
            {data.keyDevelopments.map((kd, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${THEATER_DOT[kd.theater] ?? defaultDot}`} />
                <div className="min-w-0">
                  <p className="text-[10px] text-zinc-200 leading-relaxed truncate">{kd.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {kd.verified && <ShieldCheck size={8} className="text-emerald-400" />}
                    <span className="text-[8px] text-zinc-600">{kd.theater}</span>
                    <span className="text-[8px] text-zinc-700">{kd.confidence}%</span>
                    {kd.source && <span className="text-[8px] text-zinc-700 truncate">{kd.source}</span>}
                    <span className="text-[8px] text-zinc-700">{timeAgo(kd.created_at)}</span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ORACLE threats */}
      {data.topThreats.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Cpu size={9} className="text-zinc-600" />
            <p className="text-[8px] text-zinc-600 tracking-[0.2em] uppercase">ORACLE-9 Top Threats</p>
          </div>
          <div className="space-y-1">
            {data.topThreats.map((t, i) => (
              <div key={i} className="flex items-center gap-2">
                <TrendIcon trend={t.trend} />
                <span className={`text-[9px] font-medium shrink-0 ${SEVERITY_COLOR[t.severity] ?? 'text-zinc-400'}`}>
                  {t.probability}%
                </span>
                <div className="flex-1 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      t.probability >= 70 ? 'bg-red-600' :
                      t.probability >= 50 ? 'bg-amber-500' :
                      'bg-sky-600'
                    }`}
                    style={{ width: `${t.probability}%` }}
                  />
                </div>
                <span className="text-[9px] text-zinc-400 min-w-0 truncate max-w-[180px]">{t.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* COMPASS economics summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-center">
        {[
          { label: 'Hormuz Flow',  value: `${data.economics.hormuzThroughputMbpd.toFixed(1)} mb/d` },
          { label: 'War-Risk Ins', value: `${data.economics.lloydWarRiskPct.toFixed(2)}% CIF`       },
          { label: 'Global CPI',   value: `+${data.economics.globalCpiImpulsePp.toFixed(2)} pp`     },
        ].map(({ label, value }) => (
          <div key={label} className="bg-zinc-900/40 rounded px-2 py-1.5">
            <p className="text-[8px] text-zinc-600 tracking-wider">{label}</p>
            <p className="text-[10px] text-amber-300 font-mono">{value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
