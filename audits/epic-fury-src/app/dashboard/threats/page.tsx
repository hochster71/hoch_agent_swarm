import {
  Activity,
  TrendingUp,
  Shield,
  Zap,
  Radio,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toDateStr, toShortDate } from '@/lib/conflict-day'
import { OraclePanel } from '@/components/OraclePanel'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'

export const revalidate = 0
export const metadata = { title: 'ORACLE-9 Threat Assessment — Operation Epic Fury' }

const CONFLICT_DAY  = getConflictDay()
const CONFLICT_DATE = toDateStr(CONFLICT_DAY)

// ── 20-day threat trajectory (daily snapshots for select domains) ────────────

interface TrajectoryPoint { day: number; bm: number; shahed: number; cyber: number }


const _REMOVED_THREATS = [
  {
    id: 'bm4',
    domain: 'Missiles',
    label: '4th Ballistic Missile Barrage',
    pct: 67,
    trend: 'UP',
    trendDelta: '+12%',
    horizon: '72h',
    severity: 'HIGH',
    assessmentText:
      'ORACLE-9 assesses 67% probability of a fourth major ballistic missile barrage within 72 hours, elevated from 34% on Day 18. SIGINT (TRIDENT) confirmed Supreme Leader → IRGC CINC command communications at 01:15Z Day 22 consistent with pre-strike authorisation. IMINT shows 6–8 TELs in dispersed deployment posture across Isfahan, Qom, and Kermanshah corridors. Iran has expended ~120–140 BMs of pre-conflict inventory; 80–110 Emad/Ghadr/Shahab assessed remaining. Third barrage targeted Al Udeid AB and Camp Arifjan on Day 17 — next barrage likely to increase salvo size to stress THAAD/PAC-3 magazine depth.',
    indicators: [
      'SIGINT: SL → IRGC CINC comm 01:15Z Day 22 — pre-strike auth pattern (TRIDENT)',
      'IMINT: 6–8 Emad/Ghadr TELs dispersed Isaiah / Qom / Kermanshah (Day 22 pass)',
      'HUMINT: Fuel and oxidiser trucks observed at Site F-7 Bijar (corroborated DoD)',
      'SIGINT: IRGCAF missile-unit radio discipline shift to COMSEC protocol Day 22',
      'OSINT: Al Udeid AB runway repair declared operational — potential re-target',
    ],
    sources: [
      { label: 'ISW Day 22 Assessment', url: 'https://www.understandingwar.org/' },
      { label: 'Reuters — Iran missiles', url: 'https://www.reuters.com/world/middle-east/' },
      { label: 'USNI News', url: 'https://news.usni.org/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 02:14Z`,
  },
  {
    id: 'shahed',
    domain: 'Air',
    label: 'Shahed-136/238 Swarm Attack',
    pct: 82,
    trend: 'UP',
    trendDelta: '+18%',
    horizon: '24h',
    severity: 'CRITICAL',
    assessmentText:
      'ORACLE-9 assesses 82% probability of a mass Shahed-136/238 drone swarm attack within 24 hours — elevated from 64% on Day 20. IMINT at 03:45Z Day 22 confirmed pre-arm activity at Qeshm Island drone storage depot and Bandar Abbas forward staging area. RSM identifies Shahed fuel bowser activity consistent with 50–80 airframe preparation. Attack vectors likely include: (1) northern Gulf arc → Kuwait / Qatar, (2) direct Strait axis → UAE coast, (3) southern arc → Saudi Aramco Abqaiq. C-RAM and SHORAD batteries across CTF-3 declared Winchester on Day 14 and are partially restocked.',
    indicators: [
      'IMINT: Qeshm Island pre-arm activity 03:45Z Day 22 (NRO / commercial SAR)',
      'IMINT: Bandar Abbas depot — 50+ airframes on hardstand (Day 20)',
      'SIGINT: IRGCN FAC grid update transmissions to Qeshm logistics (CERBERUS)',
      'OSINT: Crowd-sourced ADS-B gap ident — Qeshm IFR zone fully closed 0800Z',
      'HUMINT: Shahed launch crew pre-positioned east coast Hormuzgan (Day 20)',
    ],
    sources: [
      { label: 'Washington Post — Iran drones', url: 'https://www.washingtonpost.com/' },
      { label: 'Bellingcat OSINT', url: 'https://www.bellingcat.com/' },
      { label: 'AP — Gulf military', url: 'https://apnews.com/hub/middle-east' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 06:30Z`,
  },
  {
    id: 'irgcn',
    domain: 'Maritime',
    label: 'IRGCN Suicide FAC / Mining Escalation',
    pct: 71,
    trend: 'UP',
    trendDelta: '+9%',
    horizon: '48h',
    severity: 'HIGH',
    assessmentText:
      'ORACLE-9 assesses 71% probability of renewed IRGCN fast-attack craft offensive operations or mine re-seeding in Hormuz transit zones within 48 hours. MANTIS (maritime HUMINT) reported mine-layer GOLF-7 (MMSI 422XXXXXX) repositioning to 26.1°N / 56.53°E on Day 18 — 12nm from MCM corridor ZB-Alpha. Drone imagery shows 14 IRGCN FAC fuelled and armed at Qeshm naval base. Following Day 15 TLAM strike on Bandar Abbas, IRGCN has dispersed FAC across four secondary bases. 5th Fleet surface screen remains intact — no confirmed coalition warship losses to C-802 in AOR.',
    indicators: [
      'AIS anomaly: GOLF-7 dark transit to 26.1°N/56.53°E — mine layer profile (MANTIS)',
      'IMINT: 14 IRGCN FAC armed/fuelled Qeshm naval base (Day 20)',
      'SIGINT: 760 MHz IRGCN tactical net — burst traffic 00:00–02:00Z daily',
      'OSINT: MarineTraffic gap — 3 tankers diverting Cape of Good Hope suddenly',
      'HUMINT: FAC pre-positioned Larak Island secondary base (Day 18)',
    ],
    sources: [
      { label: 'UKMTO Advisory', url: 'https://www.ukmto.org/' },
      { label: 'MarineTraffic AIS', url: 'https://www.marinetraffic.com/' },
      { label: 'USNI — CTF operations', url: 'https://news.usni.org/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 04:00Z`,
  },
  {
    id: 'cyber',
    domain: 'Cyber',
    label: 'Major Destructive Cyber Strike (Critical Infrastructure)',
    pct: 58,
    trend: 'UP',
    trendDelta: '+14%',
    horizon: '72h',
    severity: 'HIGH',
    assessmentText:
      'ORACLE-9 assesses 58% probability of a major destructive Iranian-attributed cyber attack against US/allied critical infrastructure within 72 hours. APT34 (OilRig) lateral movement was detected on CENTCOM logistics contractor subnet on Day 18 — 3 hosts isolated by CISA Emergency Directive ED 26-01. APT33 has pre-positioned implants on Saudi Aramco OT networks since Day 11 (Abqaiq partial disruption already occurred). Potential targets: CONUS power grid (5 ICS vulnerabilities active), DoD logistics networks, UAE infrastructure, financial SWIFT nodes. Active CISA ED 26-01 patch order outstanding for Ivanti CVE-2024-21887.',
    indicators: [
      'CERBERUS: APT34 lateral movement CENTCOM contractor subnet Day 20 — 3 hosts isolated',
      'CISA ED 26-01: Ivanti CVE-2024-21887 exploitation confirmed on DoD contractor nets',
      'FBI: IRGC-linked operatives arrested Houston TX + New York NY — CI surveill.',
      'SIGINT: APT33 OT network beacon activity Aramco Dhahran sector (Day 18)',
      'NEXUS: APT35 spear-phish campaign targeting US-CENTCOM personnel emails (active)',
    ],
    sources: [
      { label: 'CISA Alert ED 26-01', url: 'https://www.cisa.gov/news-events/alerts' },
      { label: 'Mandiant / Google Threat Intel', url: 'https://cloud.google.com/blog/topics/threat-intelligence' },
      { label: 'FBI Cyber Division', url: 'https://www.fbi.gov/investigate/cyber' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 00:45Z`,
  },
  {
    id: 'hezbollah',
    domain: 'Proxy',
    label: 'Hezbollah Northern Front Escalation',
    pct: 44,
    trend: 'STABLE',
    trendDelta: '+1%',
    horizon: '72h',
    severity: 'ELEVATED',
    assessmentText:
      'ORACLE-9 assesses 44% probability of Hezbollah opening a sustained northern front against Israel in the next 72 hours, unchanged from Day 20. While Iran has publicly demanded Hezbollah engagement, Lebanese domestic political opposition and Hezbollah\'s own strategic calculus (post-2024 degradation / rebuilding phase) appear to be restraining escalation. Cross-border rocket fire from southern Lebanon has occurred Days 6, 9, 13 — all sub-threshold responses. IDF Northern Command remains at DEFCON-2 posture. Key tripwires: Israeli ground forces movement north of Haifa, or a direct Israeli strike on Hezbollah HVT.',
    indicators: [
      'SIGINT: Tehran → Dahieh encrypted calls up +40% Day 15–18 (demand for action)',
      'IMINT: Hezbollah rocket caches visible Marjayoun district (unconfirmed Day 17)',
      'OSINT: Lebanese civil-military liaisons no-show to pre-arranged UN meetings',
      'HUMINT: Hezbollah leadership split — hardliners vs strategic restraint faction',
      'OSINT: IDF Northern Command DEFCON-2 posture publicly acknowledged',
    ],
    sources: [
      { label: 'Haaretz — Lebanon', url: 'https://www.haaretz.com/' },
      { label: 'ISW Proxy Assessment', url: 'https://www.understandingwar.org/' },
      { label: 'TOI — IDF North', url: 'https://www.timesofisrael.com/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 01:30Z`,
  },
  {
    id: 'nuclear',
    domain: 'Nuclear',
    label: 'Iranian Nuclear Escalation (Declared Weapons Intent)',
    pct: 34,
    trend: 'UP',
    trendDelta: '+6%',
    horizon: '30d',
    severity: 'ELEVATED',
    assessmentText:
      'ORACLE-9 assesses 34% probability of Iran making a formal declaration of nuclear weapons intent, or attempting to reconstitute sufficient fissile material for a device, within 30 days — elevated from 28% on Day 21 following Khamenei KIA. US-Israeli precision strikes degraded Natanz FEP, Fordow FFEP, and Isfahan UCF by an estimated 18–24 months of weapons-grade production capacity. B-21 ANVIL-01 Day 22 MOP strike inflicted additional structural damage to Natanz Hall B tunnel infrastructure. IAEA continuity of knowledge completely lost since Day 5. Reconstitution risk is medium-term (6–18 months minimum) absent undisclosed covert sites. Succession vacuum raises risk of IRGC unilateral escalation decision without civilian NCA oversight. Key unknown: pre-deployed fissile material, intact covert enrichment sites.',
    indicators: [
      'IAEA: All monitoring equipment offline Day 5 \u2014 continuity of knowledge lost',
      'NGA: Natanz Hall B tunnel collapse imagery post-ANVIL-01 \u2014 BDA ongoing',
      'HUMINT: No indication of pre-deployed nuclear device (HIGH confidence D22)',
      'SIGINT: IRGC CINC command net elevated tempo post-Khamenei KIA \u2014 watch',
      'OSINT: Arms Control Wonk / FAS: 18\u201324 month reconstitution minimum (public est.)',
    ],
    sources: [
      { label: 'IAEA Director General Statement', url: 'https://www.iaea.org/news' },
      { label: 'Arms Control Association', url: 'https://www.armscontrol.org/' },
      { label: 'FAS Nuclear Notebook', url: 'https://fas.org/issues/nuclear-weapons/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 08:00Z`,
  },
  {
    id: 'succession',
    domain: 'Strategic',
    label: 'IRGC Succession Crisis — Rogue Escalation Risk (Post-Khamenei KIA)',
    pct: 74,
    trend: 'UP',
    trendDelta: '+74%',
    horizon: '24h',
    severity: 'CRITICAL',
    assessmentText:
      'ORACLE-9 assesses 74% probability of a destabilising succession event within 24 hours following confirmed KIA of Supreme Leader Khamenei at 221435Z. Assembly of Experts must convene to select new Supreme Leader \u2014 a constitutionally required 3\u20137 day process that creates acute NCA vacuum. IRGC CINC Maj Gen Salami has assumed interim strategic command authority but lacks constitutional legitimacy. Two IRGC hardliner factions have documented doctrine of pre-delegated authority for ballistic missile retaliation. Risk of unilateral IRGC missile barrage, use of pre-positioned proxy chemical munitions, or Hezbollah mass-fire activation without elected civilian oversight. DIA assesses this as the highest escalation risk window of the entire conflict. US forces at FPCON DELTA + THREATCON ALPHA.',
    indicators: [
      'CONFIRMED: Khamenei KIA 221435Z \u2014 NGA/NRO + dual HUMINT corroboration',
      'SIGINT: IRGC CINC command net: FLASH traffic volume +340% vs. D21 baseline',
      'HUMINT: SERPENT-7 reports IRGC Aerospace Force missile battalions on 15-min alert',
      'IMINT: 6\u00d7 IRGC Shahab/Emad TELs repositioned out of garrison post-D22 1800Z',
      'DIA D23 FLASH: Assembly of Experts quorum uncertain \u2014 3 senior members unreachable',
    ],
    sources: [
      { label: 'DIA Flash Assessment', url: 'https://www.dia.mil/' },
      { label: 'ICG \u2014 Iran Crisis Report', url: 'https://www.crisisgroup.org/middle-east-north-africa/gulf-and-arabian-peninsula/iran' },
      { label: 'RAND \u2014 Iran Succession Scenarios', url: 'https://www.rand.org/topics/iran.html' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 06:00Z`,
  },
  {
    id: 'hormuz_close',
    domain: 'Maritime',
    label: 'Total Hormuz Closure (>30 days)',
    pct: 61,
    trend: 'UP',
    trendDelta: '+7%',
    horizon: '30d',
    severity: 'HIGH',
    assessmentText:
      'ORACLE-9 assesses 61% probability that the Strait of Hormuz remains fully closed to commercial traffic for more than 30 days from Day 1. Mines, FAC harassment, and IRGCN anti-ship capability have effectively shut commercial transits since Day 3. MCM corridor ZB-Alpha partially cleared (22 mines neutralised by Day 22) but GOLF-7 mine-layer activity threatens re-seeding. Brent crude: $118/bbl. LNG disruption: 20% of global supply offline. IMO force majeure active. UKMTO estimates minimum 45-day clearance timeline once active hostilities end. Key assumption: Iran expends remaining maritime denial capability in continued attrition.',
    indicators: [
      'UKMTO: 43 mines confirmed in shipping lanes Days 1–22; 22 cleared ZB-Alpha',
      'IMINT: GOLF-7 mine-layer at 26.1°N/56.53°E — ZB-Alpha re-seeding imminent',
      'OSINT: Bloomberg — GCC tankers rerouting Cape of Good Hope universally',
      'OSINT: Brent $118/bbl — IMO force majeure Hormuz routing active',
      'CENTCOM: MCM clearance rate 1–2 mines/day — full clearance 6–8 weeks minimum',
    ],
    sources: [
      { label: 'Bloomberg Energy', url: 'https://www.bloomberg.com/energy' },
      { label: 'UKMTO Advisory', url: 'https://www.ukmto.org/' },
      { label: 'IMO Circular', url: 'https://www.imo.org/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 05:00Z`,
  },
  {
    id: 'conus_attack',
    domain: 'Homeland',
    label: 'IRGC Terrorist Attack on CONUS Soil',
    pct: 31,
    trend: 'UP',
    trendDelta: '+9%',
    horizon: '30d',
    severity: 'ELEVATED',
    assessmentText:
      'ORACLE-9 assesses 31% probability of an IRGC-directed or -inspired terrorist attack on US soil within 30 days. FBI arrested IRGC-linked operatives in Houston TX and New York NY on Day 17 in pre-operational surveillance postures at petrochemical and port facilities. DHS NTAS ELEVATED bulletin active. IRGC Quds Force has historically maintained sleeper networks in the Western hemisphere; historical precedent: 2011 Arbabsiar Assassination Plot (DC). Key concern: retaliatory lone-wolf attacks inspired by IRGC media. CBP has elevated screening protocols at all US ports of entry.',
    indicators: [
      'FBI: 2 IRGC-linked operatives arrested Houston TX + New York NY Day 17',
      'DHS NTAS ELEVATED: IRGC surveillance CONUS military/CI facilities confirmed',
      'CISA: Petrochemical and port facility security posture HEIGHTENED',
      'FBI: Additional 6 individuals under 24h surveillance nationwide (Day 22)',
      'HUMINT: Quds Force Canada cell activated — travel to US border areas (Day 14)',
    ],
    sources: [
      { label: 'FBI Press Release', url: 'https://www.fbi.gov/news/press-releases' },
      { label: 'DHS NTAS', url: 'https://www.dhs.gov/ntas' },
      { label: 'Reuters — domestic threat', url: 'https://www.reuters.com/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 03:00Z`,
  },
  {
    id: 'ceasefire_72h',
    domain: 'Diplomatic',
    label: 'Ceasefire Agreement (Within 72h)',
    pct: 8,
    trend: 'DOWN',
    trendDelta: '-3%',
    horizon: '72h',
    severity: 'MODERATE',
    assessmentText:
      'ORACLE-9 assesses only 4% probability of a binding ceasefire agreement within 72 hours — reduced from 8% following Day 24 BM Barrage Alpha-4 and Iran\'s withdrawal from the Oman back-channel at 241200Z. Oman channel SUSPENDED. Qatar channel SUSPENDED since Day 13. Switzerland channel passively available but no active talks. UN Security Council Resolution stalled — Russia and China signalling possible abstention but not guaranteed. IRGC CINC Salami\'s unilateral command has locked out pragmatist faction from ceasefire negotiations. Window for tactical pause assessed at 8–12% within 7 days, contingent on Assembly of Experts reaching leadership consensus and civilian NCA restoration.',
    indicators: [
      'Oman back-channel: Active — no breakthrough reported (Day 22)',
      'Qatar mediation: Active — US-Iran precondition gap unbridged',
      'UNSC: 2nd veto Day 14 — Russia + China — French proposal under review',
      'US Statement Day 19: Formal rejection of Iran withdrawal precondition',
      'Tehran Day 20: Reiterated 7-point ceasefire demand including full US withdrawal',
    ],
    sources: [
      { label: 'Reuters Diplomatic', url: 'https://www.reuters.com/world/middle-east/' },
      { label: 'UN Security Council', url: 'https://www.un.org/securitycouncil/' },
      { label: 'Al-Monitor — Oman channel', url: 'https://www.al-monitor.com/' },
    ],
    lastUpdated: `${toShortDate(CONFLICT_DAY)} · 06:00Z`,
  },
]

const TRAJECTORY: TrajectoryPoint[] = [
  { day: 1,  bm: 15, shahed: 20, cyber: 12 },
  { day: 2,  bm: 18, shahed: 22, cyber: 14 },
  { day: 3,  bm: 30, shahed: 35, cyber: 16 },
  { day: 4,  bm: 28, shahed: 30, cyber: 20 },
  { day: 5,  bm: 25, shahed: 28, cyber: 22 },
  { day: 6,  bm: 35, shahed: 40, cyber: 25 },
  { day: 7,  bm: 32, shahed: 38, cyber: 28 },
  { day: 8,  bm: 40, shahed: 55, cyber: 32 },
  { day: 9,  bm: 52, shahed: 45, cyber: 35 },
  { day: 10, bm: 55, shahed: 50, cyber: 38 },
  { day: 11, bm: 50, shahed: 55, cyber: 42 },
  { day: 12, bm: 45, shahed: 52, cyber: 44 },
  { day: 13, bm: 60, shahed: 60, cyber: 46 },
  { day: 14, bm: 58, shahed: 57, cyber: 50 },
  { day: 15, bm: 55, shahed: 62, cyber: 48 },
  { day: 16, bm: 56, shahed: 64, cyber: 50 },
  { day: 17, bm: 67, shahed: 68, cyber: 52 },
  { day: 18, bm: 64, shahed: 76, cyber: 55 },
  { day: 19, bm: 67, shahed: 82, cyber: 58 },
  { day: 20, bm: 67, shahed: 82, cyber: 58 },
  { day: 21, bm: 70, shahed: 84, cyber: 61 },
  // Day 22: Khamenei KIA — IRGC succession vacuum → probability spike across all domains
  { day: 22, bm: 82, shahed: 88, cyber: 71 },
  // Day 23: Salami assumes unilateral command — hardliner escalation posture locked in
  { day: 23, bm: 85, shahed: 90, cyber: 74 },
  // Day 24: Oman channel suspended after BM Barrage Alpha-4 — peak escalation window
  { day: 24, bm: 88, shahed: 92, cyber: 76 },
  // Day 25: Ceasefire pre-conditions tabled; Iran SNSC split — threat posture slightly cooling
  { day: 25, bm: 82, shahed: 86, cyber: 71 },
  // Day 26: Iran SNSC drops pre-condition; Oman back-channel reopened — BM Barrage Alpha-5 (last)
  { day: 26, bm: 76, shahed: 80, cyber: 66 },
  // Day 27: Abu Dhabi Framework signed; UNSCR 2731 passed — ceasefire 68% confidence
  { day: 27, bm: 64, shahed: 72, cyber: 60 },
  // Day 28: 6th barrage risk declining; ceasefire 68%; Shahed stocks depleted
  { day: 28, bm: 41, shahed: 34, cyber: 52 },
  // Day 29-30: Abu Dhabi 96h kinetic pause framework — standdown confirmed both sides
  { day: 29, bm: 35, shahed: 26, cyber: 46 },
  { day: 30, bm: 28, shahed: 19, cyber: 40 },
  // Day 31-32: Formal ceasefire agreement signed Day 32 — offensive ops ceased
  { day: 31, bm: 22, shahed: 14, cyber: 35 },
  { day: 32, bm: 15, shahed: 10, cyber: 30 },
  // Day 33-38: Ceasefire holding; IRGCN returns to port; Hormuz demining begins Day 35
  { day: 33, bm: 13, shahed: 9,  cyber: 27 },
  { day: 34, bm: 11, shahed: 8,  cyber: 26 },
  { day: 35, bm: 10, shahed: 7,  cyber: 25 },
  { day: 36, bm: 10, shahed: 7,  cyber: 24 },
  { day: 37, bm: 10, shahed: 7,  cyber: 24 },
  { day: 38, bm: 11, shahed: 8,  cyber: 24 },
  // Day 39-42: Mojtaba Khamenei nominated/confirmed as new SL — IRGC hardliner tension
  { day: 39, bm: 14, shahed: 10, cyber: 26 },
  { day: 40, bm: 19, shahed: 13, cyber: 29 },
  { day: 41, bm: 23, shahed: 16, cyber: 32 },
  { day: 42, bm: 25, shahed: 18, cyber: 33 },
  // Day 43-45: IRGC hardliner faction contained; IAEA inspection team enters Iran
  { day: 43, bm: 21, shahed: 15, cyber: 30 },
  { day: 44, bm: 18, shahed: 12, cyber: 27 },
  { day: 45, bm: 15, shahed: 10, cyber: 25 },
  // Day 46-48: Reconstruction talks Geneva; Brent $76/bbl; Hormuz ZB-α 100% cleared
  { day: 46, bm: 13, shahed: 9,  cyber: 23 },
  { day: 47, bm: 13, shahed: 9,  cyber: 22 },
  { day: 48, bm: 12, shahed: 8,  cyber: 22 },
  // Day 49-52: Ceasefire monitoring Phase 1; sporadic IRGC proxy activity
  { day: 49, bm: 12, shahed: 8,  cyber: 21 },
  { day: 50, bm: 13, shahed: 9,  cyber: 22 },
  { day: 51, bm: 14, shahed: 10, cyber: 22 },
  { day: 52, bm: 15, shahed: 10, cyber: 23 },
  // Day 53-54: Monitoring Phase 2; IRGC hardliner watch ACTIVE; Fordow access pending
  { day: 53, bm: 16, shahed: 11, cyber: 24 },
  { day: 54, bm: 17, shahed: 12, cyber: 25 },
]

// ── Components ────────────────────────────────────────────────────────────────

function SparkLine({ data, field }: { data: TrajectoryPoint[]; field: keyof Omit<TrajectoryPoint, 'day'> }) {
  const maxVal = 100
  const h = 40
  const w = 280
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - (d[field] / maxVal) * h
    return `${x},${y}`
  }).join(' ')

  const area = `0,${h} ` + pts + ` ${w},${h}`

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: 40 }}>
      <defs>
        <linearGradient id={`grad-${field}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#grad-${field})`} suppressHydrationWarning />
      <polyline points={pts} fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinejoin="round" suppressHydrationWarning />
    </svg>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ThreatsPage() {
  return (
    <div className="space-y-5 max-w-screen-xl">

      {/* Live intelligence feeds — video-feed frame treatment */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="video-feed-frame relative rounded-sm">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 left-8 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            <span className="text-[7px] text-red-400/70 font-bold tracking-[0.2em]">REC</span>
          </div>
          <TheaterIntelFeed theater="Air" limit={12} />
        </div>
        <div className="video-feed-frame relative rounded-sm">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-8 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">OSINT LIVE</span>
          </div>
          <LiveNewsBoard limit={20} warFilter={true} compact={false} />
        </div>
      </div>

      {/* ── Cinematic Threat Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(245,158,11,0.012) 2px, rgba(245,158,11,0.012) 4px)'}} />
          <div className="relative z-[3] flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="relative">
                <Activity size={20} className="text-amber-400 animate-pulse drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-400 rounded-full animate-pulse" />
              </div>
              <div>
                <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                  ORACLE-9 Probabilistic Threat Engine — Day {CONFLICT_DAY} of Active Hostilities
                </p>
                <h1 className="text-base font-bold tracking-widest text-amber-400 uppercase glow-amber">
                  THREAT ASSESSMENT — {CONFLICT_DATE}
                </h1>
                <p className="text-[10px] text-zinc-500 mt-1 leading-relaxed">
                  ORACLE-9 cross-domain probabilistic engine fusing SIGINT (TRIDENT), IMINT (NRO), HUMINT, AIS, ADS-B, and OSINT
                  streams. All assessments represent probability within stated horizon under current conditions.
                  Probabilities refresh every 30 seconds via live Bayesian engine.
                </p>
              </div>
            </div>
            <div className="on-air-badge inline-block bg-amber-900/40 text-amber-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-1 rounded-sm border border-amber-800/60 shrink-0">
              ● THREAT ENGINE LIVE
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" style={{background: 'linear-gradient(90deg, transparent, #d97706, #f59e0b, #d97706, transparent)'}} />
      </div>

      {/* 20-day threat trajectory — cinematic */}
      <div className="video-feed-frame tac-card p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-amber-500/60 font-bold tracking-[0.2em]">TRAJECTORY MODEL</span>
        </div>
        <div className="flex items-center gap-2 pb-2 mb-3 relative z-[1]">
          <TrendingUp size={11} className="text-amber-400 drop-shadow-[0_0_6px_rgba(245,158,11,0.4)]" />
          <h2 className="tac-section-header flex-1">
            <span className="glow-amber">Threat Trajectory — Days 1–{CONFLICT_DAY}</span>
          </h2>
          <span className="ml-auto text-[9px] text-zinc-600">ORACLE-9 historical model output</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { field: 'bm' as const,     label: '6th Barrage Risk',      color: 'text-red-400',    gradId: 'bm' },
            { field: 'shahed' as const, label: 'Shahed Swarm',          color: 'text-sky-400',    gradId: 'shahed' },
            { field: 'cyber' as const,  label: 'Destructive Cyber',     color: 'text-purple-400', gradId: 'cyber' },
          ].map(({ field, label, color }) => (
            <div key={field} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className={cn('text-[9px] font-bold tracking-widest uppercase', color)}>{label}</span>
                <span className={cn('text-base font-bold tabular-nums', color)}>
                  {TRAJECTORY[TRAJECTORY.length - 1][field]}%
                </span>
              </div>
              <SparkLine data={TRAJECTORY} field={field} />
              <div className="flex justify-between text-[8px] text-zinc-700">
                <span>Day 1</span><span>Day {CONFLICT_DAY}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ORACLE-9 live probabilities — cinematic */}
      <div className="tac-card tac-card-critical p-4 space-y-3 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(239,68,68,0.03) 0%, transparent 50%)'}} />
        <div className="tac-section-header mb-1 relative z-[1]">
          <Activity size={11} className="text-amber-400 animate-pulse drop-shadow-[0_0_6px_rgba(245,158,11,0.4)]" />
          <span className="text-amber-400 tracking-widest glow-amber">ORACLE-9 LIVE — Real-Time Threat Probabilities</span>
          <span className="ml-auto flex items-center gap-1.5 text-[9px] font-mono text-zinc-500 normal-case font-normal">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            auto-refresh 30s
          </span>
        </div>
        <div className="relative z-[1]">
          <OraclePanel />
        </div>
      </div>

      {/* Model methodology — cinematic */}
      <div className="tac-card tac-card-intel p-4 space-y-2 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(14,165,233,0.02) 0%, transparent 50%)'}} />
        <div className="flex items-center gap-2 pb-2 mb-3 relative z-[1]">
          <Shield size={11} className="text-zinc-500 drop-shadow-[0_0_4px_rgba(161,161,170,0.3)]" />
          <h2 className="tac-section-header flex-1">ORACLE-9 Model Methodology</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'SIGINT Streams', desc: 'TRIDENT + CERBERUS + NEXUS multi-INT fusion — SL/IRGC comm pattern analysis, COMSEC discipline shifts', icon: Radio },
            { label: 'IMINT Sources', desc: 'NRO overhead + commercial SAR (Capella, ICEYE) + Maxar WV-3 — TEL count, airframe pre-arm, naval posture', icon: Zap },
            { label: 'HUMINT Network', desc: 'MANTIS (maritime) + embedded regional HUMINT — ground truth on IRGCN ops, proxy positioning, Quds Force', icon: Shield },
            { label: 'OSINT Fusion', desc: 'AIS/ADS-B anomaly detection, financial signals (Brent/CDS), 36 verified media outlets, UN/IAEA official feeds', icon: Activity },
          ].map(({ label, desc, icon: Icon }) => (
            <div key={label} className="space-y-1">
              <div className="flex items-center gap-1.5">
                <Icon size={10} className="text-amber-500" />
                <p className="text-[9px] font-bold tracking-widest text-zinc-300 uppercase">{label}</p>
              </div>
              <p className="text-[10px] text-zinc-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-700 pt-2 border-t border-zinc-800">
          ORACLE-9 is a live AI probabilistic assessment engine. All probability estimates are AI-synthesized from
          publicly available information combined with real-time open-source intelligence. Not a product of any government intelligence community.
          Sources cited are real public outlets. {' '}
          <a href="https://www.rand.org/topics/iran.html" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400">
            RAND Iran Analysis
          </a>{' · '}
          <a href="https://www.understandingwar.org/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400">
            ISW
          </a>{' · '}
          <a href="https://www.armscontrolwonk.com/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400">
            Arms Control Wonk
          </a>
        </p>
      </div>

    </div>
  )
}
