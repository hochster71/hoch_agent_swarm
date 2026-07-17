import DebatePanel from '@/components/DebatePanel'
import type { Metadata } from 'next'
import { Brain } from 'lucide-react'

export const revalidate = 0

export const metadata: Metadata = {
  title: 'Neural Truth Autonomy — EPIC FURY 2026',
  description:
    'Layer 2 Neural Truth Autonomy Core: 5-agent multi-agent debate audit log — ' +
    'Researcher, Skeptic, Verifier, US-Impact Analyst, Moderator.',
}

export default function DebatePage() {
  return (
    <div className="space-y-5 max-w-screen-lg">
      {/* Page header */}
      <div className="tac-card tac-card-critical p-4">
        <div className="flex items-start gap-3">
          <Brain size={15} className="text-purple-400 animate-pulse shrink-0 mt-0.5" />
          <div>
            <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
              Platform Governor — Layer 2 — Neural Truth Autonomy Core
            </p>
            <p className="text-sm font-bold tracking-widest text-purple-300 uppercase">
              5-Agent Multi-Agent Debate Audit
            </p>
            <p className="text-[10px] text-zinc-500 mt-1 tracking-wide">
              Every intel claim passes a structured debate before reaching VERIFIED status.{' '}
              Researcher ⟷ Skeptic ⟷ Verifier ⟷ US-Impact Analyst — moderated to consensus ≥ 7.5/10.
              All sessions persisted with full provenance.
            </p>
          </div>
        </div>
      </div>

      {/* Full debate panel */}
      <DebatePanel />
    </div>
  )
}
