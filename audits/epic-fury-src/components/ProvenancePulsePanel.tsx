import { CheckCircle2, ShieldCheck, ShieldX, Telescope } from 'lucide-react'
import type { Intel } from '@/lib/types'

interface ProvenancePulsePanelProps {
  recentIntel: Intel[]
}

function pct(value: number, total: number): number {
  if (total <= 0) return 0
  return Math.round((value / total) * 100)
}

export function ProvenancePulsePanel({ recentIntel }: ProvenancePulsePanelProps) {
  const total = recentIntel.length
  const verified = recentIntel.filter((item) => item.verified).length
  const avgConfidence = total > 0
    ? Math.round(recentIntel.reduce((acc, item) => acc + (item.confidence ?? 0), 0) / total)
    : 0
  const uniqueSources = new Set(recentIntel.map((item) => item.source_name ?? 'Unknown')).size

  return (
    <section className="tac-card border border-emerald-900/60 bg-emerald-950/10 p-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="tac-section-header mb-0">Provenance Pulse</h2>
        <span className="inline-flex items-center gap-1 text-[9px] tracking-widest uppercase text-emerald-400">
          <Telescope size={11} />
          Open Intel Trust
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        <div className="rounded border border-zinc-800 bg-zinc-950/55 p-2">
          <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Reports</p>
          <p className="text-sm font-bold text-zinc-200 tabular-nums">{total}</p>
        </div>
        <div className="rounded border border-zinc-800 bg-zinc-950/55 p-2">
          <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Verified</p>
          <p className="text-sm font-bold text-emerald-400 tabular-nums">{verified} ({pct(verified, total)}%)</p>
        </div>
        <div className="rounded border border-zinc-800 bg-zinc-950/55 p-2">
          <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Avg Confidence</p>
          <p className="text-sm font-bold text-cyan-300 tabular-nums">{avgConfidence}%</p>
        </div>
        <div className="rounded border border-zinc-800 bg-zinc-950/55 p-2">
          <p className="text-[8px] tracking-widest text-zinc-600 uppercase">Sources</p>
          <p className="text-sm font-bold text-amber-300 tabular-nums">{uniqueSources}</p>
        </div>
      </div>

      <div className="space-y-1.5">
        {recentIntel.slice(0, 5).map((item) => (
          <div key={item.id} className="flex items-center gap-2 rounded border border-zinc-800/80 bg-zinc-950/45 px-2.5 py-1.5">
            {item.verified ? (
              <CheckCircle2 size={11} className="text-emerald-400 shrink-0" />
            ) : (
              <ShieldX size={11} className="text-amber-400 shrink-0" />
            )}
            <span className="text-[10px] text-zinc-300 truncate flex-1">{item.title}</span>
            <span className="text-[9px] text-zinc-500 hidden sm:inline">{item.source_name ?? 'Unknown'}</span>
            <span className="text-[9px] text-zinc-400 tabular-nums">{item.confidence ?? 0}%</span>
          </div>
        ))}
        {recentIntel.length === 0 && (
          <div className="rounded border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-[10px] text-zinc-500">
            No recent reports available for provenance scoring.
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-1.5 text-[9px] tracking-wide text-zinc-500">
        <ShieldCheck size={10} className="text-zinc-600" />
        Confidence and verification are shown together to expose evidence quality, not just headline velocity.
      </div>
    </section>
  )
}
