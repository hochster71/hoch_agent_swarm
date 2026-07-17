'use client'

/**
 * components/DebatePanel.tsx — Neural Truth Autonomy Core Panel
 *
 * Visualises the 5-agent multi-agent debate sessions that power Layer 2
 * of the EPIC FURY 2026 Platform Governor.
 *
 * Compact mode: stats strip used on main command dashboard.
 * Full mode:    recent debate sessions with agent round breakdowns.
 */

import { useState, useCallback } from 'react'
import { useSmartPoll } from '@/hooks/useSmartPoll'
import {
  Brain,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Users,
  ShieldCheck,
  HelpCircle,
  Zap,
  MessageSquare,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ---------------------------------------------------------------------------
// Types (mirrors debate-engine.ts — kept local to avoid server import)
// ---------------------------------------------------------------------------

type AgentRole = 'RESEARCHER' | 'SKEPTIC' | 'VERIFIER' | 'US_IMPACT_ANALYST' | 'MODERATOR'
type AgentPosition = 'SUPPORTS' | 'CHALLENGES' | 'NEUTRAL' | 'INCONCLUSIVE' | 'CONSENSUS'
type Verdict = 'VERIFIED' | 'CONTRADICTED' | 'PENDING' | 'UNVERIFIABLE' | 'ESCALATED'

interface DebateRound {
  round_number:    number
  agent_role:      AgentRole
  position:        AgentPosition
  reasoning:       string
  confidence:      number
  rebuttal_target: string | null
}

interface DebateSession {
  id:               string
  claim_text:       string
  final_verdict:    Verdict
  consensus_score:  number | null
  rounds_completed: number
  us_impact_score:  number | null
  duration_ms:      number | null
  created_at:       string
  rounds?:          DebateRound[]
}

interface DebateStats {
  totalSessions:        number
  verifiedByDebate:     number
  contradictedByDebate: number
  avgConsensusScore:    number
  avgRoundsToConsensus: number
  avgDurationMs:        number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const VERDICT_CONFIG: Record<Verdict, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  VERIFIED:     { label: 'VERIFIED',     color: 'text-emerald-400', bg: 'bg-emerald-950/30 border-emerald-800', icon: CheckCircle2 },
  CONTRADICTED: { label: 'CONTRADICTED', color: 'text-red-400',     bg: 'bg-red-950/30 border-red-800',        icon: XCircle },
  PENDING:      { label: 'PENDING',      color: 'text-amber-400',   bg: 'bg-amber-950/20 border-amber-800',    icon: Clock },
  UNVERIFIABLE: { label: 'UNVERIFIABLE', color: 'text-zinc-400',    bg: 'bg-zinc-900/30 border-zinc-700',      icon: HelpCircle },
  ESCALATED:    { label: 'ESCALATED',    color: 'text-purple-400',  bg: 'bg-purple-950/20 border-purple-800',  icon: AlertTriangle },
}

const AGENT_CONFIG: Record<AgentRole, { label: string; color: string; abbr: string }> = {
  RESEARCHER:       { label: 'Researcher',      color: 'text-blue-400',    abbr: 'RES' },
  SKEPTIC:          { label: 'Skeptic',          color: 'text-amber-400',   abbr: 'SKP' },
  VERIFIER:         { label: 'Verifier',         color: 'text-emerald-400', abbr: 'VER' },
  US_IMPACT_ANALYST: { label: 'US Impact',       color: 'text-red-400',     abbr: 'USI' },
  MODERATOR:        { label: 'Moderator',        color: 'text-purple-400',  abbr: 'MOD' },
}

const POSITION_COLOR: Record<AgentPosition, string> = {
  SUPPORTS:    'text-emerald-400',
  CHALLENGES:  'text-red-400',
  NEUTRAL:     'text-zinc-400',
  INCONCLUSIVE:'text-amber-400',
  CONSENSUS:   'text-purple-400',
}

function elapsed(ms: number | null): string {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`
  return `${Math.round(diff / 3_600_000)}h ago`
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConsensusBar({ score }: { score: number | null }) {
  const s = score ?? 0
  const color = s >= 7.5 ? 'bg-emerald-500' : s >= 4 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${(s / 10) * 100}%` }} />
      </div>
      <span className="text-[10px] tabular-nums text-zinc-400 w-6 text-right">{s.toFixed(1)}</span>
    </div>
  )
}

function RoundCard({ round }: { round: DebateRound }) {
  const agent = AGENT_CONFIG[round.agent_role]
  return (
    <div className="flex gap-2 py-1.5 border-b border-zinc-900 last:border-0">
      <div className={cn('text-[9px] font-bold tracking-widest w-9 shrink-0 pt-0.5', agent.color)}>
        {agent.abbr}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={cn('text-[9px] font-bold tracking-wide uppercase', POSITION_COLOR[round.position])}>
            {round.position}
          </span>
          {round.rebuttal_target && (
            <span className="text-[9px] text-zinc-600">↩ {round.rebuttal_target}</span>
          )}
          <span className="text-[9px] text-zinc-600 ml-auto">{round.confidence.toFixed(1)}/10</span>
        </div>
        <p className="text-[10px] text-zinc-400 leading-relaxed line-clamp-2">{round.reasoning}</p>
      </div>
    </div>
  )
}

function SessionCard({ session }: { session: DebateSession }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = VERDICT_CONFIG[session.final_verdict]
  const Icon = cfg.icon

  return (
    <div className={cn('border rounded-sm p-3 space-y-2', cfg.bg)}>
      {/* Header */}
      <div className="flex items-start gap-2">
        <Icon size={11} className={cn('shrink-0 mt-0.5', cfg.color)} />
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-zinc-300 leading-snug line-clamp-2">{session.claim_text}</p>
        </div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="shrink-0 text-zinc-600 hover:text-zinc-400 mt-0.5"
          aria-label={expanded ? 'Collapse' : 'Expand'}
        >
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>
      </div>

      {/* Meta strip */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className={cn('text-[9px] font-bold tracking-widest uppercase', cfg.color)}>
          {cfg.label}
        </span>
        <span className="text-[9px] text-zinc-600">{session.rounds_completed} rounds</span>
        <span className="text-[9px] text-zinc-600">{elapsed(session.duration_ms)}</span>
        {session.us_impact_score != null && (
          <span className="text-[9px] text-red-400">US-Impact {session.us_impact_score.toFixed(1)}/10</span>
        )}
        <span className="text-[9px] text-zinc-700 ml-auto">{timeAgo(session.created_at)}</span>
      </div>

      {/* Consensus bar */}
      <ConsensusBar score={session.consensus_score} />

      {/* Expanded rounds */}
      {expanded && session.rounds && session.rounds.length > 0 && (
        <div className="mt-2 pt-2 border-t border-zinc-800 space-y-0">
          <p className="text-[9px] tracking-widest text-zinc-600 uppercase mb-1">
            Debate Transcript — {session.rounds.length} agent actions
          </p>
          {session.rounds.map((r, i) => (
            <RoundCard key={i} round={r} />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stats strip (compact mode)
// ---------------------------------------------------------------------------

function StatsStrip({ stats }: { stats: DebateStats }) {
  const verifyRate = stats.totalSessions > 0
    ? Math.round((stats.verifiedByDebate / stats.totalSessions) * 100)
    : 0

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      {[
        { label: 'Total Debates',    value: stats.totalSessions,            color: 'text-zinc-300' },
        { label: 'Verified',         value: `${stats.verifiedByDebate} (${verifyRate}%)`, color: 'text-emerald-400' },
        { label: 'Avg Consensus',    value: `${stats.avgConsensusScore}/10`,  color: 'text-blue-400' },
        { label: 'Avg Rounds',       value: stats.avgRoundsToConsensus,    color: 'text-amber-400' },
      ].map(({ label, value, color }) => (
        <div key={label} className="tac-card p-2.5 space-y-1">
          <p className="text-[9px] tracking-widest text-zinc-600 uppercase">{label}</p>
          <p className={cn('text-sm font-bold tabular-nums', color)}>{value}</p>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface DebatePanelProps {
  compact?: boolean
}

export default function DebatePanel({ compact = false }: DebatePanelProps) {
  const [stats, setStats]         = useState<DebateStats | null>(null)
  const [sessions, setSessions]   = useState<DebateSession[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    try {
      const limit = compact ? 3 : 10
      const res = await fetch(`/api/intel/debate?limit=${limit}`, { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json() as { stats: DebateStats; sessions: DebateSession[] }
      setStats(data.stats)
      setSessions(data.sessions)
      setLastRefresh(new Date())
      setError(null)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }, [compact])

  useSmartPoll(refresh, compact ? 30_000 : 60_000)

  // ── Compact strip for main command dashboard ──────────────────────────────
  if (compact) {
    return (
      <div className="tac-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain size={13} className="text-purple-400" />
            <p className="text-[10px] tracking-widest text-zinc-400 uppercase font-bold">
              Neural Truth Autonomy — Layer 2 Debate Core
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
            <span className="text-[9px] text-zinc-600 uppercase tracking-widest">5-Agent Active</span>
          </div>
        </div>

        {loading && (
          <div className="h-10 flex items-center justify-center">
            <p className="text-[10px] text-zinc-600 animate-pulse">Loading debate telemetry…</p>
          </div>
        )}

        {error && (
          <p className="text-[10px] text-red-500">Debate telemetry unavailable — {error}</p>
        )}

        {!loading && !error && stats && (
          <>
            <StatsStrip stats={stats} />
            {sessions.length > 0 && (
              <div className="space-y-1.5">
                {sessions.slice(0, 2).map(s => {
                  const cfg = VERDICT_CONFIG[s.final_verdict]
                  const Icon = cfg.icon
                  return (
                    <div key={s.id} className="flex items-center gap-2 py-1 border-b border-zinc-900">
                      <Icon size={10} className={cfg.color} />
                      <p className="text-[10px] text-zinc-400 flex-1 truncate">{s.claim_text}</p>
                      <span className={cn('text-[9px] font-bold tracking-wide shrink-0', cfg.color)}>
                        {cfg.label}
                      </span>
                      <span className="text-[9px] text-zinc-700 shrink-0 w-14 text-right">
                        {s.consensus_score?.toFixed(1) ?? '—'}/10
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </>
        )}

        {lastRefresh && (
          <p className="text-[9px] text-zinc-700">
            Updated {lastRefresh.toLocaleTimeString()}
          </p>
        )}
      </div>
    )
  }

  // ── Full panel ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="tac-card p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Brain size={16} className="text-purple-400" />
            <div>
              <p className="text-[9px] tracking-[0.3em] text-zinc-500 uppercase">Platform Governor — Layer 2</p>
              <h2 className="text-sm font-bold text-purple-300 tracking-widest uppercase">
                Neural Truth Autonomy Core
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
              <span className="text-[9px] text-zinc-500 tracking-widest uppercase">5-Agent Debate Active</span>
            </div>
            <button
              onClick={refresh}
              className="text-[9px] tracking-widest text-zinc-600 hover:text-zinc-400 uppercase px-2 py-1 border border-zinc-800 hover:border-zinc-600 rounded-sm"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Agent roster */}
        <div className="grid grid-cols-5 gap-2 mb-4">
          {(Object.entries(AGENT_CONFIG) as [AgentRole, typeof AGENT_CONFIG[AgentRole]][]).map(([role, cfg]) => {
            const RoleIcon =
              role === 'MODERATOR' ? ShieldCheck :
              role === 'SKEPTIC'   ? AlertTriangle :
              role === 'VERIFIER'  ? CheckCircle2 :
              role === 'US_IMPACT_ANALYST' ? Users :
              MessageSquare
            return (
              <div key={role} className="tac-card p-2 space-y-1 text-center">
                <RoleIcon size={12} className={cn('mx-auto', cfg.color)} />
                <p className={cn('text-[9px] font-bold tracking-wider uppercase', cfg.color)}>
                  {cfg.abbr}
                </p>
                <p className="text-[8px] text-zinc-600 leading-tight">{cfg.label}</p>
              </div>
            )
          })}
        </div>

        {/* Protocol explanation */}
        <div className="grid grid-cols-3 gap-2 text-center">
          {[
            { step: 'R1', desc: 'Independent positions' },
            { step: 'R2', desc: 'Skeptic→Researcher rebuttal' },
            { step: 'R3+', desc: 'Consensus convergence' },
          ].map(({ step, desc }) => (
            <div key={step} className="border border-zinc-800 p-2 rounded-sm">
              <p className="text-[10px] font-bold text-purple-400 mb-0.5">{step}</p>
              <p className="text-[9px] text-zinc-600">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      {!loading && !error && stats && (
        <div className="tac-card p-4 space-y-3">
          <p className="text-[9px] tracking-widest text-zinc-500 uppercase">Debate Telemetry</p>
          <StatsStrip stats={stats} />
          <div className="grid grid-cols-2 gap-2">
            <div className="border border-zinc-800 p-2.5 rounded-sm">
              <p className="text-[9px] text-zinc-600 mb-1">Contradicted</p>
              <p className="text-lg font-bold text-red-400 tabular-nums">{stats.contradictedByDebate}</p>
            </div>
            <div className="border border-zinc-800 p-2.5 rounded-sm">
              <p className="text-[9px] text-zinc-600 mb-1">Avg Duration</p>
              <p className="text-lg font-bold text-zinc-300 tabular-nums">{elapsed(stats.avgDurationMs)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Loading / error states */}
      {loading && (
        <div className="tac-card p-8 flex items-center justify-center">
          <div className="text-center space-y-2">
            <Zap size={20} className="text-purple-500 animate-pulse mx-auto" />
            <p className="text-[10px] text-zinc-600 animate-pulse tracking-widest">
              Loading debate sessions…
            </p>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="tac-card p-4 border-red-900">
          <p className="text-[10px] text-red-400">Debate API offline — {error}</p>
          <p className="text-[10px] text-zinc-600 mt-1">
            Check <code className="text-zinc-400">/api/intel/debate</code> and Supabase connectivity.
          </p>
        </div>
      )}

      {/* Debate sessions */}
      {!loading && !error && sessions.length > 0 && (
        <div className="space-y-3">
          <p className="text-[9px] tracking-widest text-zinc-500 uppercase px-1">
            Recent Debate Sessions ({sessions.length})
          </p>
          {sessions.map(s => (
            <SessionCard key={s.id} session={s} />
          ))}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="tac-card p-6 text-center space-y-2">
          <Brain size={18} className="text-zinc-700 mx-auto" />
          <p className="text-[10px] text-zinc-600">No debate sessions yet.</p>
          <p className="text-[10px] text-zinc-700">
            Sessions are created automatically when intel claims are verified by Layer 2.
          </p>
        </div>
      )}

      {lastRefresh && (
        <p className="text-[9px] text-zinc-700 text-right">
          Last updated: {lastRefresh.toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
