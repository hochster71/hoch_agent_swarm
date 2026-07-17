import {
  Package,
  Fuel,
  Zap,
  AlertTriangle,
  CheckCircle2,
  MinusCircle,
  XCircle,
  ExternalLink,
  Heart,
  Truck,
  Cpu,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toDateStr, toShortDate } from '@/lib/conflict-day'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0
export const metadata = { title: 'Logistics & Sustainment — Operation Epic Fury' }

const CONFLICT_DAY  = getConflictDay()
const CONFLICT_DATE = toDateStr(CONFLICT_DAY)

/** Build a resupply ETA label that auto-ages as CONFLICT_DAY advances */
function etaLabel(deliveredDay: number, suffix: string): string {
  if (CONFLICT_DAY > deliveredDay) return `Day ${deliveredDay} — RECEIVED (${suffix})`
  if (CONFLICT_DAY === deliveredDay) return `TODAY Day ${deliveredDay} — ARRIVING (${suffix})`
  return `Day ${deliveredDay} — ETA in ${deliveredDay - CONFLICT_DAY}d (${suffix})`
}

// ── Types ─────────────────────────────────────────────────────────────────────

type ReadinessLevel = 'C1' | 'C2' | 'C3' | 'C4'
type StockStatus    = 'ADEQUATE' | 'MARGINAL' | 'CRITICAL' | 'WINCHESTER'

// ── Munitions Inventory ───────────────────────────────────────────────────────

interface MunitionRow {
  id: string
  name: string
  type: string
  pctRemaining: number
  status: StockStatus
  expended: number
  unit: string
  resupplyETA: string
  notes: string
}

const MUNITIONS: MunitionRow[] = [
  {
    id: 'sm3',
    name: 'SM-3 Block IIA',
    type: 'BMD Interceptor',
    pctRemaining: 38,
    status: 'CRITICAL',
    expended: 31,
    unit: 'rounds',
    resupplyETA: etaLabel(24, 'MPS-Guam transfer complete; USNS Wally Schirra T-AKE-8 delivery confirmed'),
    notes: 'Expended against 5 Iranian BM barrages D1–D26. D24 resupply restored to ~58% stockpile. BM Barrage Alpha-5 (D26) consumed additional 14 rounds. Ship USNS Wally Schirra delivery complete. CTF monitoring magazine depth ahead of any renewed barrages.',
  },
  {
    id: 'sm6',
    name: 'SM-6 Block I/IA',
    type: 'Area Defense / Anti-Ship',
    pctRemaining: 52,
    status: 'MARGINAL',
    expended: 96,
    unit: 'rounds',
    resupplyETA: `Day ${CONFLICT_DAY} (Raytheon Tucson priority)`,
    notes: 'Dual-role use (BMD + anti-ship) accelerating consumption. DDG magazine depth averages ~60% across 5th Fleet surface screen. SM-6 resupply C-17 pipeline active from Raytheon Tucson surge lot.',
  },
  {
    id: 'tlam',
    name: 'BGM-109 Tomahawk (TLAM)',
    type: 'Land Attack Cruise Missile',
    pctRemaining: 44,
    status: 'MARGINAL',
    expended: 218,
    unit: 'rounds',
    resupplyETA: etaLabel(26, 'Raytheon priority lot — operational integration ongoing'),
    notes: 'Third strike wave Day 17 consumed 84 rounds against Natanz dispersal sites and Isfahan complex. SSGN USS Ohio (SSGN-726) VLS 60% expended. SSN pool maintaining 35% reserve.',
  },
  {
    id: 'essm',
    name: 'RIM-162 ESSM Block 2',
    type: 'Point Defense SHORAD',
    pctRemaining: 31,
    status: 'CRITICAL',
    expended: 142,
    unit: 'rounds',
    resupplyETA: etaLabel(23, 'Mk 41 reload ship WestPac inbound reload complete'),
    notes: `SHORAD consumption from Shahed swarm Days 8, 11, 14, 17. Mk 41 reload ship WestPac completed emergency ESSM reload Day 23. Two Mk 41 VLS cells aboard USS Bunker Hill (CG-52) restored to partial capacity. C-RAM canister ammunition below 30% on 3 Patriot batteries — resupply D27 ${CONFLICT_DAY > 27 ? 'RECEIVED' : 'pending'}.`,
  },
  {
    id: 'jdam',
    name: 'GBU-31/38 JDAM (all variants)',
    type: 'Precision Guided Munition',
    pctRemaining: 61,
    status: 'ADEQUATE',
    expended: 1240,
    unit: 'rounds',
    resupplyETA: 'Continuous (C-17 airlift)',
    notes: 'JDAM consumption on track with pre-war planning assumptions. GBU-31 2,000lb variant adequate; GBU-53 StormBreaker (SDB-II) stocks at 55%. C-17 resupply sorties from CONUS operational daily.',
  },
  {
    id: 'agm88',
    name: 'AGM-88E AARGM-ER',
    type: 'Anti-Radiation Missile (SEAD)',
    pctRemaining: 29,
    status: 'CRITICAL',
    expended: 74,
    unit: 'rounds',
    resupplyETA: etaLabel(28, 'Northrop Grumman production surge — KESTREL SEAD loadout priority'),
    notes: 'SEAD employment against IRGCAF S-300 and Bavar-373 SAM systems consumed significant AARGM inventory. F/A-18E/F SEAD package KESTREL has been flying with reduced ARM loadout since Day 15. NGL: HARM Block 6W stocks drawn down to 18%.',
  },
  {
    id: 'aim120',
    name: 'AIM-120D-3 AMRAAM',
    type: 'BVR Air-to-Air Missile',
    pctRemaining: 74,
    status: 'ADEQUATE',
    expended: 52,
    unit: 'rounds',
    resupplyETA: 'Continuous (C-17 airlift)',
    notes: 'Limited air-to-air engagements — Iran chose not to contest air superiority after losing 8 jets Day 1–3. AIM-120 consumption primarily against UCAV and cruise missile intercepts. Stocks adequate for sustained campaign.',
  },
  {
    id: 'gbumop',
    name: 'GBU-57A/B MOP',
    type: 'Massive Ordnance Penetrator',
    pctRemaining: 0,
    status: 'WINCHESTER',
    expended: 8,
    unit: 'rounds',
    resupplyETA: 'None — production rate 1/month (Boeing) — NO STOCK IN THEATER',
    notes: 'WINCHESTER as of Day 22. 6 expended Days 1–19 (Fordow ×2, Natanz ×4). Final 2 rounds employed by B-21 RAIDER ANVIL-01 against Natanz hardened tunnel complex Day 22 0447Z — COMBAT DEBUT. Only 8 MOPs in global inventory maintained; reconstitution ETA earliest Day 52. B-2A Spirit crew on crew rest.',
  },
]

// ── Strike Groups ─────────────────────────────────────────────────────────────

interface CSG {
  name: string
  cv: string
  flag: string
  readiness: ReadinessLevel
  location: string
  sorties: number
  magazinePct: number
  fuel: number
  notes: string
  damage?: string
}

const STRIKE_GROUPS: CSG[] = [
  {
    name: 'CSG-12 (EISENHOWER)',
    cv: 'CVN-69 Dwight D. Eisenhower',
    flag: 'CTF-3 ALFA',
    readiness: 'C1',
    location: 'Northern Gulf · 26.2°N / 53.4°E',
    sorties: 1400,
    magazinePct: 58,
    fuel: 72,
    notes: 'CVW-7 at 1,400+ total sorties — full combat power. No aircraft lost to hostile fire. F/A-18E/F Block III night sorties averaging 3.2/day per squadron. Carrier onboard delivery C-2A Greyhound running continuous resupply from Bahrain.',
  },
  {
    name: 'CSG-2 (ROOSEVELT)',
    cv: 'CVN-71 Theodore Roosevelt',
    flag: 'CTF-3 BRAVO',
    readiness: 'C2',
    location: 'Arabian Sea · 23.1°N / 60.5°E',
    sorties: 1200,
    magazinePct: 63,
    fuel: 68,
    notes: 'CVW-11 providing southern arc coverage. TLAM salvo Day 17 consumed 32 rounds from USS Cole (DDG-67). HSM-46 Wolfpack helicopter squadron conducting ASW/MCM operations Hormuz approaches. Degraded SOE (synchronised operating envelope) due to helo tempo.',
  },
  {
    name: 'CSG-8 (FORD)',
    cv: 'CVN-78 Gerald R. Ford',
    flag: 'CTF-3 CHARLIE (Reserve)',
    readiness: 'C2',
    location: 'Red Sea · 15.4°N / 42.3°E',
    sorties: 700,
    magazinePct: 79,
    fuel: 85,
    notes: `Transiting Red Sea to Arabian Sea — ETA Day ${CONFLICT_DAY}. Full combat power once on station. AAVS and CATCC operational post-Day 5 electromagnetic system fixes. Fresh magazine — will provide SM-3/SM-6 relief to forward groups.`,
  },
  {
    name: 'FS Charles de Gaulle (R91)',
    cv: 'PA Charles de Gaulle',
    flag: 'French ALFAN (Coalition)',
    readiness: 'C1',
    location: 'Arabian Sea · 22.8°N / 61.2°E',
    sorties: 500,
    magazinePct: 71,
    fuel: 66,
    notes: 'French PA operational Day 18 — adding 24+ Rafale M sorties daily. Aster 15/30 magazine intact. EC-725 Caïman helicopters conducting logistics relay. French FREMM Alsace and Provence escorting with Aster 30 Block 1NT BMD.',
  },
]

// ── Sustainment by domain ─────────────────────────────────────────────────────

interface SustainRow {
  category: string
  items: { label: string; value: string; status: StockStatus }[]
}

const SUSTAINMENT: SustainRow[] = [
  {
    category: 'Aviation Fuel (JP-5/JP-8)',
    items: [
      { label: 'Al Udeid AB reserve', value: '34 days remaining at current sortie rate', status: 'ADEQUATE' },
      { label: 'Naval aviation (JP-5)', value: '22 days — tanker USNS Washington Chambers enroute', status: 'MARGINAL' },
      { label: 'Al Dhafra AB (UAE)', value: '41 days — buffer from UAE strategic reserve', status: 'ADEQUATE' },
    ],
  },
  {
    category: 'Ordnance / JLOTS',
    items: [
      { label: 'JLOTS throughput Bahrain', value: '1,800 short tons/day — 15% below plan (IRGCN threat)', status: 'MARGINAL' },
      { label: 'MPF ship USNS Watson (LMSR)', value: 'Offload complete Day 19 Salalah Oman — 4 APS sets combat-ready Day 20', status: 'ADEQUATE' },
      { label: 'C-17 resupply sorties', value: '22 sorties/day Dover→Al Udeid — on schedule', status: 'ADEQUATE' },
    ],
  },
  {
    category: 'Ballistic Missile Defense',
    items: [
      { label: 'THAAD battery PAC Bay Kuwait', value: '41% interceptors remaining — reload 10 days', status: 'CRITICAL' },
      { label: 'Patriot PAC-3 Qatar (3 batteries)', value: '28% MSE rounds — Winchester on 2 fire units', status: 'CRITICAL' },
      { label: 'Aegis Ashore Romania', value: 'Full — not in theater but SM-3 reserve available', status: 'ADEQUATE' },
    ],
  },
  {
    category: 'Medical / CASEVAC',
    items: [
      { label: 'USNS Comfort (T-AH-20) trauma beds', value: '847/1,000 available — Bahrain anchor', status: 'ADEQUATE' },
      { label: 'Forward surgical teams', value: '6/6 operational across theater', status: 'ADEQUATE' },
      { label: 'Blood products (O-neg)', value: '6-day supply on hand — resupply pipeline active', status: 'MARGINAL' },
    ],
  },
]

// ── Casualty Report ───────────────────────────────────────────────────────────

const CASUALTIES = {
  us: { kia: 11, wia: 47, missing: 2, pow: 3 },
  coalition: { kia: 6, wia: 19, missing: 0, pow: 0 },
  iran_est: { kia: 840, wia: 2100, captured: 47 },
  civilian_est: { killed: 390, displaced: 142000 },
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: StockStatus }) {
  const cfg: Record<StockStatus, string> = {
    ADEQUATE:  'text-emerald-400 border-emerald-700 bg-emerald-950/20',
    MARGINAL:  'text-amber-400  border-amber-700  bg-amber-950/20',
    CRITICAL:  'text-red-400    border-red-700    bg-red-950/30',
    WINCHESTER:'text-zinc-400   border-zinc-600   bg-zinc-800',
  }
  const Icon = status === 'ADEQUATE' ? CheckCircle2 : status === 'MARGINAL' ? MinusCircle : XCircle
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm uppercase', cfg[status])}>
      <Icon size={9} />{status}
    </span>
  )
}

function ReadinessBadge({ level }: { level: ReadinessLevel }) {
  const cfg: Record<ReadinessLevel, string> = {
    C1: 'text-emerald-400 border-emerald-700 bg-emerald-950/20',
    C2: 'text-yellow-400  border-yellow-700  bg-yellow-950/20',
    C3: 'text-amber-400   border-amber-700   bg-amber-950/20',
    C4: 'text-red-400     border-red-700     bg-red-950/30',
  }
  const desc: Record<ReadinessLevel, string> = { C1: 'Full', C2: 'Substantial', C3: 'Degraded', C4: 'Not Ready' }
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm', cfg[level])}>
      {level} — {desc[level]}
    </span>
  )
}

function MunitionBar({ pct, status }: { pct: number; status: StockStatus }) {
  const color = status === 'ADEQUATE' ? 'bg-emerald-500' : status === 'MARGINAL' ? 'bg-amber-500' : status === 'CRITICAL' ? 'bg-red-500' : 'bg-zinc-600'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-zinc-800 rounded-sm overflow-hidden">
        <div className={cn('h-full rounded-sm', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn('text-sm font-bold tabular-nums w-10 text-right',
        status === 'ADEQUATE' ? 'text-emerald-400' : status === 'MARGINAL' ? 'text-amber-400' : status === 'CRITICAL' ? 'text-red-400' : 'text-zinc-500'
      )}>{pct}%</span>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function LogisticsPage() {
  const critMunitions = MUNITIONS.filter((m) => m.status === 'CRITICAL').length
  const margMunitions = MUNITIONS.filter((m) => m.status === 'MARGINAL').length

  // Fetch live AI logistics events from Supabase
  interface LiveLogEvent { id: number; munition_id: string; event_type: string; description: string; quantity?: number; conflict_day: number; created_at: string }
  let liveLogEvents: LiveLogEvent[] = []
  try {
    const sb = await createServerClient()
    if (sb) {
      const since = new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString()
      const { data } = await sb
        .from('logistics_events')
        .select('*')
        .gte('created_at', since)
        .order('created_at', { ascending: false })
        .limit(15)
      liveLogEvents = (data ?? []) as LiveLogEvent[]
    }
  } catch { /* non-fatal */ }

  return (
    <div className="space-y-5 max-w-screen-xl">

      {/* ── Cinematic J4 Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(245,158,11,0.012) 2px, rgba(245,158,11,0.012) 4px)'}} />
          <div className="relative z-[3] flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="relative">
                <Package size={26} className="text-amber-400 drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-400 rounded-full animate-pulse" />
              </div>
              <div>
                <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                  J4 Logistics & Sustainment — Day {CONFLICT_DAY} Status
                </p>
                <h1 className="text-lg font-bold tracking-widest text-amber-400 glow-amber uppercase">
                  COALITION SUSTAINMENT — {CONFLICT_DATE}
                </h1>
                <p className="text-[10px] text-zinc-500 mt-1 leading-relaxed max-w-lg">
                  J4 logistics status across munitions, fuel, fleet readiness, and sustainment pipelines.
                  BMD interceptor and SEAD munitions critically low — resupply priority ALPHA.
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <div className="on-air-badge inline-block bg-amber-900/60 text-amber-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-amber-800/60">
                ● J4 LIVE
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'CRITICAL', count: critMunitions, color: 'border-red-800 bg-red-950/20 text-red-400' },
                  { label: 'MARGINAL', count: margMunitions, color: 'border-amber-800 bg-amber-950/20 text-amber-400' },
                ].map(({ label, count, color }) => (
                  <div key={label} className={cn('tac-card data-card-glow border rounded-sm p-2.5 text-center', color)}>
                    <p className="text-xl font-bold tabular-nums">{count}</p>
                    <p className="text-[8px] tracking-widest uppercase">{label} Munitions</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="studio-accent-bar-amber" />
      </div>

      {/* Critical Interceptor Magazine Depth — Ring Gauges — cinematic */}
      <div className="video-feed-frame tac-card-critical border-red-900/50 p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-red-500/60 font-bold tracking-[0.2em]">BMDS ALERT</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <AlertTriangle size={11} className="text-red-400 animate-pulse drop-shadow-[0_0_4px_rgba(239,68,68,0.4)]" />
          <span className="text-red-400 glow-red">CRITICAL — Interceptor &amp; BMD Magazine Depth</span>
          <span className="ml-auto text-[9px] text-red-700 normal-case tracking-normal font-normal">NCA NOTICE · RESUPPLY PRIORITY ALPHA</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
          {[
            { label: 'SM-3 Block IIA',      pct: 38, status: 'CRITICAL' as StockStatus, expended: 31,  resupply: 'D24' },
            { label: 'SM-6 Block I/IA',     pct: 52, status: 'MARGINAL' as StockStatus, expended: 96,  resupply: 'D22' },
            { label: 'ESSM Block 2',        pct: 31, status: 'CRITICAL' as StockStatus, expended: 142, resupply: 'D23' },
            { label: 'THAAD (PAC Bay KW)',  pct: 41, status: 'CRITICAL' as StockStatus, expended: 11,  resupply: 'D28' },
            { label: 'PAC-3 MSE (Qatar)',   pct: 28, status: 'CRITICAL' as StockStatus, expended: 36,  resupply: 'D30' },
          ].map(({ label, pct, status, expended, resupply }) => {
            const r = 28
            const circ = 2 * Math.PI * r
            const strokeColor = status === 'CRITICAL' ? '#ef4444' : '#f59e0b'
            const offset = circ - (pct / 100) * circ
            return (
              <div key={label} className="flex flex-col items-center gap-1">
                <svg width="72" height="72" viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="36" cy="36" r={r} fill="none" stroke="#18181b" strokeWidth="7" />
                  <circle
                    cx="36" cy="36" r={r}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth="7"
                    strokeDasharray={`${circ}`}
                    strokeDashoffset={`${offset}`}
                    strokeLinecap="round"
                    transform="rotate(-90 36 36)"
                  />
                  <text x="36" y="40" textAnchor="middle" fontSize="11" fontWeight="bold" fill={strokeColor} fontFamily="monospace">{pct}%</text>
                </svg>
                <p className="text-[8px] font-bold text-zinc-400 text-center leading-tight tracking-wide">{label}</p>
                <div className="flex gap-2 text-[7px] tracking-widest text-center">
                  <span className="text-zinc-600">×{expended} EXP</span>
                  <span className="text-zinc-700">ETA {resupply}</span>
                </div>
                <span className={cn('text-[7px] font-bold tracking-widest', status === 'CRITICAL' ? 'text-red-400' : 'text-amber-400')}>{status}</span>
              </div>
            )
          })}
        </div>
        <p className="text-[8px] text-zinc-700 pt-1 border-t border-zinc-900">* Combat expenditure rates may exceed 72h resupply window. THAAD reload requires C-17 airlift + technical crew — Day 28 earliest. PAC-3 MSE winchester risk if second major BM salvo occurs before Day 30.</p>
      </div>

      {/* Munitions inventory */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Zap size={11} className="text-amber-400" />
          <span>Munitions Inventory — Day {CONFLICT_DAY} (8 Systems)</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">% of pre-conflict theater stockpile</span>
        </div>
        <div className="space-y-3">
          {MUNITIONS.sort((a, b) => {
            const o: Record<StockStatus, number> = { CRITICAL: 0, MARGINAL: 1, WINCHESTER: 2, ADEQUATE: 3 }
            return o[a.status] - o[b.status]
          }).map((m) => (
            <div key={m.id} className="border border-zinc-800 rounded p-3 space-y-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-bold text-zinc-100">{m.name}</p>
                    <StatusBadge status={m.status} />
                  </div>
                  <p className="text-[9px] text-zinc-500 tracking-wider">{m.type} · Expended: {m.expended.toLocaleString()} {m.unit}</p>
                </div>
                <p className="text-[9px] text-zinc-600 shrink-0">
                  Resupply ETA: <span className="text-amber-600">{m.resupplyETA}</span>
                </p>
              </div>
              <MunitionBar pct={m.pctRemaining} status={m.status} />
              <p className="text-[10px] text-zinc-500 leading-relaxed">{m.notes}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Strike Group Readiness — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-sky-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-sky-500/60 font-bold tracking-[0.2em]">NAVCENT</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <Fuel size={11} className="text-sky-400 drop-shadow-[0_0_4px_rgba(56,189,248,0.4)]" />
          <span className="text-sky-400 glow-blue">Carrier Strike Group Readiness — 4 CSGs / PA</span>
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {STRIKE_GROUPS.map((csg) => (
            <div key={csg.name} className="border border-zinc-800 rounded p-3 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-[9px] font-bold text-zinc-500 tracking-widest uppercase">{csg.flag}</p>
                  <p className="text-sm font-bold text-zinc-100">{csg.cv}</p>
                  <p className="text-[9px] text-zinc-600">{csg.location}</p>
                </div>
                <ReadinessBadge level={csg.readiness} />
              </div>
              {/* Mini stats */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Combat Sorties', value: csg.sorties.toString(), color: 'text-emerald-400' },
                  { label: 'Magazine', value: `${csg.magazinePct}%`, color: csg.magazinePct < 50 ? 'text-red-400' : 'text-amber-400' },
                  { label: 'Fuel', value: `${csg.fuel}%`, color: csg.fuel < 60 ? 'text-amber-400' : 'text-emerald-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-zinc-900 rounded p-2 text-center">
                    <p className={cn('text-base font-bold tabular-nums', color)}>{value}</p>
                    <p className="text-[8px] text-zinc-600 uppercase tracking-widest">{label}</p>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-zinc-500 leading-relaxed">{csg.notes}</p>
              {csg.damage && (
                <div className="flex items-start gap-1.5 bg-amber-950/20 border border-amber-900/50 rounded px-2 py-1.5">
                  <AlertTriangle size={9} className="text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-[10px] text-amber-400">{csg.damage}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* J4 Resupply Pipeline — Inbound Assets — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">TRANSCOM</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <Truck size={11} className="text-emerald-400 drop-shadow-[0_0_4px_rgba(16,185,129,0.4)]" />
          <span className="glow-green">J4 Resupply Pipeline — Inbound Assets</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">Day {CONFLICT_DAY} / {toShortDate(CONFLICT_DAY)}</span>
        </div>
        <div className="relative pl-5 space-y-3">
          <div className="absolute left-2 top-1 bottom-1 w-px bg-zinc-800" />
          {[
            {
              day: 22, pct: 75,
              ship: 'USNS Wally Schirra (T-AKE-8)',
              cargo: 'SM-6 Block IA ×64 · ESSM Block 2 ×96 · Tomahawk Block V ×48 · SDB ×240',
              status: 'ENROUTE', color: 'bg-emerald-600', dotColor: 'bg-emerald-500',
            },
            {
              day: 24, pct: 45,
              ship: 'C-17 ALPHA-PRIOR (6× sorties) + MPS Guam transfer',
              cargo: 'SM-3 Block IIA ×18 (Pt Mugu reserve) · PAC-3 MSE ×24 · THAAD kill vehicles ×12',
              status: 'PLANNED', color: 'bg-sky-700', dotColor: 'bg-sky-500',
            },
            {
              day: 26, pct: 20,
              ship: 'USNS Rainier (T-AOE-7) + Raytheon priority production lot',
              cargo: 'Tomahawk Block V ×120 (Raytheon Tucson) · JASSM-ER ×24 · GBU-57 MOP ×2',
              status: 'PLANNED', color: 'bg-zinc-600', dotColor: 'bg-zinc-500',
            },
            {
              day: 30, pct: 5,
              ship: 'USNS Watson (LMSR) — 2nd lift APS sets',
              cargo: 'GBU-39/B SDB II ×400 · AGM-154C JSOW ×96 · AARGM-ER ×24 · AGM-84 ×12',
              status: 'PLANNED', color: 'bg-zinc-700', dotColor: 'bg-zinc-600',
            },
          ].map(({ day, pct, ship, cargo, status, color, dotColor }) => (
            <div key={day} className="relative ml-2">
              <div className="absolute -left-[21px] w-3.5 h-3.5 rounded-full bg-zinc-900 border border-zinc-700 flex items-center justify-center top-1">
                <div className={cn('w-2 h-2 rounded-full', dotColor)} />
              </div>
              <div className="border border-zinc-800 rounded p-2.5 space-y-1.5">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold text-zinc-200 tracking-widest">DAY {day}</span>
                    <span className="text-[9px] text-zinc-400">{ship}</span>
                  </div>
                  <span className={cn('text-[8px] font-bold tracking-widest shrink-0',
                    status === 'ENROUTE' ? 'text-emerald-400' : 'text-zinc-500'
                  )}>{status}</span>
                </div>
                <p className="text-[9px] text-zinc-500">{cargo}</p>
                <div className="h-1 bg-zinc-900 rounded-full overflow-hidden">
                  <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sustainment status */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Truck size={11} className="text-zinc-400" />
          <span>Sustainment Pipeline Status</span>
        </div>
        <div className="space-y-4">
          {SUSTAINMENT.map((group) => (
            <div key={group.category}>
              <p className="text-[9px] font-bold tracking-widest text-zinc-400 uppercase mb-2">{group.category}</p>
              <div className="space-y-1.5">
                {group.items.map((item) => (
                  <div key={item.label} className="flex items-start justify-between gap-3 py-1.5 border-b border-zinc-800/60 last:border-0">
                    <div>
                      <p className="text-[10px] font-bold text-zinc-300">{item.label}</p>
                      <p className="text-[10px] text-zinc-500">{item.value}</p>
                    </div>
                    <StatusBadge status={item.status} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Casualty Report — cinematic */}
      <div className="tac-card-critical p-4 space-y-3 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none z-0" style={{background: 'linear-gradient(135deg, rgba(239,68,68,0.04), transparent 60%)'}} />
        <div className="tac-section-header mb-1 relative z-[1]">
          <Heart size={11} className="text-red-500 drop-shadow-[0_0_4px_rgba(239,68,68,0.5)]" />
          <span className="text-red-400 glow-red">Casualty Report — Day {CONFLICT_DAY}</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">Source: CENTCOM J1 / OCHA</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* US */}
          <div className="border border-zinc-800 rounded p-3 space-y-2">
            <p className="text-[9px] font-bold tracking-widest text-zinc-400 uppercase">US Forces</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'KIA', value: CASUALTIES.us.kia, color: 'text-red-400' },
                { label: 'WIA', value: CASUALTIES.us.wia, color: 'text-amber-400' },
                { label: 'MIA', value: CASUALTIES.us.missing, color: 'text-yellow-400' },
                { label: 'POW', value: CASUALTIES.us.pow, color: 'text-sky-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center">
                  <p className={cn('text-xl font-bold tabular-nums', color)}>{value}</p>
                  <p className="text-[8px] text-zinc-600 uppercase tracking-widest">{label}</p>
                </div>
              ))}
            </div>
          </div>
          {/* Coalition */}
          <div className="border border-zinc-800 rounded p-3 space-y-2">
            <p className="text-[9px] font-bold tracking-widest text-zinc-400 uppercase">Coalition Partners</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'KIA', value: CASUALTIES.coalition.kia, color: 'text-red-400' },
                { label: 'WIA', value: CASUALTIES.coalition.wia, color: 'text-amber-400' },
                { label: 'MIA', value: CASUALTIES.coalition.missing, color: 'text-yellow-400' },
                { label: 'POW', value: CASUALTIES.coalition.pow, color: 'text-sky-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center">
                  <p className={cn('text-xl font-bold tabular-nums', color)}>{value}</p>
                  <p className="text-[8px] text-zinc-600 uppercase tracking-widest">{label}</p>
                </div>
              ))}
            </div>
          </div>
          {/* Iran + Civilian est */}
          <div className="border border-zinc-800 rounded p-3 space-y-3">
            <div>
              <p className="text-[9px] font-bold tracking-widest text-zinc-400 uppercase mb-2">Iran (Estimated)</p>
              <div className="grid grid-cols-3 gap-1">
                {[
                  { label: 'KIA est.', value: CASUALTIES.iran_est.kia.toLocaleString(), color: 'text-red-500' },
                  { label: 'WIA est.', value: CASUALTIES.iran_est.wia.toLocaleString(), color: 'text-amber-500' },
                  { label: 'Captured', value: CASUALTIES.iran_est.captured.toString(), color: 'text-sky-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center">
                    <p className={cn('text-sm font-bold tabular-nums', color)}>{value}</p>
                    <p className="text-[8px] text-zinc-600 uppercase tracking-widest">{label}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="border-t border-zinc-800 pt-2">
              <p className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase mb-1.5">Civilian (OCHA Est.)</p>
              <div className="grid grid-cols-2 gap-1">
                {[
                  { label: 'Killed', value: CASUALTIES.civilian_est.killed.toLocaleString(), color: 'text-red-600' },
                  { label: 'Displaced', value: `${(CASUALTIES.civilian_est.displaced / 1000).toFixed(0)}K`, color: 'text-orange-500' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center">
                    <p className={cn('text-sm font-bold tabular-nums', color)}>{value}</p>
                    <p className="text-[8px] text-zinc-600 uppercase tracking-widest">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 pt-1 text-[9px] text-zinc-600">
          <a href="https://www.centcom.mil/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-zinc-400 transition-colors">
            <ExternalLink size={8} /> CENTCOM.MIL
          </a>
          <a href="https://www.unocha.org/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-zinc-400 transition-colors">
            <ExternalLink size={8} /> UN OCHA
          </a>
          <span className="ml-auto">Iranian figures are intelligence estimates — CENTCOM-assessed, not confirmed</span>
        </div>
      </div>

      {/* Live AI-extracted logistics events */}
      {liveLogEvents.length > 0 && (
        <div className="tac-card p-5 space-y-3">
          <div className="tac-section-header mb-3">
            <Cpu size={12} className="text-emerald-500" />
            <span>Live Logistics Events — NEXUS-AI</span>
            <span className="ml-auto text-[9px] text-emerald-600 normal-case font-normal tracking-widest">GPT-4o-mini extraction</span>
          </div>
          <div className="space-y-2">
            {liveLogEvents.map((ev) => (
              <div key={ev.id} className="flex items-start gap-3 p-2 bg-zinc-900/50 rounded-sm border border-zinc-800">
                <span className="text-[8px] text-emerald-500 font-bold tracking-widest shrink-0 mt-0.5">D{ev.conflict_day}</span>
                <div className="flex-1 min-w-0">
                  <span className="text-[8px] text-zinc-500 uppercase tracking-widest mr-2">{ev.event_type}</span>
                  <span className="text-[9px] text-zinc-400 leading-snug">{ev.description}</span>
                  {ev.quantity != null && (
                    <span className="ml-2 text-[8px] text-amber-500">×{ev.quantity}</span>
                  )}
                </div>
                <Cpu size={8} className="text-emerald-700 shrink-0 mt-0.5" />
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
