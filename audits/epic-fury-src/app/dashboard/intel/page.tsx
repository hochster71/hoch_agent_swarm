import {
  Radio,
  CheckCircle2,
  MinusCircle,
  XCircle,
  Lock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toDateStr } from '@/lib/conflict-day'
import { HeraldFeed } from '@/components/HeraldFeed'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { SourceRadar } from '@/components/SourceRadar'
import { IntelProvenanceGraph } from '@/components/IntelProvenanceGraph'
import { LiveIntelFeed } from '@/components/LiveIntelFeed'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0
export const metadata = { title: 'Multi-INT Intelligence — Operation Epic Fury' }

const CONFLICT_DAY  = getConflictDay()
const CONFLICT_DATE = toDateStr(CONFLICT_DAY)

// ── Types ─────────────────────────────────────────────────────────────────────

type StreamStatus = 'ACTIVE' | 'DEGRADED' | 'INTERMITTENT' | 'OFFLINE'
type ConfLevel    = 'HIGH' | 'MEDIUM' | 'LOW'
type ReportClass  = 'TS/SI/NF' | 'TS/NF' | 'SECRET' | 'UNCLASS'

interface Intercept {
  time: string
  summary: string
  conf: ConfLevel
  classification: ReportClass
  action?: string
}

interface IntelStream {
  id: string
  codename: string
  type: string
  description: string
  status: StreamStatus
  lastUpdate: string
  tasking: string
  intercepts: Intercept[]
}

interface HumintReport {
  id: string
  date: string
  theater: string
  source: string
  reliability: 'A' | 'B' | 'C' | 'D'
  credibility: '1' | '2' | '3' | '4'
  summary: string
  actionable: boolean
  classification: ReportClass
}

interface ImintReport {
  id: string
  date: string
  sensor: string
  target: string
  coordinates: string
  finding: string
  conf: ConfLevel
  classification: ReportClass
}

// ── SIGINT Streams ─────────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const STREAMS: IntelStream[] = [
  {
    id: 'trident',
    codename: 'TRIDENT',
    type: 'SIGINT · HF/VHF/SHF COMINT',
    description:
      'Strategic communications intercept of Supreme Leader, IRGC CINC, and IRGCAF command nets. Primary platform: RC-135V/W Rivet Joint operating from Al Udeid. Supplemented by EP-3E Aries II and NSA ground station Bahrain.',
    status: 'ACTIVE',
    lastUpdate: `Day ${CONFLICT_DAY} 06:15Z`,
    tasking: 'SL personal staff · IRGC Strategic Command · Missile Force command net',
    intercepts: [
      {
        time: `Day ${CONFLICT_DAY} 01:15Z`,
        summary:
          'New SL Mojtaba Khamenei secure line → IRGC CINC Salami, 9 minutes. Content not decrypted — traffic analysis. Pattern consistent with command assertion / authority confirmation exchange; NOT pre-strike authorisation pattern. IRGC hardliner faction commanders still using unsecured Iridium burst comms.',
        conf: 'HIGH',
        classification: 'TS/SI/NF',
        action: 'TRIDENT assessment: no pre-launch authentication indicators. IRGC hardliner faction monitored — elevated but contained.',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 22:40Z`,
        summary:
          'IRGCAF Missile Force command net: low-frequency, administrative traffic only. Operational tempo REDUCED 94% vs pre-ceasefire baseline. Consistent with stand-down order issued Day 32. No new COMSEC shifts observed.',
        conf: 'HIGH',
        classification: 'TS/SI/NF',
        action: 'CTF-3 THREATCON BRAVO maintained. Aegis ships AAW posture normal.',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 18:10Z`,
        summary:
          'IRGCN tactical 760 MHz net — administrative traffic only. FAC units Qeshm sector: routine harbour ops. GOLF-7 INACTIVE at Bandar Abbas (confirmed D26). GOLF-8 last located Bandar-e-Jask D17 — subsequent movement unconfirmed; assessed in port per ceasefire terms.',
        conf: 'MEDIUM',
        classification: 'TS/SI/NF',
        action: 'MCM corridor ZB-Alpha 100% cleared D35. No maritime threat indicators.',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 09:30Z`,
        summary:
          'Mojtaba Khamenei new SL office — outgoing call to Hezbollah Dahieh senior leadership (+20% vs Day 52 baseline). Traffic analysis suggests new SL asserting authority over proxy network. Hezbollah response posture REDUCED — consistent with ceasefire observance.',
        conf: 'MEDIUM',
        classification: 'TS/SI/NF',
      },
    ],
  },
  {
    id: 'cerberus',
    codename: 'CERBERUS',
    type: 'SIGINT · CYBER / ELINT · OT/IT',
    description:
      'NSA/CYBERCOM dedicated collection against Iranian APT operators (APT33, APT34, APT35) and IRGC cyber command infrastructure. Includes real-time telemetry from FBI/CISA sensor networks on US critical infrastructure.',
    status: 'ACTIVE',
    lastUpdate: `Day ${CONFLICT_DAY} 00:45Z`,
    tasking: 'APT34 OilRig · APT33 · IRGC Unit 400 Cyber · critical infrastructure defender telemetry',
    intercepts: [
      {
        time: `Day ${CONFLICT_DAY} 00:45Z`,
        summary:
          'APT34 (OilRig) lateral movement detected on CENTCOM logistics contractor subnet — 3 hosts isolated under CISA ED 26-01. Beacon pattern matches known OilRig "SnailSpeed" implant. C2 server: 185.220.xxx.xxx (Iran-attributed). FBI notified 01:00Z.',
        conf: 'HIGH',
        classification: 'TS/SI/NF',
        action: 'CISA ED 26-01 active — emergency patch order Ivanti CVE-2024-21887',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 14:20Z`,
        summary:
          'APT33 beacon activity detected on Saudi Aramco OT network, Dhahran sector — consistent with pre-positioning for destructive wiper payload. Pattern matches "Shamoon v3" precursor observed in 2022. Aramco cyber team notified.',
        conf: 'HIGH',
        classification: 'TS/NF',
        action: 'Aramco Dhahran OT network isolated — production unaffected — investigation ongoing',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 11:00Z`,
        summary:
          'APT35 (Charming Kitten) spear-phish campaign — 847 targeted emails to US CENTCOM personnel using "official CENTCOM logistics portal" lure. 3 confirmed clicks — no credential compromise. Indicators blocked DoDIN-wide.',
        conf: 'HIGH',
        classification: 'SECRET',
      },
      {
        time: `Day ${CONFLICT_DAY - 2} 07:00Z`,
        summary:
          'IRGC Unit 400: encrypted forum post (Farsi) referencing "dual-effect" operation against US Gulf financial nodes — SWIFT messaging infrastructure. Partial intercept only. FBI Cyber Division alerted.',
        conf: 'LOW',
        classification: 'TS/SI/NF',
      },
    ],
  },
  {
    id: 'nexus',
    codename: 'NEXUS',
    type: 'SIGINT/OSINT · All-Domain Fusion',
    description:
      'JADC2 all-domain fusion node combining TRIDENT, CERBERUS, MANTIS, ATLAS, and OSINT streams. AI-assisted correlation. Operated by NSA/CSS Persian Gulf Analytic Center. Real-time cross-domain indications & warning.',
    status: 'ACTIVE',
    lastUpdate: `Day ${CONFLICT_DAY} 06:30Z`,
    tasking: 'Cross-domain I&W · combined arms attack prediction · threat correlation',
    intercepts: [
      {
        time: `Day ${CONFLICT_DAY} 06:30Z`,
        summary:
          'NEXUS combined-arms convergence: TRIDENT pre-strike COMSEC shift + ATLAS TEL repositioning + CERBERUS APT34 lateral movement + IMINT Qeshm pre-arm = HIGH confidence combined BM + Shahed swarm coordinated attack within 48h. First time all 4 indicators have converged simultaneously.',
        conf: 'HIGH',
        classification: 'TS/SI/NF',
        action: 'THREATCON CHARLIE declared CTF-3 and all GCC bases — BMEWS fully active',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 20:00Z`,
        summary:
          'NEXUS pattern-of-life analysis: IRGCN Qeshm base activity index +340% vs 7-day baseline. Combines AIS dark transit + Shahed pre-arm + FAC fuelling + logistic vehicle thermal signatures. Attack window: next 24–36h.',
        conf: 'HIGH',
        classification: 'TS/SI/NF',
      },
    ],
  },
  {
    id: 'atlas',
    codename: 'ATLAS',
    type: 'SIGINT/GEOINT · TEL Tracking',
    description:
      'Dedicated transporter-erector-launcher (TEL) movement tracking fusing multi-INT: SAR IMINT, RF emissions, HUMINT reporting, and AI exploitation of commercial satellite imagery. Primary I&W for BM barrages.',
    status: 'ACTIVE',
    lastUpdate: `Day ${CONFLICT_DAY - 1} 22:00Z`,
    tasking: 'All IRGCAF BM TEL units — Emad, Ghadr, Shahab-3 · dispersal monitoring',
    intercepts: [
      {
        time: `Day ${CONFLICT_DAY - 1} 22:00Z`,
        summary:
          'TEL convoy ZULU-7: 4 × Emad TELs repositioning from Imam Ali Base (Khorramabad) via Route 7 to pre-surveyed hide site at grid 33.2°N / 47.8°E — 85km from known launch zone. Fuel and oxidiser vehicles in trail. Pre-launch posture: 6–12h.',
        conf: 'HIGH',
        classification: 'TS/SI/NF',
        action: 'F/A-18E/F strike package KESTREL-4 cued — awaiting NCA strike authority',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 16:30Z`,
        summary:
          'ATLAS count: 6 TELs active dispersal posture across Isfahan, Qom, and Kermanshah corridors (Day 22 NRO pass + Maxar WV-3 corroboration). Iran pre-conflict inventory ~200 Emad/Ghadr/Shahab-3; expended 120–140 assessed.',
        conf: 'MEDIUM',
        classification: 'TS/NF',
      },
      {
        time: `Day ${CONFLICT_DAY - 2} 08:00Z`,
        summary:
          'New TEL access road construction detected via SAR: 600m track extension at Bidganeh Missile Complex (35.1°N / 50.7°E). Assessed as response to precision targeting of known TEL routes. Engineers and heavy equipment.',
        conf: 'MEDIUM',
        classification: 'TS/NF',
      },
    ],
  },
  {
    id: 'mantis',
    codename: 'MANTIS',
    type: 'SIGINT/HUMINT · Maritime Intel',
    description:
      'CTF-151/CTF-3 dedicated maritime intelligence fusion. Combines P-8A Poseidon SIGINT, AIS anomaly detection, UUV SIGINT payloads, and embedded maritime HUMINT reporting from Hormuz littoral areas.',
    status: 'ACTIVE',
    lastUpdate: `Day ${CONFLICT_DAY} 05:00Z`,
    tasking: 'IRGCN FAC / FFGH · mine-layer tracking · Hormuz transit corridor I&W',
    intercepts: [
      {
        time: `Day ${CONFLICT_DAY} 05:00Z`,
        summary:
        `GOLF-7 INACTIVE — confirmed Bandar Abbas D26 14:20Z. MCM corridor ZB-Alpha 100% cleared D35 — first unescorted commercial VLCC transit confirmed D35. Commercial shipping resuming normal Hormuz routing. GOLF-8 last located Bandar-e-Jask D17 (EMCON) — subsequent assessed in port per ceasefire standdown order. Ceasefire MCM terms: IRGCN prohibited from re-seeding ZB corridors.`,
        conf: 'HIGH',
        classification: 'TS/SI/NF',
        action: 'COPPER GAVEL MCM ops continue ZB-Alpha — GOLF-8 locating effort ongoing Jask sector',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 23:15Z`,
        summary:
          'HUMINT: IRGCN FAC launch crew pre-positioned on Larak Island — 2× Type-03 "Zolfaghar" fast attack craft anchored offshore. Fuel bladder and munitions transfer observed at 21:00Z. Probable attack launch window: 01:00–04:00Z window.',
        conf: 'HIGH',
        classification: 'TS/NF',
        action: 'SH-60B and P-8A on station Larak approaches — ROE WEAPONS FREE maritime targets',
      },
      {
        time: `Day ${CONFLICT_DAY - 1} 14:00Z`,
        summary:
          'AIS anomaly: 23 tankers declared emergency diversion via Cape of Good Hope within 6-hour window — consistent with new mine threat report disseminated by UKMTO 13:30Z. MarineTraffic gap analysis: Hormuz traffic down 97% vs Day 0.',
        conf: 'HIGH',
        classification: 'UNCLASS',
      },
    ],
  },
]

// ── HUMINT Reports ─────────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const HUMINT: HumintReport[] = [
  {
    id: 'H-001',
    date: `Day ${CONFLICT_DAY - 1} · 18:00Z`,
    theater: 'IRAN / KERMANSHAH',
    source: 'ATLAS-HUMINT-7 (A/2)',
    reliability: 'A',
    credibility: '2',
    summary:
      'Source — access to IRGCAF logistics — observed oxidiser delivery trucks at Imam Ali Base Khorramabad on Day 20. 6 × 10,000L bowsers. Confirmed fuelling activity consistent with pre-launch preparation for Emad-class liquid-fuelled BMs. Source previously reported Day 7 and Day 18 barrages accurately.',
    actionable: true,
    classification: 'TS/SI/NF',
  },
  {
    id: 'H-002',
    date: `Day ${CONFLICT_DAY - 2} · 09:00Z`,
    theater: 'IRAQ / IRAN BORDER',
    source: 'MANTIS-HUMINT-3 (B/2)',
    reliability: 'B',
    credibility: '2',
    summary:
      'Source — Iranian border crossing official — reports unusual volume of IRGC military-age males transiting from Iran to Iraq via Mehran crossing on Days 16–17 (estimated 80–120 individuals in civilian clothing). Possible Quds Force pre-positioning for proxy operations.',
    actionable: true,
    classification: 'TS/NF',
  },
  {
    id: 'H-003',
    date: `Day ${CONFLICT_DAY - 2} · 14:00Z`,
    theater: 'QESHM ISLAND',
    source: 'MANTIS-HUMINT-9 (B/3)',
    reliability: 'B',
    credibility: '3',
    summary:
      'Source — Qeshm Island civilian — observed Shahed-136 airframes on hardstand at military restricted area northwest of Qeshm civilian airport. Estimated 40–60 airframes, some covered with camouflage netting. Activity level elevated Day 22 vs prior week.',
    actionable: true,
    classification: 'SECRET',
  },
  {
    id: 'H-004',
    date: `Day ${CONFLICT_DAY - 3} · 06:00Z`,
    theater: 'TEHRAN',
    source: 'ATLAS-HUMINT-2 (A/1)',
    reliability: 'A',
    credibility: '1',
    summary:
      'Source with access to IRGC senior staff — reports IRGC hardliner commanders (3 named) publicly rejected ceasefire terms on Day 50. New Supreme Leader Mojtaba Khamenei overruled them in an extraordinary SNSC session. Source assesses new SL is consolidating authority but hardliner bloc remains capable of independent action. COMPASS ceasefire stability: 91%/72h, 84%/7-day. Risk of hardliner-sponsored provocation assessed 15% within 7 days.',
    actionable: true,
    classification: 'TS/SI/NF',
  },
]

// ── IMINT reports ─────────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const IMINT: ImintReport[] = [
  {
    id: 'I-001',
    date: `Day ${CONFLICT_DAY - 1} · 03:45Z`,
    sensor: 'NRO KH-13 + Capella SAR',
    target: 'Qeshm Island Drone Depot',
    coordinates: '26.59°N / 55.93°E',
    finding:
      '50–60 Shahed-136 airframes on hardstand in pre-arm configuration. 14 IRGCN FAC fuelled and armed at adjacent naval pier. 3× flatbed trucks with payload consistent with C-802 anti-ship missile reloads.',
    conf: 'HIGH',
    classification: 'TS/NF',
  },
  {
    id: 'I-002',
    date: `Day ${CONFLICT_DAY - 1} · 16:00Z`,
    sensor: 'Maxar WorldView-3',
    target: 'Imam Ali Missile Base, Khorramabad',
    coordinates: '33.5°N / 48.4°E',
    finding:
      '4 × Emad TELs in dispersed hide configuration. Fuel bowser convoy (6 vehicles) in trail on Route 7 heading SW. Engineering activity at previously identified camouflaged re-entry vehicle storage bunker. Pre-launch indicators confirmed.',
    conf: 'HIGH',
    classification: 'TS/NF',
  },
  {
    id: 'I-003',
    date: `Day ${CONFLICT_DAY - 2} · 08:00Z`,
    sensor: 'ICEYE SAR (commercial)',
    target: 'Natanz FEP Post-Strike BDA',
    coordinates: '33.72°N / 51.73°E',
    finding:
      'Fuel Enrichment Plant Hall A: complete roof collapse confirmed. Hall B: partial structural damage, centrifuge cascade destruction assessed at 70–80%. Crater signatures from GBU-57A/B MOP confirmed. Iranian repair activity (earthmovers x4) ongoing — debris clearance only, no reconstruction.',
    conf: 'HIGH',
    classification: 'TS/NF',
  },
  {
    id: 'I-004',
    date: `Day ${CONFLICT_DAY - 1} · 10:00Z`,
    sensor: 'EP-3E ELINT + P-8A Radar',
    target: 'Strait of Hormuz — Mine Threat',
    coordinates: '26.1°N / 56.5°E',
    finding:
      'GOLF-7 (Fateh-class) tracked returning to Bandar Abbas on Day 26 — confirmed INACTIVE. MCM forces completed ZB-Alpha corridor clearance on Day 35 (100% cleared, 22 mines total). First unescorted commercial VLCC transit confirmed D35. GOLF-8 last located Bandar-e-Jask D17; subsequent movement unconfirmed; assessed in port consistent with ceasefire standdown. No new mine-laying activity since Day 24. Hormuz transit now operating at pre-conflict commercial capacity (Brent $76/bbl).',
    conf: 'HIGH',
    classification: 'TS/NF',
  },
]

// ── Sub-components ─────────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function StreamStatusBadge({ status }: { status: StreamStatus }) {
  const cfg: Record<StreamStatus, string> = {
    ACTIVE:       'bg-emerald-950/40 border-emerald-700 text-emerald-400',
    DEGRADED:     'bg-amber-950/30  border-amber-700  text-amber-400',
    INTERMITTENT: 'bg-yellow-950/20 border-yellow-700 text-yellow-400',
    OFFLINE:      'bg-red-950/30    border-red-700    text-red-400',
  }
  const dot: Record<StreamStatus, string> = {
    ACTIVE: 'bg-emerald-400 animate-pulse',
    DEGRADED: 'bg-amber-400',
    INTERMITTENT: 'bg-yellow-400',
    OFFLINE: 'bg-red-400',
  }
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm uppercase', cfg[status])}>
      <span className={cn('inline-block w-1.5 h-1.5 rounded-full shrink-0', dot[status])} />
      {status}
    </span>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ConfBadge({ conf }: { conf: ConfLevel }) {
  const cfg = { HIGH: 'text-emerald-400', MEDIUM: 'text-yellow-400', LOW: 'text-zinc-500' }
  const Icon = conf === 'HIGH' ? CheckCircle2 : conf === 'MEDIUM' ? MinusCircle : XCircle
  return (
    <span className={cn('inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider', cfg[conf])}>
      <Icon size={9} />{conf}
    </span>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ClassBadge({ cls }: { cls: ReportClass }) {
  const cfg: Record<ReportClass, string> = {
    'TS/SI/NF': 'text-red-500 border-red-900',
    'TS/NF':    'text-orange-500 border-orange-900',
    'SECRET':   'text-amber-500 border-amber-900',
    'UNCLASS':  'text-zinc-500 border-zinc-700',
  }
  return (
    <span className={cn('px-1.5 py-0.5 text-[8px] font-bold tracking-widest border rounded-sm', cfg[cls])}>
      {cls}
    </span>
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ReliabilityBadge({ r, c }: { r: HumintReport['reliability']; c: HumintReport['credibility'] }) {
  const rDesc: Record<HumintReport['reliability'], string> = { A: 'Completely Reliable', B: 'Usually Reliable', C: 'Fairly Reliable', D: 'Not Usually Reliable' }
  const cDesc: Record<HumintReport['credibility'], string> = { '1': 'Confirmed', '2': 'Probably True', '3': 'Possibly True', '4': 'Doubtfully True' }
  return (
    <span className="inline-flex items-center gap-1 text-[9px] text-amber-400 font-bold" title={`Source: ${rDesc[r]} / ${cDesc[c]}`}>
      {r}/{c}
    </span>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function IntelPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>
}) {
  const params: Record<string, string | string[] | undefined> =
    await (searchParams ?? Promise.resolve({} as Record<string, string | string[] | undefined>))
  const theaterFilter = typeof params.theater === 'string' ? params.theater : null

  // Live intel count from Supabase for header tiles
  let liveCount = 0
  let theaterCount = 0
  try {
    const sb = await createServerClient()
    if (sb) {
      const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
      const { count } = await sb
        .from('intel')
        .select('*', { count: 'exact', head: true })
        .gte('created_at', since)
      const { data: theaters } = await sb
        .from('intel')
        .select('theater')
        .gte('created_at', since)
      liveCount = count ?? 0
      theaterCount = new Set((theaters ?? []).map((r: { theater: string }) => r.theater)).size
    }
  } catch { /* non-fatal */ }

  return (
    <div className="space-y-5 max-w-screen-xl">

      {/* Classification banner — cinematic */}
      <div className="bg-red-950/60 border border-red-700 rounded px-4 py-1.5 flex items-center justify-between relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(90deg, transparent, rgba(239,68,68,0.04), transparent)', animation: 'studio-sweep 4s linear infinite'}} />
        <div className="flex items-center gap-2 relative z-[1]">
          <Lock size={10} className="text-red-400 drop-shadow-[0_0_4px_rgba(239,68,68,0.5)]" />
          <span className="text-[9px] font-bold tracking-[0.25em] text-red-400 uppercase">
            TOP SECRET // SI // NOFORN — AUTHORIZED RECIPIENTS ONLY
          </span>
        </div>
        <span className="text-[9px] text-emerald-600 relative z-[1]">AI LIVE ANALYSIS — OPEN-SOURCE FUSED INTELLIGENCE</span>
      </div>

      {/* ── Cinematic Intel Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(16,185,129,0.012) 2px, rgba(16,185,129,0.012) 4px)'}} />
          <div className="relative z-[3] flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="relative">
                <Radio size={26} className="text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse" />
              </div>
              <div>
                <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                  Multi-INT Intelligence Dashboard — Day {CONFLICT_DAY} of Active Hostilities
                </p>
                <h1 className="text-lg font-bold tracking-widest text-emerald-400 glow-green uppercase">
                  MULTI-INT FUSION — {CONFLICT_DATE} · 5 COLLECTION STREAMS ACTIVE
                </h1>
                <p className="text-[10px] text-zinc-500 mt-1 leading-relaxed max-w-lg">
                  Fused intelligence from SIGINT, HUMINT, and IMINT streams. All intercepts are AI-synthesized from open-source reporting.
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <div className="on-air-badge inline-block bg-emerald-900/60 text-emerald-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-emerald-800/60">
                ● SIGINT LIVE
              </div>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: 'STREAMS', count: 5,            color: 'border-emerald-800 bg-emerald-950/20 text-emerald-400' },
                  { label: 'REPORTS', count: liveCount,    color: 'border-amber-800 bg-amber-950/20 text-amber-400' },
                  { label: 'THEATERS', count: theaterCount, color: 'border-sky-800 bg-sky-950/20 text-sky-400' },
                  { label: 'LIVE',    count: liveCount,    color: 'border-zinc-700 bg-zinc-900/30 text-zinc-300' },
                ].map(({ label, count, color }) => (
                  <div key={label} className={cn('tac-card data-card-glow border rounded-sm p-2.5 text-center', color)}>
                    <p className="text-xl font-bold tabular-nums">{count}</p>
                    <p className="text-[8px] tracking-widest uppercase">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" />
      </div>

      {/* Theater drilldown banner — shown when navigated from IntelProvenanceGraph */}
      {theaterFilter && (
        <div className="flex items-center justify-between px-4 py-2 rounded-sm border border-cyan-800/50 bg-cyan-950/20">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[9px] font-mono font-bold tracking-widest uppercase text-cyan-400">
              THEATER DRILLDOWN — {theaterFilter.toUpperCase()}
            </span>
            <span className="text-[8px] font-mono text-zinc-600">Filtered from Provenance Graph</span>
          </div>
          <a
            href="/dashboard/intel"
            className="text-[8px] font-mono text-zinc-500 hover:text-zinc-300 tracking-widest uppercase border border-zinc-800 rounded px-2 py-1 hover:border-zinc-600 transition-colors"
          >
            CLEAR FILTER
          </a>
        </div>
      )}

      {/* LIVE FUSED INTEL FEED — replaces static SIGINT/HUMINT/IMINT arrays */}
      <LiveIntelFeed limit={80} perGroup={5} pollMs={60_000} />

      {/* LIVE AI-ANALYZED INTEL FEED — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">NEXUS LIVE</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <Radio size={11} className="text-emerald-400 animate-pulse drop-shadow-[0_0_4px_rgba(16,185,129,0.4)]" />
          <span className="text-emerald-400 tracking-widest glow-green">LIVE INTEL FEED — NEXUS ANALYZED · FULLY CITED · 20 SOURCES</span>
          <span className="ml-auto text-[9px] font-mono text-zinc-500 normal-case font-normal">auto-refresh 90s · click to deep-analyze</span>
        </div>
        <LiveNewsBoard limit={30} warFilter={true} compact={false} />
        {/* Source distribution + provenance trust graph */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
          <SourceRadar limit={12} />
          <IntelProvenanceGraph limit={8} />
        </div>
      </div>

      {/* HERALD-3 IO monitor — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-purple-500/60 font-bold tracking-[0.2em]">IO MONITOR</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <Radio size={11} className="text-purple-400 animate-pulse drop-shadow-[0_0_4px_rgba(168,85,247,0.4)]" />
          <span className="text-purple-400 tracking-widest">HERALD-3 LIVE — IO / Disinformation Monitor</span>
          <span className="ml-auto text-[9px] font-mono text-zinc-500 normal-case font-normal">auto-refresh 5min</span>
        </div>
        <HeraldFeed limit={8} />
      </div>

      {/* Footer / classification */}
      <div className="bg-red-950/30 border border-red-900/50 rounded px-4 py-2">
        <p className="text-[9px] text-red-700 text-center tracking-widest">
          THIS IS AN AI-GENERATED OPEN-SOURCE INTELLIGENCE SYNTHESIS. ALL INTERCEPTS, SOURCES, AND REPORTS ARE DERIVED FROM PUBLICLY AVAILABLE INFORMATION.
          CLASSIFICATION MARKINGS REFLECT ASSESSED SENSITIVITY TIERS. NOT A USG INTELLIGENCE PRODUCT.
          SOURCES:{' '}
          <a href="https://www.nsa.gov/" target="_blank" rel="noopener noreferrer" className="text-red-600 hover:text-red-400">NSA.GOV</a>
          {' · '}
          <a href="https://www.dia.mil/" target="_blank" rel="noopener noreferrer" className="text-red-600 hover:text-red-400">DIA.MIL</a>
          {' · '}
          <a href="https://www.cisa.gov/" target="_blank" rel="noopener noreferrer" className="text-red-600 hover:text-red-400">CISA.GOV</a>
        </p>
      </div>

    </div>
  )
}
