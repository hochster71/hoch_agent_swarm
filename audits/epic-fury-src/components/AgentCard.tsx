'use client'

import { useState } from 'react'
import type { Agent } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp, Clock, Target, Crosshair, BrainCircuit } from 'lucide-react'

const STATUS_STYLES: Record<Agent['status'], string> = {
  'ON STATION': 'border-emerald-700 text-emerald-400 bg-emerald-950/60',
  ENGAGED:      'border-amber-600  text-amber-400  bg-amber-950/60',
  MONITORING:   'border-zinc-600   text-zinc-400   bg-zinc-900/60',
  ALERT:        'border-red-600    text-red-400    bg-red-950/60',
}

const STATUS_DOT: Record<Agent['status'], string> = {
  'ON STATION': 'bg-emerald-400',
  ENGAGED:      'bg-amber-400 animate-pulse',
  MONITORING:   'bg-zinc-400',
  ALERT:        'bg-red-400 animate-ping',
}

const PRIORITY_STYLES: Record<Agent['priority'], string> = {
  CRITICAL: 'text-red-400    border-red-800    bg-red-950/50',
  HIGH:     'text-amber-400  border-amber-800  bg-amber-950/50',
  MEDIUM:   'text-sky-400    border-sky-800    bg-sky-950/50',
  LOW:      'text-zinc-500   border-zinc-800   bg-zinc-900/50',
}

const DOMAIN_COLOR: Record<Agent['domain'], string> = {
  ISR:        'text-cyan-500',
  Cyber:      'text-purple-400',
  SIGINT:     'text-yellow-500',
  OSINT:      'text-lime-500',
  Prediction: 'text-blue-400',
  Strike:     'text-red-400',
  Maritime:   'text-sky-400',
  IMINT:      'text-emerald-400',
  Fusion:     'text-white',
  EW:         'text-violet-400',
  STRATCOM:   'text-rose-400',
  IO:         'text-violet-400',
  Analytics:  'text-cyan-400',
}

function ConfidenceBar({ value }: { value: number }) {
  const color =
    value >= 80 ? 'bg-emerald-500' : value >= 55 ? 'bg-amber-500' : 'bg-red-600'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 rounded-full bg-zinc-800">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${value}%` }} />
      </div>
      <span className="text-[9px] text-zinc-500 w-7 text-right tracking-wider">{value}%</span>
    </div>
  )
}

export function AgentCard({ agent }: { agent: Agent }) {
  const [expanded, setExpanded] = useState(false)
  const isAlert = agent.status === 'ALERT'

  return (
    <article
      className={cn(
        'tac-card rounded-sm p-4 space-y-3 cursor-pointer select-none transition-colors',
        isAlert ? 'border-red-700 hover:border-red-500' : 'hover:border-emerald-700/60'
      )}
      onClick={() => setExpanded((v) => !v)}
    >
      {/* ── Header row ── */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-xs font-bold text-emerald-300 tracking-widest uppercase glow-green">
              {agent.name}
            </p>
            <span className={cn('text-[9px] font-bold tracking-widest uppercase', DOMAIN_COLOR[agent.domain])}>
              [{agent.domain}]
            </span>
          </div>
          <p className="text-[10px] text-zinc-500 tracking-wider mt-0.5">{agent.role}</p>
        </div>

        {/* Status + Priority */}
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={cn('status-badge border text-[9px]', STATUS_STYLES[agent.status])}>
            <span className={cn('inline-block w-1.5 h-1.5 rounded-full', STATUS_DOT[agent.status])} />
            {agent.status}
          </span>
          <span className={cn('text-[8px] px-1.5 py-0.5 border rounded-sm tracking-widest', PRIORITY_STYLES[agent.priority])}>
            PRI: {agent.priority}
          </span>
        </div>
      </div>

      {/* ── Confidence bar ── */}
      <div>
        <p className="text-[8px] text-zinc-600 tracking-widest mb-1">SIGNAL CONFIDENCE</p>
        <ConfidenceBar value={agent.confidence} />
      </div>

      {/* ── Tasking ── */}
      <div className="flex items-start gap-1.5">
        <Target size={9} className="text-zinc-600 shrink-0 mt-0.5" />
        <p className="text-[10px] text-zinc-400 leading-relaxed">{agent.tasking}</p>
      </div>

      {/* ── Footer: last update + expand toggle ── */}
      <div className="flex items-center justify-between pt-1">
        <p className="text-[9px] text-zinc-600 tracking-widest">
          <Clock size={8} className="inline mr-1" />
          {agent.lastUpdate}
        </p>
        <div className="flex items-center gap-1 text-[9px] text-zinc-600 tracking-widest">
          {expanded ? <ChevronUp size={9} /> : <ChevronDown size={9} />}
          {expanded ? 'COLLAPSE' : 'EXPAND LOG'}
        </div>
      </div>

      {/* ── Expanded panel ── */}
      {expanded && (
        <div className="border-t border-zinc-800 pt-3 space-y-3">
          {/* Threat focus */}
          <div className="flex items-start gap-1.5">
            <Crosshair size={9} className="text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-[8px] text-zinc-600 tracking-widest mb-0.5">THREAT FOCUS</p>
              <p className="text-[10px] text-red-300/80">{agent.threat_focus}</p>
            </div>
          </div>

          {/* Reasoning quote */}
          <div className="flex items-start gap-1.5">
            <BrainCircuit size={9} className="text-emerald-700 shrink-0 mt-0.5" />
            <div>
              <p className="text-[8px] text-zinc-600 tracking-widest mb-0.5">ASSESSMENT</p>
              <blockquote className="pl-2 border-l-2 border-emerald-800 text-[10px] text-zinc-400 italic leading-relaxed">
                &ldquo;{agent.quote}&rdquo;
              </blockquote>
            </div>
          </div>

          {/* Activity log */}
          <div>
            <p className="text-[8px] text-zinc-600 tracking-widest mb-1.5">ACTIVITY LOG</p>
            <ul className="space-y-1.5">
              {agent.actions.map((a, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-[8px] text-zinc-600 tracking-wider shrink-0 w-14">{a.time}</span>
                  <span className="text-[10px] text-zinc-500 leading-snug">{a.entry}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </article>
  )
}
