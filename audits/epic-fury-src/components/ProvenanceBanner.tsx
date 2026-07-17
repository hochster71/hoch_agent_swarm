'use client'

/**
 * PROVENANCE BANNER — tells the customer, on every single dashboard, whether what
 * they are looking at is the real world or the Epic Fury scenario.
 *
 * Mounted in app/dashboard/layout.tsx, so it is IMPOSSIBLE for a dashboard to render
 * without it. That is deliberate: a label you have to remember to add is a label that
 * eventually gets forgotten, and the one time it is forgotten is the time an analyst
 * mistakes a simulation for intelligence.
 *
 * SIMULATED is styled as loudly as LIVE. We are not hiding it — a good wargame is
 * worth paying for. What is not worth paying for is not knowing which one you bought.
 */

import { usePathname } from 'next/navigation'
import { getProvenance, type Provenance } from '@/lib/data-provenance'
import { Radio, FlaskConical, Layers, HelpCircle, Construction } from 'lucide-react'

const STYLE: Record<Provenance, { label: string; cls: string; Icon: typeof Radio }> = {
  LIVE: {
    label: 'LIVE DATA',
    cls: 'border-emerald-800/60 bg-emerald-950/40 text-emerald-300',
    Icon: Radio,
  },
  SIMULATED: {
    label: 'SIMULATION — NOT REAL-WORLD INTELLIGENCE',
    cls: 'border-amber-700/60 bg-amber-950/40 text-amber-300',
    Icon: FlaskConical,
  },
  MIXED: {
    label: 'MIXED — LIVE DATA + SIMULATION',
    cls: 'border-sky-800/60 bg-sky-950/40 text-sky-300',
    Icon: Layers,
  },
  PLACEHOLDER: {
    label: 'NOT BUILT YET — NO DATA BEHIND THIS VIEW',
    cls: 'border-zinc-700 bg-zinc-900/60 text-zinc-400',
    Icon: Construction,
  },
  UNKNOWN: {
    label: 'UNVERIFIED — SOURCE NOT DECLARED',
    cls: 'border-zinc-700 bg-zinc-900/60 text-zinc-400',
    Icon: HelpCircle,
  },
}

export default function ProvenanceBanner() {
  const pathname = usePathname()
  const { provenance, note } = getProvenance(pathname)
  const { label, cls, Icon } = STYLE[provenance]

  return (
    <div
      role="status"
      aria-live="polite"
      data-provenance={provenance}
      className={`flex items-start gap-2.5 border-b px-4 py-2 ${cls}`}
    >
      <Icon size={13} className="mt-0.5 shrink-0" aria-hidden />
      <p className="text-[10px] leading-relaxed tracking-[0.12em] uppercase">
        <span className="font-bold">{label}</span>
        <span className="mx-1.5 opacity-40">|</span>
        <span className="normal-case tracking-normal opacity-90">{note}</span>
      </p>
    </div>
  )
}
