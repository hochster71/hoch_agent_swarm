'use client'

/**
 * SynthesisPanel — NEXUS Commander's Intelligence Assessment
 *
 * Displays the output of Governor Layer 10: synthesised threat level,
 * headline, executive summary, key threats, developments, recommended
 * actions, and foresight signals.
 *
 * Props:
 *   compact — renders a 4-metric strip + latest headline for dashboard use
 */

import { useState } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import { Brain, AlertTriangle, Shield, ChevronRight, RefreshCw, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NexusAssessment, SynthesisStats, ThreatLevel } from '@/lib/synthesis-engine'

// ── Colour maps ──────────────────────────────────────────────────────────────

const LEVEL_COLOR: Record<ThreatLevel, string> = {
  CRITICAL: 'text-red-400 border-red-700 bg-red-950/30',
  HIGH:     'text-orange-400 border-orange-700 bg-orange-950/30',
  ELEVATED: 'text-amber-400 border-amber-700 bg-amber-950/30',
  MODERATE: 'text-yellow-400 border-yellow-700 bg-yellow-950/30',
  LOW:      'text-emerald-400 border-emerald-700 bg-emerald-950/30',
}

const LEVEL_BADGE: Record<ThreatLevel, string> = {
  CRITICAL: 'bg-red-900/60 text-red-300 border border-red-700',
  HIGH:     'bg-orange-900/60 text-orange-300 border border-orange-700',
  ELEVATED: 'bg-amber-900/60 text-amber-300 border border-amber-700',
  MODERATE: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700',
  LOW:      'bg-emerald-900/60 text-emerald-300 border border-emerald-700',
}

const SEV_DOT: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-500',
  MODERATE: 'bg-yellow-500',
  LOW:      'bg-blue-500',
}

const SIG_DOT: Record<string, string> = {
  HIGH:   'bg-red-400',
  MEDIUM: 'bg-amber-400',
  LOW:    'bg-zinc-500',
}

const PRI_COLOR: Record<number, string> = {
  1: 'text-red-400',
  2: 'text-amber-400',
  3: 'text-blue-400',
}

// ── API response types ────────────────────────────────────────────────────────

interface SynthesisResponse {
  stats?:       SynthesisStats
  assessment?:  NexusAssessment
  assessments?: NexusAssessment[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60)  return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`
}

// ── Compact mode ─────────────────────────────────────────────────────────────

function CompactPanel({ data }: { data: SynthesisResponse | null }) {
  const stats      = data?.stats
  const assessment = data?.assessments?.[0] ?? data?.assessment

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={13} className="text-violet-400" />
          <span className="text-[11px] font-semibold tracking-widest text-zinc-300 uppercase">
            NEXUS Synthesis
          </span>
        </div>
        {stats && (
          <span className="text-[9px] text-zinc-600 uppercase tracking-widest">
            {stats.totalAssessments} briefs · {timeAgo(stats.lastAssessmentAt)}
          </span>
        )}
      </div>

      {/* Threat level + headline */}
      {assessment ? (
        <div className={cn('rounded-md border px-3 py-2', LEVEL_COLOR[assessment.threatLevel])}>
          <div className="flex items-center justify-between gap-2">
            <span className={cn('text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 rounded', LEVEL_BADGE[assessment.threatLevel])}>
              {assessment.threatLevel}
            </span>
            <span className="text-[9px] text-zinc-500">Day {assessment.conflictDay}</span>
          </div>
          <p className="text-[11px] font-medium mt-1.5 leading-tight">{assessment.headline}</p>
        </div>
      ) : (
        <div className="rounded-md border border-zinc-700 px-3 py-2 text-[10px] text-zinc-500">
          No assessment yet — trigger a heartbeat to generate
        </div>
      )}

      {/* 4-metric row */}
      {stats && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Briefs',    v: stats.totalAssessments },
            { label: 'Critical',  v: stats.recentByThreatLevel.CRITICAL },
            { label: 'High',      v: stats.recentByThreatLevel.HIGH },
            { label: 'Conf',      v: `${Math.round((stats.avgConfidence ?? 0) * 100)}%` },
          ].map(({ label, v }) => (
            <div key={label} className="text-center">
              <p className="text-[14px] font-bold text-zinc-200">{v}</p>
              <p className="text-[8px] text-zinc-600 uppercase tracking-widest">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Recent key threats (up to 2) */}
      {assessment?.keyThreats?.slice(0, 2).map((t, i) => (
        <div key={i} className="flex items-start gap-2">
          <span className={cn('mt-[5px] h-1.5 w-1.5 rounded-full flex-shrink-0', SEV_DOT[t.severity] ?? 'bg-zinc-500')} />
          <span className="text-[10px] text-zinc-400 leading-snug">{t.label} — {t.detail}</span>
        </div>
      ))}
    </div>
  )
}

// ── Full mode ─────────────────────────────────────────────────────────────────

function FullPanel({ data, loading }: { data: SynthesisResponse | null; loading: boolean }) {
  const stats       = data?.stats
  const assessments = data?.assessments ?? []
  const latest      = assessments[0]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-zinc-600 text-sm">
        <RefreshCw size={14} className="animate-spin mr-2" /> Loading NEXUS assessments…
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Stats header */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total Briefs',     v: stats.totalAssessments,                    c: 'text-violet-400' },
            { label: 'Threat Level',     v: stats.currentThreatLevel,                  c: LEVEL_COLOR[stats.currentThreatLevel]?.split(' ')[0] ?? 'text-zinc-300' },
            { label: 'Avg Confidence',   v: `${Math.round((stats.avgConfidence ?? 0) * 100)}%`, c: 'text-emerald-400' },
            { label: 'Last Brief',       v: timeAgo(stats.lastAssessmentAt),           c: 'text-zinc-400' },
          ].map(({ label, v, c }) => (
            <div key={label} className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3 text-center">
              <p className={cn('text-lg font-bold', c)}>{v}</p>
              <p className="text-[9px] text-zinc-600 uppercase tracking-widest mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Latest full assessment */}
      {latest && (
        <div className={cn('rounded-xl border p-4 space-y-3', LEVEL_COLOR[latest.threatLevel])}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain size={14} />
              <span className="text-[11px] font-bold tracking-widest uppercase">NEXUS Intelligence Brief</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={cn('text-[9px] font-bold px-2 py-0.5 rounded', LEVEL_BADGE[latest.threatLevel])}>
                {latest.threatLevel}
              </span>
              <span className="text-[9px] text-zinc-500">Day {latest.conflictDay} · {timeAgo(latest.createdAt)}</span>
            </div>
          </div>

          <p className="text-sm font-semibold leading-snug">{latest.headline}</p>
          <p className="text-[11px] text-zinc-300 leading-relaxed">{latest.executiveSummary}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Key Threats */}
            {latest.keyThreats?.length > 0 && (
              <div>
                <p className="text-[9px] text-zinc-600 uppercase tracking-widest mb-1.5">Key Threats</p>
                <div className="space-y-1.5">
                  {latest.keyThreats.map((t, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className={cn('mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0', SEV_DOT[t.severity] ?? 'bg-zinc-500')} />
                      <div>
                        <p className="text-[10px] font-medium text-zinc-200">{t.label}</p>
                        <p className="text-[9px] text-zinc-500">{t.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Key Developments */}
            {latest.keyDevelopments?.length > 0 && (
              <div>
                <p className="text-[9px] text-zinc-600 uppercase tracking-widest mb-1.5">Key Developments</p>
                <div className="space-y-1.5">
                  {latest.keyDevelopments.map((d, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className={cn('mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0', SIG_DOT[d.significance] ?? 'bg-zinc-500')} />
                      <div>
                        <p className="text-[10px] font-medium text-zinc-200">{d.domain}</p>
                        <p className="text-[9px] text-zinc-500">{d.headline}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Recommended Actions */}
          {latest.recommendedActions?.length > 0 && (
            <div>
              <p className="text-[9px] text-zinc-600 uppercase tracking-widest mb-1.5">Recommended Actions</p>
              <div className="space-y-1.5">
                {latest.recommendedActions.map((a, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className={cn('text-[10px] font-bold', PRI_COLOR[a.priority] ?? 'text-zinc-400')}>
                      P{a.priority}
                    </span>
                    <div>
                      <p className="text-[10px] font-medium text-zinc-200">{a.action}</p>
                      <p className="text-[9px] text-zinc-500">{a.rationale}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Foresight signals */}
          {latest.foresightSignals?.length > 0 && (
            <div>
              <p className="text-[9px] text-zinc-600 uppercase tracking-widest mb-1.5">
                <TrendingUp size={9} className="inline mr-1" />Foresight Signals
              </p>
              <div className="space-y-1">
                {latest.foresightSignals.map((s, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-[9px] text-zinc-500 uppercase">[{s.horizon}]</span>
                    <span className="text-[10px] text-zinc-300">{s.prediction}</span>
                    <span className="ml-auto text-[9px] text-violet-400">{Math.round(s.confidence * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-current/20 pt-2">
            <span className="text-[8px] text-zinc-600">
              {latest.modelUsed} · {latest.layersCompleted} layers · conf {Math.round((latest.confidenceScore ?? 0) * 100)}%
            </span>
            <span className="text-[8px] text-zinc-600">{latest.urgentEscalations} urgent escalations</span>
          </div>
        </div>
      )}

      {/* Assessment history */}
      {assessments.length > 1 && (
        <div className="space-y-1">
          <p className="text-[9px] text-zinc-600 uppercase tracking-widest">Assessment History</p>
          {assessments.slice(1).map((a) => (
            <div key={a.id} className="flex items-center gap-3 bg-zinc-900/40 border border-zinc-800 rounded-md px-3 py-2">
              <span className={cn('text-[9px] font-bold px-1.5 py-0.5 rounded', LEVEL_BADGE[a.threatLevel])}>
                {a.threatLevel}
              </span>
              <span className="text-[10px] text-zinc-300 flex-1 truncate">{a.headline}</span>
              <span className="text-[9px] text-zinc-600 flex-shrink-0">Day {a.conflictDay} · {timeAgo(a.createdAt)}</span>
              <ChevronRight size={10} className="text-zinc-700 flex-shrink-0" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!latest && !loading && (
        <div className="rounded-xl border border-zinc-800 p-6 text-center">
          <Brain size={24} className="text-zinc-700 mx-auto mb-2" />
          <p className="text-zinc-500 text-sm">No NEXUS assessments yet</p>
          <p className="text-zinc-600 text-xs mt-1">
            Trigger a governor heartbeat to generate the first Commander&apos;s Brief
          </p>
          <div className="mt-3 flex items-center justify-center gap-1 text-[9px] text-zinc-600">
            <AlertTriangle size={9} /> Requires OPENAI_API_KEY for AI synthesis
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function SynthesisPanel({ compact = false }: { compact?: boolean }) {
  const [data, setData]       = useState<SynthesisResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await fetch('/api/intel/synthesis?limit=6', { cache: 'no-store' })
      if (res.ok) setData(await res.json() as SynthesisResponse)
    } catch { /* non-fatal */ } finally {
      setLoading(false)
    }
  }

  useSmartPoll(load, 60_000)

  if (compact) return <CompactPanel data={data} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={15} className="text-violet-400" />
          <h2 className="text-sm font-semibold text-zinc-200 tracking-wide uppercase">
            NEXUS — Commander&apos;s Intelligence Assessment
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <Shield size={11} className="text-zinc-600" />
          <span className="text-[9px] text-zinc-600 uppercase tracking-widest">Layer 10 · Synthesis</span>
        </div>
      </div>
      <FullPanel data={data} loading={loading} />
    </div>
  )
}
