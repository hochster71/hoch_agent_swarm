'use client'

/**
 * TruthReport
 *
 * Standalone expandable card that displays a full AnalysisReport
 * in a visually rich "classified brief" format.
 *
 * Usage:
 *   <TruthReport report={report} headline="US Targets..." source="Reuters" />
 *   <TruthReport url="/api/analyze?url=...&title=..." autoFetch />
 */

import { useEffect, useState } from 'react'
import {
  ShieldCheck, ShieldAlert, Shield, ShieldX, ShieldQuestion,
  FileText, ListChecks, AlertTriangle, BookOpen, Activity,
  ChevronDown, ChevronUp, ExternalLink,
} from 'lucide-react'
import type { AnalysisReport } from '@/app/api/analyze/route'

// ── Helpers ────────────────────────────────────────────────────────────────
const VERDICT_META: Record<string, { label: string; icon: typeof Shield; ring: string; text: string; bg: string }> = {
  VERIFIED:       { label: 'VERIFIED',        icon: ShieldCheck,    ring: 'border-emerald-600',   text: 'text-emerald-300', bg: 'bg-emerald-950/50' },
  LIKELY_TRUE:    { label: 'LIKELY TRUE',      icon: ShieldCheck,    ring: 'border-sky-600',       text: 'text-sky-300',     bg: 'bg-sky-950/40' },
  UNCONFIRMED:    { label: 'UNCONFIRMED',      icon: ShieldQuestion, ring: 'border-zinc-600',      text: 'text-zinc-400',    bg: 'bg-zinc-900/40' },
  SUSPICIOUS:     { label: 'SUSPICIOUS',       icon: ShieldAlert,    ring: 'border-amber-600',     text: 'text-amber-300',   bg: 'bg-amber-950/40' },
  DISINFORMATION: { label: 'DISINFORMATION',   icon: ShieldX,        ring: 'border-red-600',       text: 'text-red-300',     bg: 'bg-red-950/60' },
}

function TruthBar({ score, verdict }: { score: number; verdict: string }) {
  const meta = VERDICT_META[verdict] ?? VERDICT_META.UNCONFIRMED
  const segments = Array.from({ length: 20 }, (_, i) => i * 5 < score)
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[8px] font-mono">
        <span className="text-zinc-600">TRUTH SCORE</span>
        <span className={`font-bold ${meta.text}`}>{score} / 100</span>
      </div>
      <div className="flex gap-0.5">
        {segments.map((filled, i) => (
          <div
            key={i}
            className={`flex-1 h-2 rounded-[1px] transition-all duration-500 ${
              filled
                ? score >= 80 ? 'bg-emerald-500'
                : score >= 60 ? 'bg-sky-500'
                : score >= 40 ? 'bg-amber-500'
                : 'bg-red-500'
                : 'bg-zinc-800'
            }`}
          />
        ))}
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────
interface TruthReportProps {
  /** Pre-fetched report */
  report?: AnalysisReport
  /** If provided (and report is omitted), will auto-fetch this URL once mounted */
  fetchUrl?: string
  /** Shown in header regardless of report */
  headline?: string
  source?: string
  /** Start expanded (default: false) */
  defaultOpen?: boolean
  /** Called with report once fetched */
  onReport?: (r: AnalysisReport) => void
}

export function TruthReport({
  report: initialReport,
  fetchUrl,
  headline,
  source,
  defaultOpen  = false,
  onReport,
}: TruthReportProps) {
  const [open,     setOpen]    = useState(defaultOpen)
  const [report,   setReport]  = useState<AnalysisReport | null>(initialReport ?? null)
  const [loading,  setLoading] = useState(false)
  const [err,      setErr]     = useState<string | null>(null)

  useEffect(() => {
    if (initialReport) setReport(initialReport)
  }, [initialReport])

  const loadReport = async () => {
    if (report || !fetchUrl) return
    setLoading(true)
    setErr(null)
    try {
      const res = await fetch(fetchUrl, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as AnalysisReport
      setReport(data)
      onReport?.(data)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Fetch failed')
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = () => {
    setOpen(o => !o)
    if (!open && !report) loadReport()
  }

  const meta = report ? (VERDICT_META[report.verdict] ?? VERDICT_META.UNCONFIRMED) : null

  return (
    <div className={`rounded-sm border transition-all duration-200 overflow-hidden ${meta ? `${meta.ring} ${meta.bg}` : 'border-zinc-800/60 bg-zinc-950/60'}`}>
      {/* Toggle header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        {/* Verdict icon */}
        {meta ? (
          <meta.icon size={14} className={meta.text} />
        ) : (
          <FileText size={14} className="text-zinc-600" />
        )}

        {/* Headline + source */}
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-mono font-semibold text-zinc-200 truncate leading-snug">
            {headline ?? report?.title ?? 'NEXUS Analysis Report'}
          </p>
          {(source ?? report?.source) && (
            <span className="text-[8px] font-mono text-zinc-500">{source ?? report?.source}</span>
          )}
        </div>

        {/* Verdict pill */}
        {meta && (
          <span className={`shrink-0 text-[8px] font-mono font-bold tracking-widest px-2 py-0.5 rounded-sm border ${meta.ring} ${meta.text}`}>
            {meta.label}
          </span>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="shrink-0 w-3 h-3 rounded-full border border-cyan-400 border-t-transparent animate-spin" />
        )}

        <span className="shrink-0">
          {open ? <ChevronUp size={12} className="text-zinc-600" /> : <ChevronDown size={12} className="text-zinc-600" />}
        </span>
      </button>

      {/* Body */}
      {open && (
        <div className="px-3 pb-3 space-y-4 border-t border-zinc-800/40">
          {/* Error state */}
          {err && <p className="text-[9px] font-mono text-red-400 pt-2">{err}</p>}

          {/* Loading state */}
          {loading && !report && (
            <div className="flex items-center gap-2 text-[9px] font-mono text-cyan-400 pt-3">
              <div className="w-3 h-3 rounded-full border border-cyan-400 border-t-transparent animate-spin" />
              NEXUS multi-agent pipeline running…
            </div>
          )}

          {report && (
            <>
              {/* Truth score bar */}
              <div className="pt-3">
                <TruthBar score={report.truthScore} verdict={report.verdict} />
              </div>

              {/* Verdict reason */}
              <div className={`rounded-sm p-2 border ${meta!.ring}`}>
                <div className={`text-[8px] font-mono tracking-widest font-bold mb-1 ${meta!.text}`}>
                  ASSESSMENT
                </div>
                <p className="text-[9px] font-mono text-zinc-300 leading-relaxed">{report.verdictReason}</p>
              </div>

              {/* HERALD score breakdown */}
              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <Activity size={10} className="text-amber-400" />
                  <span className="text-[8px] font-mono tracking-widest text-amber-400">
                    HERALD-3 IO SCORE — {report.heraldScore} pts · {report.heraldRisk}
                  </span>
                </div>
                {report.ioWarnings.length > 0 ? (
                  <div className="space-y-0.5">
                    {report.ioWarnings.map((w, i) => (
                      <div key={i} className="text-[9px] font-mono text-amber-300/70 flex gap-1.5">
                        <span className="text-amber-600 shrink-0">⚑</span>
                        <span>{w}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[9px] font-mono text-zinc-600">No IO flags detected.</p>
                )}
                {report.heraldFlags.length > 0 && (
                  <div className="grid grid-cols-2 gap-1">
                    {report.heraldFlags.map((f, i) => (
                      <div key={i} className="text-[8px] font-mono border border-zinc-800/60 rounded-sm px-1.5 py-1 bg-zinc-900/40 flex justify-between">
                        <span className="text-zinc-500">[{f.category}]</span>
                        <span className="text-amber-400">+{f.weight}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Claims */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <ListChecks size={10} className="text-cyan-400" />
                  <span className="text-[8px] font-mono tracking-widest text-cyan-400">
                    EXTRACTED CLAIMS ({report.claims.length})
                  </span>
                </div>
                {report.claims.length === 0 ? (
                  <p className="text-[9px] font-mono text-zinc-600">No verifiable claims extracted.</p>
                ) : (
                  <div className="space-y-1">
                    {report.claims.map((c, i) => (
                      <div key={i} className={`rounded-sm border px-2 py-1.5 flex items-center gap-2 ${c.verified ? 'border-emerald-800/50 bg-emerald-950/30' : 'border-zinc-800/40 bg-zinc-900/30'}`}>
                        <span className={`text-[10px] shrink-0 ${c.verified ? 'text-emerald-400' : 'text-zinc-600'}`}>
                          {c.verified ? '✓' : '○'}
                        </span>
                        <p className="text-[9px] font-mono text-zinc-300 flex-1">{c.text}</p>
                        <span className="text-[8px] font-mono text-zinc-600 shrink-0">{c.source}</span>
                        <span className={`text-[8px] font-mono font-bold shrink-0 ${c.confidence >= 70 ? 'text-emerald-400' : c.confidence >= 50 ? 'text-amber-400' : 'text-zinc-500'}`}>
                          {c.confidence}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Corroboration */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <Shield size={10} className="text-violet-400" />
                  <span className="text-[8px] font-mono tracking-widest text-violet-400">
                    INTEL DATABASE CORROBORATION — {report.corroboration.count} MATCH{report.corroboration.count !== 1 ? 'ES' : ''}
                  </span>
                </div>
                {report.corroboration.items.length === 0 ? (
                  <p className="text-[9px] font-mono text-zinc-600">No corroborating intel records found.</p>
                ) : (
                  <div className="space-y-1">
                    {report.corroboration.items.slice(0, 5).map((ci, i) => (
                      <div key={i} className="rounded-sm border border-violet-900/40 bg-violet-950/20 px-2 py-1.5 space-y-0.5">
                        <div className="text-[9px] font-mono text-zinc-300">{ci.title}</div>
                        <div className="flex items-center gap-2 text-[8px] font-mono text-zinc-600">
                          <span className="text-violet-400">{ci.theater}</span>
                          <span>·</span>
                          <span className="text-zinc-500">{ci.author ?? 'unknown'}</span>
                          <span>·</span>
                          <span>conf {ci.confidence}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* ORACLE threat context */}
              {report.relatedThreats.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle size={10} className="text-red-400" />
                    <span className="text-[8px] font-mono tracking-widest text-red-400">
                      ORACLE-9 RELATED THREATS
                    </span>
                  </div>
                  <div className="space-y-1">
                    {(report.relatedThreats ?? []).filter(t => t != null).map((t, i) => (
                      <div key={i} className="flex items-center gap-2 text-[9px] font-mono border border-red-900/30 rounded-sm px-2 py-1 bg-red-950/20">
                        <span className="text-red-400 shrink-0">▲</span>
                        <span className="text-zinc-300 flex-1">{t.label}</span>
                        <span className="text-amber-400 shrink-0">{t.probability != null ? (t.probability * 100).toFixed(1) : '?'}%</span>
                        <span className="text-zinc-600 shrink-0">[{t.domain}]</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Citations */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5">
                  <BookOpen size={10} className="text-zinc-500" />
                  <span className="text-[8px] font-mono tracking-widest text-zinc-500">
                    CITATIONS ({report.citations.length})
                  </span>
                </div>
                <div className="space-y-0.5">
                  {report.citations.map((c, i) => (
                    <div key={i} className="text-[9px] font-mono text-zinc-500 flex gap-1.5 leading-relaxed">
                      <span className="text-zinc-700 shrink-0">[{i + 1}]</span>
                      <span className="break-words">{c}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Source link */}
              {report.url && (
                <a
                  href={report.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-[9px] font-mono text-emerald-400 hover:text-emerald-300 border border-emerald-800/40 rounded-sm px-2 py-1 hover:bg-emerald-950/20 transition-colors"
                >
                  <ExternalLink size={9} />
                  Read primary source
                </a>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
