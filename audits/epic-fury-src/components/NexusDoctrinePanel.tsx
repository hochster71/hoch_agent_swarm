import { Medal, Radar, Shield, Waypoints } from 'lucide-react'

interface NexusDoctrinePanelProps {
  conflictDay: number
}

const DOCTRINE_LINES = [
  {
    title: 'Fleet Watchstanding Discipline',
    detail: '31 years of Naval service translated into repeatable decision rhythm, concise command language, and operator accountability.',
    icon: Medal,
    color: 'text-emerald-300',
  },
  {
    title: 'Integrated Missile Defense Lens',
    detail: '7 years of BMD expertise fused into threat triage, interceptor prioritization, and probability-driven warning posture.',
    icon: Shield,
    color: 'text-cyan-300',
  },
  {
    title: 'Joint Information Control',
    detail: 'Cross-domain narrative control with transparent sourcing, confidence signaling, and adversary disinformation resistance.',
    icon: Radar,
    color: 'text-amber-300',
  },
  {
    title: 'JADC2 Decision Fabric',
    detail: 'Sensor-to-shooter alignment modeled for citizen clarity: detect, orient, decide, and communicate with traceable evidence.',
    icon: Waypoints,
    color: 'text-rose-300',
  },
]

export function NexusDoctrinePanel({ conflictDay }: NexusDoctrinePanelProps) {
  return (
    <section className="tac-card border border-cyan-900/60 bg-cyan-950/10 p-4">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="tac-section-header mb-0 text-cyan-300">Nexus Doctrine Brief</h2>
        <span className="text-[9px] tracking-[0.2em] uppercase text-cyan-500">Day {conflictDay}</span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {DOCTRINE_LINES.map((item) => (
          <div key={item.title} className="rounded border border-zinc-800 bg-zinc-950/55 px-3 py-2.5">
            <div className="flex items-center gap-1.5 mb-1">
              <item.icon size={12} className={item.color} />
              <p className={`text-[10px] tracking-[0.18em] uppercase font-semibold ${item.color}`}>{item.title}</p>
            </div>
            <p className="text-[11px] leading-relaxed text-zinc-400">{item.detail}</p>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded border border-zinc-800/80 bg-zinc-900/35 px-3 py-2">
        <p className="text-[9px] tracking-[0.15em] uppercase text-zinc-500">Professional Lineage</p>
        <p className="text-[11px] text-zinc-300 mt-1">
          E-1 to E-9 Master Chief Operations Specialist to LDO Surface Line Operations 6120.
        </p>
      </div>
    </section>
  )
}
