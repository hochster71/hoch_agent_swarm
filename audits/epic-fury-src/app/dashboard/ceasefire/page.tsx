import {
  Scale,
  Clock,
  CheckCircle2,
  XCircle,
  MinusCircle,
  Globe,
  ExternalLink,
  AlertTriangle,
  Radio,
  Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toDateStr } from '@/lib/conflict-day'
import { OraclePanel } from '@/components/OraclePanel'
import { CompassPanel } from '@/components/CompassPanel'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'
import { ShareButton } from '@/components/ShareButton'

export const revalidate = 0
export const metadata = { title: 'Ceasefire & Diplomacy — Operation Epic Fury' }

const CONFLICT_DAY  = getConflictDay()
const CONFLICT_DATE = toDateStr(CONFLICT_DAY)

// ── Data ──────────────────────────────────────────────────────────────────────

type ChannelStatus = 'ACTIVE' | 'SUSPENDED' | 'OBSERVING' | 'DEADLOCKED' | 'REJECTED'

interface DipChannel {
  id: string
  mediator: string
  flag: string
  status: ChannelStatus
  lastContact: string
  summary: string
  latestDevelopment: string
  source: string
  sourceUrl: string
}

const CHANNELS: DipChannel[] = [
  {
    id: 'oman',
    mediator: 'Sultanate of Oman',
    flag: '🇴🇲',
    status: 'ACTIVE',
    lastContact: `Day 52 · 09:30Z`,
    summary:
      `Oman remained the primary back-channel conduit throughout the conflict and played a central role in the Abu Dhabi Framework talks (Day 28–30). Following the formal ceasefire agreement on Day 32, Oman's role shifted from negotiator to facilitator of implementation — coordinating the 96-hour standdown verification, Hormuz demining sequencing, and POW/detainee exchange logistics. On Day 52, Oman hosted the Phase 1 prisoner exchange in Muscat under ICRC supervision: 47 IRGC prisoners returned to Iran, 12 US/coalition personnel returned to US custody. Oman has offered to host Phase 2 POW talks and continues to serve as the preferred conduit between Washington and Tehran's new Supreme Leader Mojtaba Khamenei's office.`,
    latestDevelopment:
      `Day 52: POW/detainee Phase 1 complete — 47 IRGC + 12 coalition. Channel fully ACTIVE. Phase 2 logistics ongoing.`,
    source: 'Reuters / AP Diplomacy',
    sourceUrl: 'https://www.reuters.com/world/middle-east/',
  },
  {
    id: 'uae',
    mediator: 'UAE / Abu Dhabi — Crown Prince MbZ',
    flag: '🇦🇪',
    status: 'OBSERVING',
    lastContact: `Day 32 · 14:00Z`,
    summary:
      `UAE hosted the Abu Dhabi proximity talks (Days 27–30) that produced the 96-hour kinetic pause and the ceasefire framework text. Crown Prince MbZ served as principal facilitator, bridging the US NSC Deputy Principal and Iran's SNSC delegation in separate rooms. The Abu Dhabi Framework was signed on Day 30 and formalized into the Ceasefire Agreement on Day 32. Following signature, UAE transitioned from active host to observer role — monitoring framework implementation, supporting Hormuz commercial corridor restoration, and liaising on reconstruction finance. UAE sovereign wealth funds are positioned to participate in Iran reconstruction financing post-JCPOA resolution.`,
    latestDevelopment:
      `Day 32: Abu Dhabi Framework signed — UAE facilitation complete. Now OBSERVING ceasefire implementation.`,
    source: 'Reuters / BBC Diplomacy',
    sourceUrl: 'https://www.reuters.com/world/middle-east/',
  },
  {
    id: 'qatar',
    mediator: 'State of Qatar / Al Udeid',
    flag: '🇶🇦',
    status: 'ACTIVE',
    lastContact: 'Day 48 · Geneva',
    summary:
      'Qatar\'s mediation role was suspended after Day 13\'s Iranian ballistic missile strike on Al Udeid AB. Following the Day 32 ceasefire, Qatar normalised its diplomatic posture toward Iran and re-entered the multilateral track. Qatar is participating in the Geneva post-conflict reconstruction talks as a co-host alongside Switzerland (from Day 48), with Qatari investment commitments under discussion. Al Udeid Air Base remains fully operational. The Qatari FM met with Iran\'s new FM (appointed by SL Mojtaba) on Day 47 — the first direct Qatari-Iranian ministerial contact since Day 13. Qatar is assessed as an important bridge to Tehran\'s new leadership given its established relationship with Islamic governance frameworks.',
    latestDevelopment:
      'Day 48: Qatar co-hosting Geneva reconstruction talks. FM-to-FM contact with Iran restored. Channel ACTIVE.',
    source: 'Reuters',
    sourceUrl: 'https://www.reuters.com/world/middle-east/',
  },
  {
    id: 'switzerland',
    mediator: 'Switzerland / US Interests Section',
    flag: '🇨🇭',
    status: 'ACTIVE',
    lastContact: 'Day 48 · Geneva',
    summary:
      'Switzerland, which hosts the US Interests Section in Tehran, transmitted the initial US Diplomatic Note to Tehran on Day 10 and deployed a senior FDFA diplomat to Muscat to support the Omani channel. Following the Day 32 ceasefire, Switzerland offered Geneva as a venue for post-conflict reconstruction and JCPOA-replacement framework talks — accepted by both sides on Day 46. The Geneva talks opened on Day 48 with a working group on sanctions relief, reconstruction finance, and a framework for nuclear transparency monitoring to replace the original JCPOA. Switzerland is also coordinating with IAEA on the inspection verification protocol. The Swiss FDFA role has substantially expanded from message conduit to active treaty-framework host.',
    latestDevelopment:
      'Day 48: Geneva post-conflict talks open. JCPOA replacement + sanctions framework under discussion. ACTIVE.',
    source: 'Swiss FDFA',
    sourceUrl: 'https://www.eda.admin.ch/eda/en/fdfa/the-fdfa/political-divisions.html',
  },
  {
    id: 'un',
    mediator: 'United Nations Security Council',
    flag: '🇺🇳',
    status: 'ACTIVE',
    lastContact: 'Day 54 · UNSCR 2751 Monitoring',
    summary:
      'The UNSC passed three resolutions relevant to this conflict: UNSCR 2731 (Day 25, humanitarian corridor), UNSCR 2748 (Day 32, ceasefire monitoring force, unanimous 15-0), and UNSCR 2751 (Day 44, IAEA access restoration mandate, 14-0-1). A UN ceasefire monitoring mission (UNCMM) was deployed under UNSCR 2748 with 340 military observers from neutral nations. UNCMM is currently operating from Muscat and monitoring the Iran-Iraq border zone, Strait of Hormuz approaches, and designated stand-down areas. IAEA coordination under UNSCR 2751 continues — Natanz and Isfahan assessments complete; Fordow access still under negotiation. SG Guterres has offered UN facilitation for Fordow access talks.',
    latestDevelopment:
      'Day 54: UNCMM monitoring Phase 2 ACTIVE. UNSCR 2751 IAEA implementation ongoing. Fordow access pending.',
    source: 'UN Security Council',
    sourceUrl: 'https://www.un.org/securitycouncil/',
  },
]

// ── Iran's 7 ceasefire conditions vs US position ─────────────────────────────

interface ConditionRow {
  no: number
  iranCondition: string
  usPosition: 'REJECTED' | 'PARTIAL' | 'OPEN'
  usDetail: string
}

const CONDITIONS: ConditionRow[] = [
  {
    no: 1,
    iranCondition: 'Immediate and unconditional cessation of all US/Israeli military operations against Iran.',
    usPosition: 'PARTIAL',
    usDetail: 'US willing to discuss tactical pause — not unconditional cessation. Conditions include IRGCN stand-down.',
  },
  {
    no: 2,
    iranCondition: 'Full withdrawal of all US forward-deployed forces from Qatar, Bahrain, UAE, and Kuwait.',
    usPosition: 'PARTIAL',
    usDetail: 'Iran DROPPED this precondition Day 26. US committed to GCC per AUMF — long-term posture TBD in post-conflict framework.',
  },
  {
    no: 3,
    iranCondition: 'Unconditional lifting of all post-Day 1 sanctions and restoration of Iranian oil export access.',
    usPosition: 'REJECTED',
    usDetail: 'No sanctions relief pre-ceasefire. Post-ceasefire enforcement compliance required first.',
  },
  {
    no: 4,
    iranCondition: 'International investigation into Israeli nuclear and industrial strikes on Iranian soil.',
    usPosition: 'PARTIAL',
    usDetail: 'US does not object to post-conflict international review — but cannot commit to outcomes.',
  },
  {
    no: 5,
    iranCondition: 'Release of 47 IRGC prisoners captured in coalition special operations actions Days 1–18.',
    usPosition: 'OPEN',
    usDetail: 'Open to humanitarian/POW exchanges as part of a credible ceasefire package. Under Oman channel.',
  },
  {
    no: 6,
    iranCondition: 'IAEA access rights suspended — Iran retains right to reconstitute nuclear program.',
    usPosition: 'REJECTED',
    usDetail: 'Non-starter. Any ceasefire agreement must include IAEA monitoring restoration and enrichment cap.',
  },
  {
    no: 7,
    iranCondition: 'Formal US acknowledgement that Iran has the right to regional deterrence posture and proxy forces.',
    usPosition: 'REJECTED',
    usDetail: 'Flatly rejected. US will not formally recognise IRGC proxy network legitimacy in any ceasefire text.',
  },
]

// ── Diplomatic event timeline (chronological) ────────────────────────────────

interface DipEvent {
  day: number
  date: string
  actor: string
  event: string
  outcome: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'
}

const TIMELINE: DipEvent[] = [
  { day: 1,  date: '01 MAR 2026', actor: 'UN Sec-Gen',        event: 'Guterres calls for "immediate de-escalation" — ignored by both parties.', outcome: 'NEUTRAL' },
  { day: 3,  date: '03 MAR 2026', actor: 'Oman',              event: 'Oman offers back-channel mediation. Tehran accepts, Washington cautiously responds.', outcome: 'POSITIVE' },
  { day: 4,  date: '04 MAR 2026', actor: 'UNSC',              event: 'Emergency UNSC session. UK/France/US resolution fails — Russia/China veto.', outcome: 'NEGATIVE' },
  { day: 6,  date: '06 MAR 2026', actor: 'Iran / Oman',       event: 'Iran transmits 7-point ceasefire demand to Oman for forwarding to US.', outcome: 'NEUTRAL' },
  { day: 8,  date: '08 MAR 2026', actor: 'UNSC',              event: '2nd UNSC emergency session. Russian-drafted resolution vetoed by US/UK/France.', outcome: 'NEGATIVE' },
  { day: 10, date: '10 MAR 2026', actor: 'Switzerland',       event: 'Swiss FDFA transmits US Diplomatic Note to Tehran via Interests Section.', outcome: 'NEUTRAL' },
  { day: 12, date: '12 MAR 2026', actor: 'Iran / Switzerland', event: 'Iran rejects US note as "legally insufficient." Bern deploys diplomat to Muscat.', outcome: 'NEGATIVE' },
  { day: 14, date: '14 MAR 2026', actor: 'UNSC',              event: '3rd UNSC session — 2nd Russia/China veto on G7 resolution. France proposes corridor.', outcome: 'NEGATIVE' },
  { day: 15, date: '15 MAR 2026', actor: 'Qatar',             event: 'Qatar suspends mediation after Al Udeid BM strike. Lodges protest with Tehran.', outcome: 'NEGATIVE' },
  { day: 18, date: '18 MAR 2026', actor: 'Oman / US',         event: 'Non-paper on humanitarian pause drafted in Muscat. Under US review — no response.', outcome: 'POSITIVE' },
  { day: 18, date: '18 MAR 2026', actor: 'US SecState',       event: 'US formally rejects Iran\'s Condition 2 (Gulf force withdrawal). No ceasefire imminent.', outcome: 'NEGATIVE' },
  { day: 18, date: '18 MAR 2026', actor: 'Qatar FM',          event: 'Qatar signals willingness to resume if Iran acknowledges Al Udeid strike.', outcome: 'POSITIVE' },
  { day: 22, date: '22 MAR 2026', actor: 'US / IRGC',         event: 'Supreme Leader Khamenei KIA — IRGC CINC Salami assumes joint war authority. FPCON DELTA.', outcome: 'NEGATIVE' },
  { day: 24, date: '24 MAR 2026', actor: 'Iran / Oman',       event: 'Iran withdraws from Oman channel following Day 24 IRGCAF ballistic missile barrage.', outcome: 'NEGATIVE' },
  { day: 25, date: '25 MAR 2026', actor: 'UNSC',              event: 'UNSCR 2731 passed 14-1 (Russia veto) — humanitarian corridor. Ceasefire resolution fails 3rd veto.', outcome: 'NEUTRAL' },
  { day: 26, date: '26 MAR 2026', actor: 'Iran SNSC',         event: 'Iran drops US withdrawal precondition. Oman channel REACTIVATED. Abu Dhabi proximity talks arranged.', outcome: 'POSITIVE' },
  { day: 27, date: '27 MAR 2026', actor: 'UAE / POTUS',       event: 'Abu Dhabi proximity talks begin. POTUS confirms ceasefire framework in national address.', outcome: 'POSITIVE' },
  { day: 28, date: '28 MAR 2026', actor: 'US / Iran',          event: '96-hour kinetic pause framework begins — both sides confirm military stand-down. IRGCN returns to port.', outcome: 'POSITIVE' },
  { day: 30, date: '30 MAR 2026', actor: 'US SecState / Iran', event: 'Abu Dhabi Framework text agreed. 96h pause, humanitarian exchange schedule, Hormuz demining sequencing table.', outcome: 'POSITIVE' },
  { day: 32, date: '01 APR 2026', actor: 'UN / US / Iran',     event: 'Formal Ceasefire Agreement signed. All offensive operations ceased. UNSC notified. MCM corridor ops expand.', outcome: 'POSITIVE' },
  { day: 35, date: '04 APR 2026', actor: 'CTF-3 / IRGCN',     event: 'Hormuz MCM corridor ZB-Alpha 100% cleared. First unescorted commercial VLCC transit under ceasefire terms.', outcome: 'POSITIVE' },
  { day: 39, date: '08 APR 2026', actor: 'Iran AoE',           event: 'Mojtaba Khamenei nominated as new Supreme Leader candidate. IRGC hardliner faction signals opposition.', outcome: 'NEGATIVE' },
  { day: 40, date: '09 APR 2026', actor: 'Iran',               event: 'Mojtaba Khamenei confirmed as new Supreme Leader (51-41 AoE vote). US/EU express concern over succession.', outcome: 'NEGATIVE' },
  { day: 44, date: '13 APR 2026', actor: 'Iran / IAEA',        event: 'First IAEA inspection team enters Iran — Natanz + Isfahan assessed under ceasefire terms. Fordow access pending.', outcome: 'POSITIVE' },
  { day: 48, date: '17 APR 2026', actor: 'US / Iran',          event: 'Post-conflict reconstruction talks open in Geneva. JCPOA replacement framework discussions begin. Brent $76/bbl.', outcome: 'POSITIVE' },
  { day: 50, date: '19 APR 2026', actor: 'IRGC hardliners',   event: 'Three IRGC commanders publicly reject ceasefire terms. New SL Mojtaba overrules — IRGC command tension elevated.', outcome: 'NEGATIVE' },
  { day: 52, date: '21 APR 2026', actor: 'Oman / ICRC',        event: 'POW/detainee exchange Phase 1 complete — 47 IRGC prisoners, 12 coalition personnel. ICRC supervised.', outcome: 'POSITIVE' },
  { day: 54, date: '23 APR 2026', actor: 'CENTCOM / IAEA',     event: 'Ceasefire monitoring Phase 2 underway. IAEA Fordow access still pending. IRGC hardliner watch ACTIVE.', outcome: 'NEUTRAL' },
]

// ── UNSC Vote History ─────────────────────────────────────────────────────────

const UNSC_VOTES = [
  { day: 4,  date: '04 MAR 2026', resolution: 'UK/FR/US — Ceasefire + IAEA access', y: 10, n: 2, abs: 3, result: 'VETOED' as const },
  { day: 8,  date: '08 MAR 2026', resolution: 'RU-drafted — Unconditional ceasefire, US withdrawal demand', y: 4, n: 3, abs: 8, result: 'VETOED' as const },
  { day: 14, date: '14 MAR 2026', resolution: 'G7 — Ceasefire, humanitarian corridors', y: 11, n: 2, abs: 2, result: 'VETOED' as const },
  { day: 25, date: '25 MAR 2026', resolution: 'FR-sponsored full ceasefire resolution', y: 9, n: 3, abs: 3, result: 'VETOED' as const },
  { day: 25, date: '25 MAR 2026', resolution: 'UNSCR 2731 — Humanitarian corridor (US abstains)', y: 14, n: 1, abs: 0, result: 'PASSED' as const },
  { day: 32, date: '01 APR 2026', resolution: 'UNSCR 2748 — Ceasefire monitoring force (unanimous)', y: 15, n: 0, abs: 0, result: 'PASSED' as const },
  { day: 44, date: '13 APR 2026', resolution: 'UNSCR 2751 — IAEA access restoration mandate', y: 14, n: 0, abs: 1, result: 'PASSED' as const },
]

// ── Probability gauge ─────────────────────────────────────────────────────────

const CEASE_PROBABILITIES = [
  { horizon: '72h',  pct: 91, label: 'Ceasefire stable (72h)' },
  { horizon: '7d',   pct: 84, label: 'Framework holding (7 days)' },
  { horizon: '30d',  pct: 67, label: 'Post-conflict deal (30 days)' },
  { horizon: '90d',  pct: 48, label: 'Durable peace (90 days)' },
]

// ── Sub-components ────────────────────────────────────────────────────────────

function ChannelStatusBadge({ status }: { status: ChannelStatus }) {
  const cfg: Record<ChannelStatus, string> = {
    ACTIVE:      'bg-emerald-950/40 border-emerald-700 text-emerald-400',
    SUSPENDED:   'bg-amber-950/30  border-amber-700  text-amber-400',
    OBSERVING:   'bg-sky-950/20    border-sky-700    text-sky-400',
    DEADLOCKED:  'bg-red-950/30    border-red-700    text-red-400',
    REJECTED:    'bg-zinc-800      border-zinc-600   text-zinc-400',
  }
  const icon: Record<ChannelStatus, React.ReactNode> = {
    ACTIVE:     <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1" />,
    SUSPENDED:  <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 mr-1" />,
    OBSERVING:  <span className="inline-block w-1.5 h-1.5 rounded-full bg-sky-400 mr-1" />,
    DEADLOCKED: <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-400 mr-1" />,
    REJECTED:   <span className="inline-block w-1.5 h-1.5 rounded-full bg-zinc-400 mr-1" />,
  }
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm uppercase', cfg[status])}>
      {icon[status]}{status}
    </span>
  )
}

function PositionBadge({ pos }: { pos: ConditionRow['usPosition'] }) {
  const cfg = {
    REJECTED: 'text-red-400 border-red-800 bg-red-950/30',
    PARTIAL:  'text-yellow-400 border-yellow-800 bg-yellow-950/20',
    OPEN:     'text-emerald-400 border-emerald-800 bg-emerald-950/20',
  }[pos]
  const Icon = pos === 'REJECTED' ? XCircle : pos === 'PARTIAL' ? MinusCircle : CheckCircle2
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm uppercase', cfg)}>
      <Icon size={9} /> {pos}
    </span>
  )
}

function outcomeColor(o: DipEvent['outcome']) {
  return o === 'POSITIVE' ? 'bg-emerald-500' : o === 'NEGATIVE' ? 'bg-red-500' : 'bg-zinc-500'
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CeasefirePage() {
  const activeCount    = CHANNELS.filter((c) => c.status === 'ACTIVE').length
  const suspendedCount = CHANNELS.filter((c) => c.status === 'SUSPENDED').length
  const deadlockedCount = CHANNELS.filter((c) => c.status === 'DEADLOCKED').length

  return (
    <div className="space-y-5 max-w-screen-xl">

      {/* Live diplomatic & ceasefire intel feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TheaterIntelFeed theater="Diplomatic" limit={12} />
        <LiveNewsBoard limit={15} warFilter={false} compact={false} />
      </div>

      {/* ── Cinematic Ceasefire Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(59,130,246,0.012) 2px, rgba(59,130,246,0.012) 4px)'}} />
          <div className="relative z-[3] flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="relative">
                <Scale size={26} className="text-blue-400 drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-blue-400 rounded-full animate-pulse" />
              </div>
              <div>
                <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                  Diplomatic Operations Center — Day {CONFLICT_DAY} Situation Report
                </p>
                <h1 className="text-lg font-bold tracking-widest text-blue-400 glow-blue uppercase">
                  CEASEFIRE & DIPLOMACY — {CONFLICT_DATE}
                </h1>
                <p className="text-[10px] text-zinc-500 mt-1 leading-relaxed max-w-lg">
                  Real-time status of all active diplomatic channels, ceasefire negotiations, UN Security Council proceedings,
                  and ORACLE-9 probabilistic ceasefire outlook.
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <div className="on-air-badge inline-block bg-blue-900/60 text-blue-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-blue-800/60">
                ● DIPLO LIVE
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Active', count: activeCount,     color: 'border-emerald-800 bg-emerald-950/20 text-emerald-400' },
                  { label: 'Suspended', count: suspendedCount, color: 'border-amber-800 bg-amber-950/20 text-amber-400' },
                  { label: 'Deadlocked', count: deadlockedCount, color: 'border-red-800 bg-red-950/20 text-red-400' },
                ].map(({ label, count, color }) => (
                  <div key={label} className={cn('tac-card data-card-glow border rounded-sm p-2.5 text-center', color)}>
                    <p className="text-xl font-bold tabular-nums">{count}</p>
                    <p className="text-[8px] tracking-widest uppercase">{label}</p>
                  </div>
                ))}
              </div>
              <ShareButton
                title="Ceasefire &amp; Diplomacy — Epic Fury Dashboard"
                text={`Day ${CONFLICT_DAY}: Ceasefire probability 72h=${CEASE_PROBABILITIES[0].pct}%. Track all diplomatic channels live.`}
              />
            </div>
          </div>
        </div>
        <div className="h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent" style={{animation: 'bar-slide 1s ease forwards'}} />
      </div>

      {/* PEACE-O-METER + ORACLE-9 Ceasefire probability — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-4 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-blue-500/60 font-bold tracking-[0.2em]">ORACLE-9</span>
        </div>
        <div className="tac-section-header mb-1 relative z-[1]">
          <Shield size={11} className="text-blue-400 drop-shadow-[0_0_4px_rgba(59,130,246,0.4)]" />
          <span className="glow-blue">ORACLE-9 — Peace-O-Meter &amp; Ceasefire Probability (Day {CONFLICT_DAY})</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">Updated Day {CONFLICT_DAY} 06:30Z</span>
        </div>

        {/* Prominent 72-hour gauge */}
        <div className="flex items-center gap-6 border border-red-900/50 rounded bg-red-950/10 p-4">
          {/* SVG arc meter */}
          <div className="shrink-0 relative w-24 h-14 flex items-end justify-center">
            <svg width="96" height="56" viewBox="0 0 96 56" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Background arc */}
              <path d="M8 52 A 40 40 0 0 1 88 52" stroke="#27272a" strokeWidth="8" strokeLinecap="round" fill="none" />
              {/* Value arc — 8% of 180° ≈ endpoint (9,42) */}
              <path d="M8 52 A 40 40 0 0 1 9 42" stroke="#ef4444" strokeWidth="8" strokeLinecap="round" fill="none" />
            </svg>
            <div className="absolute bottom-0 left-0 right-0 text-center">
              <p className="text-2xl font-bold text-red-400 leading-none">{CEASE_PROBABILITIES[0].pct}%</p>
            </div>
          </div>
          <div>
            <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-1">PEACE-O-METER — 72-HOUR PROBABILITY</p>
            <p className="text-red-300 text-xs font-semibold">Ceasefire is UNLIKELY in the next 72 hours</p>
            <p className="text-[10px] text-zinc-400 mt-1 leading-relaxed max-w-sm">
              All diplomatic channels are below threshold. Iran&apos;s core demands remain unacceptable
              to the US. No emergency talks scheduled. ORACLE-9 confidence: HIGH.
            </p>
          </div>
        </div>

        {/* Horizon bars */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {CEASE_PROBABILITIES.map(({ horizon, pct, label }) => (
            <div key={horizon} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[9px] text-zinc-500 tracking-widest uppercase">{label}</span>
                <span className={cn(
                  'text-base font-bold tabular-nums',
                  pct < 15 ? 'text-red-400' : pct < 30 ? 'text-amber-400' : pct < 50 ? 'text-yellow-400' : 'text-sky-400'
                )}>{pct}%</span>
              </div>
              <div className="h-2 bg-zinc-800 rounded-sm overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-sm',
                    pct < 15 ? 'bg-red-600' : pct < 30 ? 'bg-amber-500' : pct < 50 ? 'bg-yellow-500' : 'bg-sky-500'
                  )}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Diplomatic channels — 2-col grid */}
      <div className="space-y-1">
        <div className="flex items-center gap-2 mb-2">
          <Globe size={11} className="text-blue-400" />
          <h2 className="text-[10px] font-bold tracking-widest text-zinc-400 uppercase">
            Active Diplomatic Channels — {CHANNELS.length} Total
          </h2>
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {CHANNELS.map((ch) => (
            <div key={ch.id} className="tac-card p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  <span className="text-xl leading-none">{ch.flag}</span>
                  <div>
                    <p className="text-sm font-bold text-zinc-100">{ch.mediator}</p>
                    <p className="text-[9px] text-zinc-600 tracking-wider">Last contact: {ch.lastContact}</p>
                  </div>
                </div>
                <ChannelStatusBadge status={ch.status} />
              </div>

              <p className="text-xs text-zinc-400 leading-relaxed">{ch.summary}</p>

              <div className="rounded bg-zinc-900/60 border border-zinc-800 px-3 py-2">
                <p className="text-[9px] font-bold tracking-widest text-blue-400 uppercase mb-1">Latest Development</p>
                <p className="text-[10px] text-zinc-300">{ch.latestDevelopment}</p>
              </div>

              <div className="flex items-center justify-end pt-1 border-t border-zinc-800">
                <a href={ch.sourceUrl} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[9px] text-emerald-700 hover:text-emerald-400 transition-colors">
                  <ExternalLink size={8} /> Source: {ch.source}
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Iran 7-point demands vs US position */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <AlertTriangle size={11} className="text-amber-400" />
          <span>Iran 7-Point Ceasefire Conditions — US Position (Day {CONFLICT_DAY})</span>
          <span className="ml-auto text-[9px] text-zinc-600 normal-case tracking-normal font-normal">Source: Oman back-channel / Reuters / State Dept</span>
        </div>
        <div className="space-y-2">
          {CONDITIONS.map((c) => (
            <div key={c.no} className="grid grid-cols-[auto_1fr_auto] gap-3 items-start py-2.5 border-b border-zinc-800/60 last:border-0">
              <span className="text-lg font-bold text-zinc-600 tabular-nums w-5 text-center">{c.no}</span>
              <div className="space-y-1">
                <p className="text-xs text-zinc-300 leading-relaxed">{c.iranCondition}</p>
                <p className="text-[10px] text-zinc-500 leading-relaxed">{c.usDetail}</p>
              </div>
              <div className="shrink-0 pt-0.5">
                <PositionBadge pos={c.usPosition} />
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 pt-1">
          {[
            { pos: 'REJECTED' as const, label: 'US Rejected' },
            { pos: 'PARTIAL'  as const, label: 'US Partial' },
            { pos: 'OPEN'     as const, label: 'US Open' },
          ].map(({ pos, label }) => (
            <div key={pos} className="flex items-center gap-1.5">
              <PositionBadge pos={pos} />
              <span className="text-[9px] text-zinc-600">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* UNSC vote history */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Radio size={11} className="text-red-400" />
          <span>UN Security Council — Vote History</span>
        </div>
        <div className="space-y-2">
          {UNSC_VOTES.map((v) => (
            <div key={v.day} className="tac-card p-3 border-red-900/40 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3">
              <div>
                <p className="text-[9px] text-zinc-600 tracking-wider mb-0.5">Day {v.day} · {v.date}</p>
                <p className="text-xs text-zinc-200">{v.resolution}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <div className="flex gap-3 text-[10px] tabular-nums">
                  <span className="text-emerald-400 font-bold">Y:{v.y}</span>
                  <span className="text-red-400 font-bold">N:{v.n}</span>
                  <span className="text-zinc-500 font-bold">A:{v.abs}</span>
                </div>
                <span className={`px-2 py-0.5 text-[9px] font-bold tracking-widest border rounded-sm uppercase ${v.result === 'PASSED' ? 'border-emerald-700 bg-emerald-950/40 text-emerald-400' : 'border-red-700 bg-red-950/40 text-red-400'}`}>
                  {v.result}
                </span>
              </div>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-600">
          Four ceasefire resolutions vetoed. UNSCR 2731 humanitarian corridor passed Day 25 (Russia veto on separate full ceasefire). US abstained on UNSCR 2731 as de-escalation signal. Abu Dhabi proximity talks now active.{' '}
          <a href="https://www.un.org/securitycouncil/" target="_blank" rel="noopener noreferrer"
            className="text-emerald-700 hover:text-emerald-400 transition-colors inline-flex items-center gap-1">
            <ExternalLink size={8} /> UN Security Council
          </a>
        </p>
      </div>

      {/* Diplomatic timeline */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Clock size={11} className="text-blue-400" />
          <span>Diplomatic Event Timeline — Days 1–{CONFLICT_DAY}</span>
        </div>
        <div className="relative pl-6 space-y-0">
          {/* Vertical connector line */}
          <div className="absolute left-[5px] top-2 bottom-2 w-px bg-zinc-800" />
          {TIMELINE.map((ev, i) => (
            <div key={i} className="relative flex gap-3 pb-4">
              {/* Dot */}
              <div className={cn('absolute left-[-17px] top-1.5 w-2.5 h-2.5 rounded-full border border-zinc-900', outcomeColor(ev.outcome))} />
              <div className="space-y-0.5 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[9px] text-zinc-600 tracking-wider">{ev.date}</span>
                  <span className="text-[9px] font-bold text-zinc-400 tracking-wider">{ev.actor}</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">{ev.event}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ORACLE-9 + COMPASS live ceasefire outlook — cinematic */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="tac-card tac-card-critical p-4 space-y-3 relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(239,68,68,0.03) 0%, transparent 50%)'}} />
          <div className="tac-section-header mb-1 relative z-[1]">
            <AlertTriangle size={11} className="text-amber-400 animate-pulse drop-shadow-[0_0_6px_rgba(245,158,11,0.5)]" />
            <span className="text-amber-400 tracking-widest glow-amber">ORACLE-9 LIVE — Escalation Probabilities</span>
            <span className="ml-auto text-[9px] font-mono text-zinc-500 normal-case font-normal">auto-refresh 30s</span>
          </div>
          <OraclePanel />
        </div>
        <div className="tac-card p-4 space-y-3 relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(234,179,8,0.02) 0%, transparent 50%)'}} />
          <div className="tac-section-header mb-1 relative z-[1]">
            <Globe size={11} className="text-yellow-400 animate-pulse drop-shadow-[0_0_4px_rgba(234,179,8,0.4)]" />
            <span className="text-yellow-400 tracking-widest">COMPASS LIVE — Economic Pressure Index</span>
            <span className="ml-auto text-[9px] font-mono text-zinc-500 normal-case font-normal">auto-refresh 60s</span>
          </div>
          <CompassPanel />
        </div>
      </div>

      {/* Expert analysis */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header mb-1">
          <Scale size={11} className="text-zinc-500" />
          <span>Expert Analysis — Day {CONFLICT_DAY} Diplomatic Outlook</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              expert: 'Rear Adm. (ret.) John Kirby',
              affiliation: 'CNAS Fellow / Former NSC Coordinator',
              quote:
                '"The Oman channel is the only credible thread. Iran\'s precondition on Gulf force withdrawal is not a negotiating position — it\'s a demand for strategic surrender. That\'s not something any US administration can accept. We\'re looking at weeks, not days, before conditions exist for even a humanitarian pause."',
              source: 'CBS News Face the Nation',
              sourceUrl: 'https://www.cbsnews.com/news/face-the-nation/',
            },
            {
              expert: 'Vali Nasr',
              affiliation: 'Johns Hopkins SAIS / Former State Dept Senior Adviser',
              quote:
                '"Iran is in a fundamentally different position than in previous crises. The regime is negotiating from what it perceives as a position of demonstrated resolve — its three missile barrages have imposed real costs. Tehran believes time and economic pressure serves its interests. The US needs a face-saving off-ramp as much as Iran does."',
              source: 'Foreign Affairs',
              sourceUrl: 'https://www.foreignaffairs.com/',
            },
          ].map(({ expert, affiliation, quote, source, sourceUrl }) => (
            <div key={expert} className="space-y-2 rounded border border-zinc-800 bg-zinc-900/40 p-3">
              <div>
                <p className="text-xs font-bold text-zinc-200">{expert}</p>
                <p className="text-[9px] text-zinc-500 tracking-wider">{affiliation}</p>
              </div>
              <p className="text-[10px] text-zinc-400 leading-relaxed italic">{quote}</p>
              <a href={sourceUrl} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1 text-[9px] text-emerald-700 hover:text-emerald-400 transition-colors">
                <ExternalLink size={8} /> {source}
              </a>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
