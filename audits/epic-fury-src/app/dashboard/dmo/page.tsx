import { DmoCanvas, JicoPanel } from '@/components/DmoCanvas'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'
import { Map, AlertTriangle, Anchor, Layers, Radio, ShieldAlert, Target, Activity, Cpu } from 'lucide-react'
import { getConflictDay, toDTG } from '@/lib/conflict-day'
import { getWarStats } from '@/lib/war-stats'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0

const CONFLICT_DAY = getConflictDay()
const _ws = getWarStats(CONFLICT_DAY)

/**
 * /dashboard/dmo
 * Distributed Maritime Operations — Live AI Theater Intelligence // Hormuz Strait Theatre
 */
interface LiveDmoEvent {
  id: number
  event_id: string
  time_zulu: string
  type: string
  priority: string
  title: string
  body: string
  conflict_day: number
}

export default async function DmoPage() {
  let liveDmoEvents: LiveDmoEvent[] = []
  let intelFallback: { id: string; title: string; summary: string; confidence: number; source_url: string; source_name: string; created_at: string }[] = []
  try {
    const sb = await createServerClient()
    if (sb) {
      const [eventsRes, intelRes] = await Promise.all([
        sb.from('scenario_events')
          .select('*')
          .order('conflict_day', { ascending: false })
          .order('created_at', { ascending: false })
          .limit(15),
        sb.from('intel')
          .select('id, title, summary, confidence, source_url, source_name, created_at')
          .gte('confidence', 60)
          .order('created_at', { ascending: false })
          .limit(15),
      ])
      liveDmoEvents = (eventsRes.data ?? []) as LiveDmoEvent[]
      intelFallback = intelRes.data ?? []
    }
  } catch { /* non-fatal */ }

  return (
    <section className="space-y-5">
      {/* Live maritime / Hormuz theater intel feed */}
      <TheaterIntelFeed theater="Maritime" limit={10} compact />

      {/* ── Cinematic DMO Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(16,185,129,0.012) 2px, rgba(16,185,129,0.012) 4px)'}} />
          <div className="relative z-[3]">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Map size={26} className="text-emerald-400 drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-widest text-zinc-200 glow-green uppercase">
                  DMO Live — Hormuz Strait
                </h1>
                <p className="text-[9px] text-zinc-500 tracking-widest">
                  AS OF: {toDTG(CONFLICT_DAY)} · Day {CONFLICT_DAY} · DISTRIBUTED MARITIME OPERATIONS
                </p>
              </div>
              <div className="ml-auto on-air-badge inline-block bg-emerald-900/60 text-emerald-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-emerald-800/60 shrink-0">
                ● NAVCENT LIVE
              </div>
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" />
      </div>

      {/* Summary stat strip — DAY 27 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Combat Air Assets', value: '28', sub: 'F-35A×5 · F-22A×2 · B-21×1 · ISR×6+', accent: 'emerald' },
          { label: 'MCM ZB-Alpha', value: `${_ws.zbAlphaPct}%`, sub: `${CONFLICT_DAY - 24}+ VLCC transits D24–D${CONFLICT_DAY} — ZB-Alpha open`, accent: 'amber' },
          { label: 'IRGC Threat Level', value: 'ELEVATED', sub: 'Command consolidated D22; ceasefire talks D26–D27 (68% progress)', accent: 'amber' },
          { label: 'Straits Status', value: 'PARTIAL TRANSIT', sub: '7+ VLCCs transited ZB-Alpha under coalition escort; 78% cleared', accent: 'amber' },
        ].map(({ label, value, sub, accent }) => (
          <div
            key={label}
            className={`tac-card p-3 border-t-2 data-card-glow ${
              accent === 'emerald' ? 'border-t-emerald-600' :
              accent === 'amber'   ? 'border-t-amber-600' :
                                    'border-t-red-600'
            }`}
          >
            <p className="text-[9px] text-zinc-500 tracking-widest uppercase">{label}</p>
            <p className={`text-lg font-bold mt-0.5 ${
              accent === 'emerald' ? 'text-emerald-400' :
              accent === 'amber'   ? 'text-amber-400' :
                                    'text-red-400'
            }`}>{value}</p>
            <p className="text-[9px] text-zinc-600 mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {/* NTDS Legend + canvas */}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-[9px] text-zinc-500 tracking-widest">
          <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-full border border-emerald-400" /> Friendly Surface (⊙)</span>
          <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-full border border-emerald-400 opacity-60" style={{clipPath:'polygon(0 50%,100% 50%,100% 100%,0 100%)'}} /> Friendly Sub (⌓)</span>
          <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-full border border-emerald-400" /> Friendly Air (△ in ○)</span>
          <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 border border-red-500 rotate-45" /> Hostile Surface (◇)</span>
          <span className="flex items-center gap-1.5"><span className="inline-block w-2.5 h-2.5 border border-red-800 rotate-45" /> Hostile Mine (◇×)</span>
          <span className="flex items-center gap-1.5"><span className="inline-block w-2 h-2 border border-amber-400" /> Unknown (□)</span>
          <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-px bg-cyan-500" style={{marginTop:'1px'}} /> Link-16 data pulse</span>
        </div>
        <DmoCanvas />
      </div>

      {/* JICO / JADC2 environment */}
      <div className="tac-section-header">
        <Radio size={12} className="text-cyan-500 drop-shadow-[0_0_4px_rgba(6,182,212,0.4)]" />
        <span className="glow-blue">JICO / JADC2 Environment — Link-16 Network &amp; Kill Chain Status</span>
        <span className="ml-auto text-[9px] text-cyan-500 tracking-widest normal-case">NET-A JTIDS · E-2D NCS</span>
      </div>
      <JicoPanel />

      {/* JADC2 Kill Chain Tracker */}
      <div className="video-feed-frame tac-card p-4 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-red-500/60 font-bold tracking-[0.2em]">KILL CHAIN</span>
        </div>
        <div className="flex items-center gap-2 mb-4 relative z-[1]">
          <Target size={12} className="text-red-500 drop-shadow-[0_0_4px_rgba(239,68,68,0.4)]" />
          <p className="text-[9px] font-bold text-red-500 tracking-widest uppercase glow-red">JADC2 Kill Chain Tracker — Active Engagements Day {CONFLICT_DAY}</p>
          <span className="ml-auto text-[9px] text-zinc-600 tracking-widest normal-case">Sensor → Processor → Decider → Shooter</span>
        </div>
        <div className="space-y-3">
          {[
            {
              id: 'KC-01', target: 'FATEH-110 SRBM (Track T-221)', priority: 'CRITICAL',
              sensor: 'SBIRS / DSP-23', processor: 'NORTHCOM BMDS', decider: 'SECDEF AUTHORIZE',
              shooter: 'CG-55 SM-3 Block IIA', latency: '42s',
              phase: 'ENGAGE', phaseColor: 'text-red-500 animate-pulse',
              chainPct: 90,
            },
            {
              id: 'KC-02', target: 'SHAD-04/05 Shahed Swarm (4× UAS)', priority: 'HIGH',
              sensor: 'SENTRY-11 E-3G / LINK-16', processor: 'CAOC BLUE DAGGER', decider: 'CAOC AOC AUTO',
              shooter: 'VIPER-11/12 F-35A AIM-9X', latency: '18s',
              phase: 'KILL CONFIRM', phaseColor: 'text-emerald-400',
              chainPct: 100,
            },
            {
              id: 'KC-03', target: 'ZB-Alpha MCM Escort (7 VLCC transits D24–D27)', priority: 'HIGH',
              sensor: 'MCM-14 CHIEF / MH-53E Sonar', processor: 'CTF-52 MCM HQ', decider: 'CTF-54 CDR',
              shooter: 'MCM-14 CHIEF · MCM-11 GLADIATOR', latency: 'N/A',
              phase: 'MCM ESCORT', phaseColor: 'text-emerald-400',
              chainPct: 100,
            },
            {
              id: 'KC-04', target: 'BANDIT-γ/δ Su-25 (Ground Attack)', priority: 'HIGH',
              sensor: 'WEDGETAIL-1 E-7A', processor: 'CAOC INTEL CELL', decider: 'Strike Cell AUTO-ROE',
              shooter: 'RAPTOR-31/32 F-22A AIM-120D', latency: '24s',
              phase: 'TRACKING', phaseColor: 'text-amber-400',
              chainPct: 45,
            },
            {
              id: 'KC-05', target: 'IRGCN FAC Swarm (4× vessels)', priority: 'HIGH',
              sensor: 'MQ9-01 REAPER / HAWK-01 RQ-4B', processor: 'CTF-52 C2', decider: 'SAG CDR DDG-107',
              shooter: 'CG-55 SM-2MR / DDG-107 Mk-45 5"', latency: '3m40s',
              phase: 'WEAPONS FREE', phaseColor: 'text-red-400 animate-pulse',
              chainPct: 80,
            },
            {
              id: 'KC-06', target: 'IRGC HEU Enrichment Bunker (Fordow)', priority: 'STRATEGIC',
              sensor: 'RQ-4B HAWK-02 / NGA SAR', processor: 'DIA DNRO', decider: 'SECDEF / NSC',
              shooter: 'ANVIL-01 B-21 GBU-57B MOP', latency: '6h+ cycle',
              phase: 'BDA PENDING', phaseColor: 'text-zinc-400',
              chainPct: 100,
            },
          ].map(({ id, target, priority, sensor, processor, decider, shooter, latency, phase, phaseColor, chainPct }) => (
            <div key={id} className="border border-zinc-800 rounded-sm p-3 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-zinc-600 font-mono">{id}</span>
                    <span className={`text-[9px] font-bold tracking-widest ${
                      priority === 'CRITICAL' || priority === 'STRATEGIC' ? 'text-red-400' :
                      'text-amber-400'
                    }`}>{priority}</span>
                    <span className="text-[10px] font-bold text-zinc-200">{target}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[9px] text-zinc-600">S→S latency:</span>
                  <span className="text-[9px] font-bold text-cyan-400 font-mono">{latency}</span>
                  <span className={`text-[9px] font-bold tracking-widest border border-current px-1.5 py-0.5 rounded-sm ${phaseColor}`}>{phase}</span>
                </div>
              </div>
              {/* Kill chain flow */}
              <div className="grid grid-cols-4 gap-1 text-[8px]">
                {[
                  { icon: '◉', label: 'SENSOR', value: sensor, color: 'text-cyan-400' },
                  { icon: '⬡', label: 'C2 PROCESS', value: processor, color: 'text-violet-400' },
                  { icon: '◈', label: 'DECIDER', value: decider, color: 'text-amber-400' },
                  { icon: '⊕', label: 'SHOOTER', value: shooter, color: 'text-red-400' },
                ].map(({ icon, label, value, color }) => (
                  <div key={label} className="bg-zinc-900/60 rounded-sm px-2 py-1.5">
                    <div className={`font-bold tracking-widest ${color} mb-0.5`}>{icon} {label}</div>
                    <div className="text-zinc-400 leading-relaxed">{value}</div>
                  </div>
                ))}
              </div>
              {/* Progress bar */}
              <div className="h-1 bg-zinc-900 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all ${
                  chainPct === 100 ? 'bg-emerald-500' :
                  chainPct >= 70 ? 'bg-red-500 animate-pulse' :
                  chainPct >= 40 ? 'bg-amber-500' : 'bg-zinc-600'
                }`} style={{ width: `${chainPct}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sensor-to-Shooter Latency Dashboard */}
      <div className="tac-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={12} className="text-cyan-500" />
          <p className="text-[9px] font-bold text-cyan-500 tracking-widest uppercase">Sensor-to-Shooter Latency — JADC2 Performance Metrics Day {CONFLICT_DAY}</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { domain: 'BALLISTIC MISSILE', latency: '42s', mode: 'AUTO (BMDS)', trend: '↓18%', trendColor: 'text-emerald-400' },
            { domain: 'UAS SWARM',         latency: '18s', mode: 'AUTO (CAOC)', trend: '↓35%', trendColor: 'text-emerald-400' },
            { domain: 'SUBSURFACE',        latency: '6m12s', mode: 'MANUAL',   trend: '→ NORM', trendColor: 'text-zinc-400' },
            { domain: 'AIR (FIGHTER)',     latency: '24s',  mode: 'SEMI-AUTO', trend: '↓12%',  trendColor: 'text-emerald-400' },
            { domain: 'SURFACE (FAC)',     latency: '3m40s',mode: 'MANUAL',    trend: '↑8%',   trendColor: 'text-amber-400' },
            { domain: 'STRATEGIC STRIKE',  latency: '6h+',  mode: 'NSC APPRVD',trend: 'N/A',   trendColor: 'text-zinc-600' },
          ].map(({ domain, latency, mode, trend, trendColor }) => (
            <div key={domain} className="bg-zinc-900/50 border border-zinc-800 rounded-sm p-2 space-y-1">
              <div className="text-[8px] text-zinc-500 tracking-widest uppercase">{domain}</div>
              <div className="text-sm font-bold font-mono text-emerald-400">{latency}</div>
              <div className="text-[8px] text-zinc-600">{mode}</div>
              <div className={`text-[9px] font-bold ${trendColor}`}>{trend} vs D26</div>
            </div>
          ))}
        </div>
        <div className="mt-2 text-[8px] text-zinc-700">Source: CENTCOM J6 JADC2 Connectivity Report · Day {CONFLICT_DAY} · PGDR-1 Network</div>
      </div>

      {/* Two-column: Task Group Status + MCM Status */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

        {/* US Naval Task Group */}
        <div className="video-feed-frame tac-card p-4 space-y-3 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">CTF-50</span>
          </div>
          <div className="flex items-center gap-2 mb-1 relative z-[1]">
            <Anchor size={12} className="text-emerald-600 drop-shadow-[0_0_4px_rgba(16,185,129,0.4)]" />
            <p className="text-[9px] font-bold text-emerald-600 tracking-widest uppercase glow-green">US / Coalition Naval Task Group — Day {CONFLICT_DAY}</p>
          </div>
          <table className="w-full text-[9px]">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-600 tracking-widest uppercase">
                <th className="text-left pb-1.5 font-normal">Hull</th>
                <th className="text-left pb-1.5 font-normal">Class</th>
                <th className="text-left pb-1.5 font-normal">Position</th>
                <th className="text-left pb-1.5 font-normal">Tasking</th>
                <th className="text-left pb-1.5 font-normal">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {[
                { hull: 'USS Theodore Roosevelt (CVN-71)', cls: 'Nimitz CV',   pos: 'Red Sea',            task: 'Strike ops / Houthi suppression',   status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Abraham Lincoln (CVN-72)',    cls: 'Nimitz CV',   pos: 'N. Arabian Sea',     task: 'Strike / coalition CDG escort',     status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Eisenhower (CVN-69)',         cls: 'Nimitz CV',   pos: 'Gulf of Oman',       task: 'GOM strike / Hormuz interdiction',  status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Leyte Gulf (CG-55)',          cls: 'Tico CG',     pos: '24.3°N 57.8°E',      task: 'BMD/AAW — SM-3 SRBM engagement D22',status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Georgia (SSGN-729)',          cls: 'Ohio SSGN',   pos: 'Gulf of Oman',       task: 'TLAM strike platform — standby',    status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Mason (DDG-87)',              cls: 'Burke DDG',   pos: 'Arabian Sea',        task: 'BDA repair 65% — LIM AAW',          status: 'DEGRADED',    sc: 'text-amber-400' },
                { hull: 'USS Gravely (DDG-107)',           cls: 'Burke DDG',   pos: 'SAG Bravo 25.2°N',   task: 'SAG AAW screen / MCM escort',       status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS San Antonio (LPD-17)',        cls: 'San Antonio', pos: '23.0°N 59.5°E',      task: 'CSAR / NEO platform on standby',    status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Chief (MCM-14)',              cls: 'Avenger MCM', pos: 'Hormuz ZB-Alpha',    task: 'MCM — 78% cleared',                 status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'USS Gladiator (MCM-11)',          cls: 'Avenger MCM', pos: 'Hormuz ZB-Alpha',    task: 'MCM — new mine hold lifted 0830Z',  status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'HMAS Hobart (DDH-39)',            cls: 'Hobart DDG',  pos: 'Gulf of Oman E.',    task: 'ZD-Bravo escort / IAMD',            status: 'OPERATIONAL', sc: 'text-emerald-400' },
                { hull: 'HMS Diamond (D34)',               cls: 'T45 DDG',     pos: 'Red Sea',            task: 'Red Sea AAW / Houthi threat',       status: 'OPERATIONAL', sc: 'text-emerald-400' },
              ].map(({ hull, cls, pos, task, status, sc }) => (
                <tr key={hull} className="py-1">
                  <td className="py-1.5 text-zinc-300 font-medium">{hull}</td>
                  <td className="py-1.5 text-zinc-500">{cls}</td>
                  <td className="py-1.5 text-zinc-500">{pos}</td>
                  <td className="py-1.5 text-zinc-500 max-w-[120px]">{task}</td>
                  <td className={`py-1.5 font-bold ${sc}`}>{status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* MCM Channel Progress + Active Threats */}
        <div className="space-y-4">
          <div className="tac-card p-4 space-y-3">
            <div className="flex items-center gap-2 mb-1">
              <Layers size={12} className="text-cyan-600" />
              <p className="text-[9px] font-bold text-cyan-600 tracking-widest uppercase">MCM Channel Progress — Hormuz Strait · Day {CONFLICT_DAY}</p>
            </div>
            {[
              { ch: 'ZB-Alpha (Main)',    pct: 78, eta: 'CLEARED D23',   ships: 'Chief + Gladiator on station', color: 'bg-emerald-500' },
              { ch: 'ZB-Bravo (South)',  pct: 45, eta: 'CLEARED D25',   ships: 'MH-53E det + MH-60S',           color: 'bg-amber-500' },
              { ch: 'ZB-Charlie (N.)',   pct: 18, eta: 'D29',            ships: 'Started D24 — MCM-7 on station', color: 'bg-zinc-600' },
              { ch: 'ZC-Beta (Larak)',   pct: 91, eta: 'D22',   ships: 'HMS Chiddingfold',                     color: 'bg-cyan-500' },
              { ch: 'ZD-Alpha (GOM W.)', pct: 99, eta: 'OPEN',  ships: 'Escort on request',                   color: 'bg-emerald-500' },
              { ch: 'ZD-Bravo (GOM E.)', pct: 100,eta: 'OPEN',  ships: 'HMAS Hobart escort',                  color: 'bg-emerald-500' },
            ].map(({ ch, pct, eta, ships, color }) => (
              <div key={ch} className="space-y-1">
                <div className="flex justify-between text-[9px]">
                  <span className="text-zinc-400 tracking-wider">{ch}</span>
                  <span className="text-zinc-500">{ships} · ETA {eta}</span>
                </div>
                <div className="w-full h-2 bg-zinc-900 rounded-full overflow-hidden">
                  <div
                    className={`h-2 rounded-full ${color}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="text-[8px] text-zinc-600">{pct}% cleared</p>
              </div>
            ))}
            <p className="text-[8px] text-zinc-700 pt-1 border-t border-zinc-900">
              ✓ GOLF-7 retired to Bandar Abbas D26 — no new mine activity since D24. ZB-Alpha open for commercial transit under coalition MCM escort.
            </p>
          </div>

          <div className="video-feed-frame tac-card p-4 space-y-2 relative">
            <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
            <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse" />
              <span className="text-[7px] text-red-500/60 font-bold tracking-[0.2em]">THREAT FEED</span>
            </div>
            <div className="flex items-center gap-2 mb-1 relative z-[1]">
              <ShieldAlert size={12} className="text-red-500 drop-shadow-[0_0_4px_rgba(239,68,68,0.4)]" />
              <p className="text-[9px] font-bold text-red-500 tracking-widest uppercase glow-red">Active Maritime Threat Events — Day {CONFLICT_DAY}</p>
            </div>
            {liveDmoEvents.map((ev) => (
              <div key={ev.event_id} className="flex gap-2 text-[9px] border-b border-zinc-900/60 pb-2 last:border-0 border-l-2 border-l-emerald-800 pl-2">
                <span className="text-zinc-600 shrink-0 w-14">{ev.time_zulu}</span>
                <span className={`shrink-0 font-bold tracking-widest ${
                  ev.priority === 'CRITICAL' ? 'text-red-500' :
                  ev.priority === 'HIGH'     ? 'text-amber-400' :
                  ev.priority === 'INFO'     ? 'text-zinc-400' :
                                              'text-yellow-600'
                }`}>{ev.priority}</span>
                <span className="text-zinc-500 leading-relaxed flex-1">{ev.body}</span>
                <Cpu size={7} className="text-emerald-700 shrink-0 mt-0.5" />
              </div>
            ))}
            {liveDmoEvents.length === 0 && intelFallback.map((item) => (
              <div key={item.id} className="flex gap-2 text-[9px] border-b border-zinc-900/60 pb-2 last:border-0 border-l-2 border-l-cyan-900 pl-2">
                <span className="text-zinc-600 shrink-0 w-14">{new Date(item.created_at).toISOString().slice(11,16)}Z</span>
                <span className="shrink-0 font-bold tracking-widest text-cyan-400">INTEL</span>
                <span className="text-zinc-500 leading-relaxed flex-1">
                  {item.title}{item.summary ? ` — ${item.summary}` : ''}
                </span>
                <Cpu size={7} className="text-cyan-700 shrink-0 mt-0.5" />
              </div>
            ))}
            {liveDmoEvents.length === 0 && intelFallback.length === 0 && (
              <p className="text-[9px] text-zinc-600 text-center py-3 tracking-widest">AWAITING LIVE INTEL FEED</p>
            )}
          </div>
        </div>
      </div>

      {/* ROE / EMCON / Tactical notes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="tac-card p-4 space-y-1">
          <div className="flex items-center gap-2 mb-2">
            <Radio size={12} className="text-violet-500" />
            <p className="text-[9px] font-bold text-violet-500 tracking-widest uppercase">EMCON / ROE Status</p>
          </div>
          {[
            ['EMCON State',      'DELTA (Strict)',     'text-amber-400'],
            ['ROE Profile',      'WARTIME ROE — Annex F', 'text-red-400'],
            ['ASCM Engagement',  'WEAPONS FREE — Track 45°+ closure', 'text-red-400'],
            ['Mine Avoidance',   'ZB-Alpha safe lane only — all other water DANGER', 'text-red-400'],
            ['FAC ROE',          'Warning shots; fire if closure continues inside 1,000m', 'text-amber-400'],
            ['Tanker escort',    'SUSPENDED — TRANSCOM order effective 0001Z Day 8', 'text-zinc-400'],
          ].map(([label, val, sc]) => (
            <div key={label} className="flex justify-between border-b border-zinc-900/40 pb-1 text-[9px]">
              <span className="text-zinc-600 tracking-wider">{label}</span>
              <span className={`${sc} font-medium text-right max-w-[55%]`}>{val}</span>
            </div>
          ))}
        </div>

        <div className="tac-card p-4 space-y-1">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={12} className="text-amber-500" />
            <p className="text-[9px] font-bold text-amber-500 tracking-widest uppercase">Tactical Notes — Day {CONFLICT_DAY}</p>
          </div>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ <span className="text-red-400 font-bold animate-pulse">⚑ KHAMENEI KIA D22:</span> Iranian Supreme Leader Ali Khamenei killed in precision airstrike 221435Z on IRGC National Command Post Tehran. IRGC retaliation posture UNKNOWN — all regional naval/air/missile assets at MAXIMUM readiness. National Command Authority alerted. FPCON DELTA theatre-wide. Source: NEXUS/DIA FLASH.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ <span className="text-amber-400 font-bold">USS MASON C-802 HIT D13:</span> DDG-87 struck by IRGC Navy C-802 ASCM from Qeshm Island battery Day 13 0930Z. 88% CONF. 1 KIA (PO2 Morales), 6 WIA. Superstructure fire controlled in 90 minutes. Combat systems FUNCTIONAL; propulsion DEGRADED max 9kts. Repair 65% complete — ETA full AAW capability D24.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ <span className="text-emerald-400 font-bold">B-21 RAIDER COMBAT DEBUT:</span> ANVIL-01 employed 2× GBU-57B MOP against IRGC Natanz hardened tunnel complex D22. BDA pending NGA SAR imagery. First combat use of B-21 Raider confirmed.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ <span className="text-red-400 font-bold">FATEH-110 SRBM D22:</span> CG-55 LEYTE GULF SM-3 Block IIA intercept of Fateh SRBM 0835Z. Assessed kill — debris impact Gulf of Oman 80nm SE of target. Second SRBM engagement this conflict.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ Virginia-class SSNs (774, 777) Hormuz chokepoint patrol. SSN-777 N. CAROLINA transitioned D26 — GOLF-7 inactive, Bandar Abbas inbound. TLAM loadout fully operational — 2hr strike cycle maintained.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ LUSV wolfpack α/β/γ providing ISR relay and MCM mine detection support — ZB-Bravo/Charlie surveys ongoing under CTF-52 authority.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ SAG Bravo (DDG-107 GRAVELY + CG-55 LEYTE GULF) patrolling 12NM outside territorial limit. 4× IRGCN FAC on threat vector — weapons free inside 1,000m per ROE Foxtrot.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ USS Mason (DDG-87) — C-802 ASCM hit D13 (Qeshm Island battery, 88% CONF). 1 KIA, 6 WIA. BDA repair 65% complete — aft VLS OPERATIONAL, fwd VLS offline. Max SOG 9kts. ETA full AAW D24. Operating in GOM reduced-threat zone.</p>
          <p className="text-[9px] text-zinc-500 leading-relaxed">▸ Coalition: HMS Diamond Red Sea AAW; HMAS Hobart ZD-Bravo escort; CDG group 24+ sorties/day; SCALP-EG strike Qeshm IADS node confirmed D21.</p>
          <p className="text-[9px] text-zinc-600 leading-relaxed mt-2 pt-1 border-t border-zinc-900">Source: NAVCENT OPREP-3 / CENTCOM SITREP #{getConflictDay()} / CAOC BLUE DAGGER DAY {getConflictDay()}</p>
        </div>
      </div>
    </section>
  )
}
