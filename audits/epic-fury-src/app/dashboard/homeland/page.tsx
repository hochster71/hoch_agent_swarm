import { Home, AlertTriangle, ExternalLink, MapPin, DollarSign } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toShortDate } from '@/lib/conflict-day'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'
import { ShareButton } from '@/components/ShareButton'

export const revalidate = 0

const CONFLICT_DAY = getConflictDay()

// ── NTAS Bulletin ─────────────────────────────────────────────────────────────

const NTAS_BULLETIN = {
  id: 'NTAS-2026-04',
  issued: '01 MAR 2026',
  expires: 'UNTIL FURTHER NOTICE',
  title: 'IRGC-Affiliated Actors Identified Conducting Surveillance and Pre-Operational Planning Against US Critical Infrastructure and Military Facilities',
  summary:
    'The Department of Homeland Security, in coordination with the FBI and CISA, has identified specific intelligence indicating IRGC-affiliated threat actors are conducting pre-operational surveillance and cyber pre-positioning activities targeting US critical infrastructure sectors and CONUS military installations. All critical infrastructure owners and operators must immediately implement enhanced monitoring, apply mandated patches (see ED 26-01), and report anomalous network activity to CISA at cisa.gov/report.',
}

// ── Critical Infrastructure Domain Status ─────────────────────────────────────

interface CIDomain {
  label: string
  level: 'HIGH' | 'ELEVATED' | 'GUARDED'
  detail: string
  dot: string
  text: string
  levelText: string
  levelBg: string
}

const CI_DOMAINS: CIDomain[] = [
  {
    label: 'Energy',
    level: 'HIGH',
    dot: 'bg-yellow-400',
    text: 'text-yellow-400',
    levelText: 'text-amber-400',
    levelBg: 'border-amber-800 bg-amber-950/10',
    detail: 'NERC CIP-2026-03: APT33 pre-positioning on EMS/SCADA confirmed at 3 regional transmission orgs',
  },
  {
    label: 'Cyber',
    level: 'HIGH',
    dot: 'bg-purple-400',
    text: 'text-purple-400',
    levelText: 'text-amber-400',
    levelBg: 'border-amber-800 bg-amber-950/10',
    detail: 'APT34 lateral movement confirmed on CENTCOM logistics subnet Day 17 — ED 26-01 active',
  },
  {
    label: 'Defense IB',
    level: 'HIGH',
    dot: 'bg-red-400',
    text: 'text-red-400',
    levelText: 'text-amber-400',
    levelBg: 'border-amber-800 bg-amber-950/10',
    detail: 'APT35 contractor credential harvesting; Moses Staff wiper on two CONUS logistics firms',
  },
  {
    label: 'Border',
    level: 'HIGH',
    dot: 'bg-amber-400',
    text: 'text-amber-400',
    levelText: 'text-amber-400',
    levelBg: 'border-amber-800 bg-amber-950/10',
    detail: 'CBP elevated screening 47 land PoEs; USCG MARSEC 2 NY/LA; FBI JTTF arrests in TX & NY',
  },
  {
    label: 'Water',
    level: 'ELEVATED',
    dot: 'bg-blue-400',
    text: 'text-blue-400',
    levelText: 'text-sky-400',
    levelBg: 'border-sky-900 bg-sky-950/10',
    detail: 'Cyber Av3ngers Unitronics PLC exploitation at 3 TX/PA water utilities — CISA AA23-335A active',
  },
  {
    label: 'Finance',
    level: 'ELEVATED',
    dot: 'bg-lime-400',
    text: 'text-lime-400',
    levelText: 'text-sky-400',
    levelBg: 'border-sky-900 bg-sky-950/10',
    detail: 'FinCEN FIN-2026-A002: IRGC crypto sanctions evasion via US-based shell company networks',
  },
  {
    label: 'Transport',
    level: 'ELEVATED',
    dot: 'bg-orange-400',
    text: 'text-orange-400',
    levelText: 'text-sky-400',
    levelBg: 'border-sky-900 bg-sky-950/10',
    detail: 'TSA elevated screening near military installations; Class I rail OT monitoring heightened',
  },
  {
    label: 'Nuclear',
    level: 'ELEVATED',
    dot: 'bg-yellow-300',
    text: 'text-yellow-300',
    levelText: 'text-sky-400',
    levelBg: 'border-sky-900 bg-sky-950/10',
    detail: 'NRC enhanced facility security all 93 reactors; cyber perimeter access review mandated',
  },
  {
    label: 'Comms',
    level: 'ELEVATED',
    dot: 'bg-cyan-400',
    text: 'text-cyan-400',
    levelText: 'text-sky-400',
    levelBg: 'border-sky-900 bg-sky-950/10',
    detail: 'ISP peering point probe activity from Iranian IP space; major telecom OT on high alert',
  },
  {
    label: 'Healthcare',
    level: 'GUARDED',
    dot: 'bg-emerald-400',
    text: 'text-emerald-400',
    levelText: 'text-emerald-400',
    levelBg: 'border-zinc-800 bg-zinc-900/20',
    detail: 'No active targeting identified. CISA HC3 enhanced monitoring in place post-conflict onset',
  },
]

// ── APT Campaign Tracker ──────────────────────────────────────────────────────

interface AptCampaign {
  name: string
  aliases: string
  sector: string
  ttps: string
  status: 'ACTIVE' | 'MONITORING' | 'DISRUPTED'
  confidence: number
  advisoryId: string
  advisoryUrl: string
  detail: string
  lastSeen: string
  statusColor: string
  borderColor: string
  bgColor: string
}

const APT_CAMPAIGNS: AptCampaign[] = [
  {
    name: 'APT33 / Holmium',
    aliases: 'Refined Kitten, Elfin, MAGNALLIUM',
    sector: 'Aviation, Energy, Petrochemical',
    ttps: 'TRITON/TRISIS ICS malware; watering hole targeting OT jump servers; destructive Stage-2 payloads',
    status: 'ACTIVE',
    confidence: 87,
    advisoryId: 'CISA AA22-257A',
    advisoryUrl: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-257a',
    detail: 'Aviation sector targeting escalated Day 12. Spearphishing lures reference conflict news. Two US defense sub-contractors isolated networks Day 14 as precaution. Persistent pre-positioning on EMS/SCADA confirmed Day 25 — emergency NERC CIP-2026-03 mandate active.',
    lastSeen: `Day ${CONFLICT_DAY > 25 ? CONFLICT_DAY : 25}`,
    statusColor: 'text-red-400',
    borderColor: 'border-red-800',
    bgColor: 'bg-red-950/10',
  },
  {
    name: 'APT34 / OilRig',
    aliases: 'Helix Kitten, Crambus, Cobalt Gypsy',
    sector: 'Government, Finance, Defense Contractors',
    ttps: 'LIONTAIL/POWBAT implants; SQL injection; CVE-2024-21887 Ivanti VPN exploitation',
    status: 'ACTIVE',
    confidence: 93,
    advisoryId: 'CISA AA24-038A',
    advisoryUrl: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-038a',
    detail: `Lateral movement on CENTCOM logistics subnet confirmed Day 17 — 3 contractor hosts isolated. CERBERUS intelligence driving containment. CVE-2024-21887 Ivanti used for initial access. Day 26 activity: new Ivanti exploitation attempts against 5th Fleet contractor network — blocked by CISA ED 26-01 patches.`,
    lastSeen: `Day ${CONFLICT_DAY > 26 ? CONFLICT_DAY : 26}`,
    statusColor: 'text-red-400',
    borderColor: 'border-red-800',
    bgColor: 'bg-red-950/10',
  },
  {
    name: 'APT35 / Mint Sandstorm',
    aliases: 'Charming Kitten, Phosphorus, TA453',
    sector: 'Defense Contractors, Think Tanks, Academia',
    ttps: 'Credential harvesting via fake conference invites; MFA bypass; PowerShell backdoors',
    status: 'ACTIVE',
    confidence: 82,
    advisoryId: 'NSA CSA U/OO/241840-24',
    advisoryUrl: 'https://www.nsa.gov/cybersecurity-advisories/',
    detail: `Credential harvesting targeting policy researchers and CENTCOM-adjacent contractors. Fake "Epic Fury analyst briefing" lure documents circulating since Day 5. Day 25: new phishing wave targeting Abu Dhabi ceasefire delegation staff identified and blocked by NSA MDR.`,
    lastSeen: `Day ${CONFLICT_DAY > 25 ? CONFLICT_DAY : 25}`,
    statusColor: 'text-amber-400',
    borderColor: 'border-amber-800',
    bgColor: 'bg-amber-950/10',
  },
  {
    name: 'Cyber Av3ngers / IRGC MCIS',
    aliases: 'Emennet Pasargad (associated)',
    sector: 'Water & Wastewater, ICS/OT Systems',
    ttps: 'Unitronics Vision PLC exploitation (CVE-2023-6448); OT lateral movement; defacement and disruption',
    status: 'MONITORING',
    confidence: 79,
    advisoryId: 'CISA AA23-335A',
    advisoryUrl: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-335a',
    detail: 'Three US water utilities in TX and PA reported unauthorized SCADA access. Unitronics PLCs targeted. CISA ICS patch mandated. Day 24 re-probe attempt on two patched utilities detected and blocked by WaterISAC SOC.',
    lastSeen: `Day ${CONFLICT_DAY > 24 ? CONFLICT_DAY : 24}`,
    statusColor: 'text-amber-400',
    borderColor: 'border-amber-800',
    bgColor: 'bg-amber-950/10',
  },
  {
    name: 'Moses Staff',
    aliases: 'DEV-0796, Void Manticore, Storm-0842',
    sector: 'Government, Defense Logistics, Transportation',
    ttps: 'StrifeWater wiper malware; ransomware-without-decryption-key; multi-stage loader chains',
    status: 'MONITORING',
    confidence: 71,
    advisoryId: 'FBI Flash IC3-2026-C019',
    advisoryUrl: 'https://www.fbi.gov/investigate/cyber',
    detail: `Ransomware-without-ransom against US defense logistics software. StrifeWater wiper deployed on two CONUS contractors Day 11. IRGC sponsorship assessed HIGH confidence. Day 26 variant (StrifeWater-B) detected in pre-execution sandbox — blocked before deployment.`,
    lastSeen: `Day ${CONFLICT_DAY > 26 ? CONFLICT_DAY : 26}`,
    statusColor: 'text-amber-400',
    borderColor: 'border-amber-800',
    bgColor: 'bg-amber-950/10',
  },
  {
    name: 'Tortoiseshell / Imperial Kitten',
    aliases: 'TB3071, POTASSIUM, Yellow Liderc',
    sector: 'IT Managed Service Providers, Supply Chain',
    ttps: 'Strategic web compromise (SWC); MSP update poisoning; LEMPO/SharPivot RAT implants',
    status: 'MONITORING',
    confidence: 63,
    advisoryId: 'CISA AA23-165A',
    advisoryUrl: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-165a',
    detail: `Two CONUS MSPs serving DoD clients reporting anomalous outbound connections post-Day 9. IOCs match Tortoiseshell SharPivot and LEMPO implants. Supply chain contamination risk being assessed. Day 27: forensics team confirmed SharPivot persistence on one host — isolation and remediation complete.`,
    lastSeen: `Day ${CONFLICT_DAY > 27 ? CONFLICT_DAY : 27}`,
    statusColor: 'text-sky-400',
    borderColor: 'border-sky-900',
    bgColor: 'bg-sky-950/10',
  },
]

// ── Federal Advisories ────────────────────────────────────────────────────────

interface FedAdvisory {
  source: string
  id: string
  date: string
  subject: string
  url: string
  urgent?: boolean
  sourceColor: string
}

const FEDERAL_ADVISORIES: FedAdvisory[] = [
  {
    source: 'CISA',
    id: 'ED 26-01',
    date: '11 MAR 26',
    subject: 'Emergency Directive: Patch Ivanti ConnectSecure & Fortinet VPN — active IRGC exploitation in-progress',
    url: 'https://www.cisa.gov/news-events/directives',
    urgent: true,
    sourceColor: 'text-red-400 bg-red-950/40 border-red-800',
  },
  {
    source: 'DHS',
    id: 'NTAS-2026-04',
    date: '01 MAR 26',
    subject: 'NTAS ELEVATED: IRGC-affiliated CONUS critical infrastructure and military installation threat',
    url: 'https://www.dhs.gov/ntas',
    urgent: true,
    sourceColor: 'text-red-400 bg-red-950/40 border-red-800',
  },
  {
    source: 'FBI',
    id: 'IC3-2026-C019',
    date: '08 MAR 26',
    subject: 'IRGC-linked surveillance operatives arrested — Houston TX, New York NY, Boston MA operations confirmed',
    url: 'https://www.fbi.gov/investigate/counterterrorism',
    urgent: true,
    sourceColor: 'text-amber-400 bg-amber-950/40 border-amber-800',
  },
  {
    source: 'NERC',
    id: 'CIP-2026-03',
    date: '15 MAR 26',
    subject: 'Electric grid bulletin: IRGC pre-positioning on North American EMS/SCADA — APT33 TTPs confirmed',
    url: 'https://www.nerc.com/pa/ci/Pages/Default.aspx',
    urgent: true,
    sourceColor: 'text-amber-400 bg-amber-950/40 border-amber-800',
  },
  {
    source: 'NSA',
    id: 'CSA U/OO/241840',
    date: '14 SEP 24',
    subject: 'APT34 TTPs targeting US government networks — POWBAT/LIONTAIL IOCs and detection guidance (updated)',
    url: 'https://www.nsa.gov/cybersecurity-advisories/',
    sourceColor: 'text-sky-400 bg-sky-950/40 border-sky-800',
  },
  {
    source: 'CISA',
    id: 'AA24-038A',
    date: '07 FEB 24',
    subject: 'PRC/Iranian joint advisory: pre-positioning on US critical infrastructure — TTPs and mitigations',
    url: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-038a',
    sourceColor: 'text-sky-400 bg-sky-950/40 border-sky-800',
  },
  {
    source: 'CISA',
    id: 'AA23-335A',
    date: '01 DEC 23',
    subject: 'Cyber Av3ngers IRGC MCIS: water/wastewater ICS Unitronics PLC exploitation — detection + mitigation',
    url: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-335a',
    sourceColor: 'text-zinc-400 bg-zinc-900/30 border-zinc-700',
  },
  {
    source: 'CISA',
    id: 'AA22-257A',
    date: '14 SEP 22',
    subject: 'IRGC APT actors compromise US federal network — BitLocker ransomware deployment + IRGC TTP guide',
    url: 'https://www.cisa.gov/news-events/cybersecurity-advisories/aa22-257a',
    sourceColor: 'text-zinc-400 bg-zinc-900/30 border-zinc-700',
  },
]

// ── CISA Known Exploited Vulnerabilities ──────────────────────────────────────

interface KevEntry {
  cve: string
  product: string
  cvss: number
  actor: string
  dateAdded: string
  description: string
}

const KEV_ENTRIES: KevEntry[] = [
  {
    cve: 'CVE-2024-21887',
    product: 'Ivanti ConnectSecure / Policy Secure',
    cvss: 9.1,
    actor: 'APT34 / UTA0178',
    dateAdded: '17 JAN 2024',
    description: 'Command injection in web component. Exploited for initial VPN access to CENTCOM contractor networks — chained with CVE-2023-46805.',
  },
  {
    cve: 'CVE-2023-46805',
    product: 'Ivanti ConnectSecure — Auth Bypass',
    cvss: 8.2,
    actor: 'APT34 / UTA0178',
    dateAdded: '17 JAN 2024',
    description: 'Authentication bypass chained with CVE-2024-21887 for unauthenticated remote access to contractor VPN infrastructure prior to CENTCOM lateral movement.',
  },
  {
    cve: 'CVE-2024-3400',
    product: 'Palo Alto PAN-OS GlobalProtect',
    cvss: 10.0,
    actor: 'UTA0178 (IRGC-nexus)',
    dateAdded: '12 APR 2024',
    description: 'Command injection in GlobalProtect Gateway. Persistent implant established on perimeter devices at three US military-adjacent network segments. CISA emergency directive issued.',
  },
  {
    cve: 'CVE-2022-47966',
    product: 'ManageEngine Multiple Products RCE',
    cvss: 9.8,
    actor: 'APT34 / OilRig',
    dateAdded: '19 JAN 2023',
    description: 'Unauthenticated RCE via SAML authentication endpoint. Used by APT34 for initial foothold in US federal agency and contractor environments — LIONTAIL implant deployed post-exploitation.',
  },
  {
    cve: 'CVE-2021-44228',
    product: 'Apache Log4j2 (Log4Shell)',
    cvss: 10.0,
    actor: 'APT35 / Charming Kitten',
    dateAdded: '10 DEC 2021',
    description: 'Critical JNDI RCE in Java logging library. APT35 conducted mass scanning within hours of disclosure. Still actively exploited in unpatched think-tank and contractor systems as of Day 18.',
  },
]

// ── Border & Port Security ────────────────────────────────────────────────────

interface BorderStatus {
  location: string
  status: string
  detail: string
  color: string
}

const BORDER_STATUS: BorderStatus[] = [
  {
    location: 'CBP — 47 Land Ports of Entry',
    status: 'ELEVATED',
    detail: 'Enhanced secondary screening; biometric cross-referencing with IRGC/HVT watchlist; extended vehicle inspection protocols',
    color: 'text-amber-400',
  },
  {
    location: 'TSA — 35 Major Airports',
    status: 'ELEVATED',
    detail: 'Increased random screening near military installations; enhanced cargo hold inspection; airside access scrutiny heightened',
    color: 'text-amber-400',
  },
  {
    location: 'USCG — Sector New York',
    status: 'MARSEC 2',
    detail: 'All vessels calling Port NY/NJ subject to boarding inspection; patrol assets increased 150% in approaches',
    color: 'text-red-400',
  },
  {
    location: 'USCG — Sector Los Angeles',
    status: 'MARSEC 2',
    detail: 'Port of Long Beach/LA: enhanced access control, increased patrol, commercial diver hull inspections',
    color: 'text-red-400',
  },
  {
    location: 'FBI JTTF — TX / NY / MA / IL',
    status: 'ACTIVE CI OPS',
    detail: 'IRGC surveillance operative arrests confirmed; ongoing counterintelligence in Houston, NYC, Boston, Chicago',
    color: 'text-red-400',
  },
]

// ── Economic Impact ───────────────────────────────────────────────────────────

interface EconIndicator {
  label: string
  value: string
  change: string
  changeColor: string
  source: string
}

const ECON_INDICATORS: EconIndicator[] = [
  { label: 'Brent Crude Spot',        value: '$94.20/bbl',     change: '↑26% since Day 0', changeColor: 'text-amber-400', source: 'Bloomberg ICE' },
  { label: 'WTI NYMEX Spot',          value: '$91.40/bbl',     change: '↑28% since Day 0', changeColor: 'text-amber-400', source: 'CME Group' },
  { label: 'US Regular Gasoline avg', value: '$6.82/gal',      change: '↑127% since Day 0', changeColor: 'text-red-400',   source: 'AAA / EIA' },
  { label: 'Diesel (US avg)',          value: '$7.41/gal',      change: '↑131% since Day 0', changeColor: 'text-red-400',   source: 'EIA' },
  { label: 'LNG Henry Hub',            value: '$12.40/MMbtu',   change: '↑89% since Day 0',  changeColor: 'text-amber-400', source: 'CME Group' },
  { label: 'Medical Supply Delay',     value: '45+ days',       change: '23% rerouted Cape',  changeColor: 'text-amber-400', source: 'WHO / Supply Chain' },
  { label: 'CPI Monthly Impact',       value: '+2.1 pts est.',  change: '30-day projection',  changeColor: 'text-amber-400', source: 'BLS Projection' },
  { label: 'SPR Emergency Release',    value: '50M bbl auth.',  change: 'DOE activated Day 4', changeColor: 'text-sky-400',  source: 'DOE / EIA' },
]

// ── National Intelligence Quick-Links ─────────────────────────────────────────

const INTEL_SOURCES = [
  { label: 'CISA',   url: 'https://www.cisa.gov/news-events/alerts',           color: 'text-red-400    border-red-800    bg-red-950/20' },
  { label: 'DHS',    url: 'https://www.dhs.gov/news-events',                   color: 'text-blue-400   border-blue-800   bg-blue-950/20' },
  { label: 'FBI',    url: 'https://www.fbi.gov/investigate/cyber',             color: 'text-amber-400  border-amber-800  bg-amber-950/20' },
  { label: 'NSA',    url: 'https://www.nsa.gov/cybersecurity-advisories/',     color: 'text-sky-400    border-sky-800    bg-sky-950/20' },
  { label: 'NCTC',   url: 'https://www.nctc.gov/',                             color: 'text-violet-400 border-violet-800 bg-violet-950/20' },
  { label: 'ODNI',   url: 'https://www.dni.gov/index.php/newsroom',            color: 'text-zinc-300   border-zinc-700   bg-zinc-900/20' },
  { label: 'NERC',   url: 'https://www.nerc.com/pa/ci/Pages/Default.aspx',     color: 'text-yellow-400 border-yellow-800 bg-yellow-950/20' },
  { label: 'NRC',    url: 'https://www.nrc.gov/security.html',                 color: 'text-lime-400   border-lime-800   bg-lime-950/20' },
  { label: 'FINCEN', url: 'https://www.fincen.gov/resources/advisories',       color: 'text-emerald-400 border-emerald-800 bg-emerald-950/20' },
  { label: 'IC3',    url: 'https://www.ic3.gov/',                              color: 'text-orange-400 border-orange-800 bg-orange-950/20' },
  { label: 'CISA KEV', url: 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog', color: 'text-rose-400 border-rose-800 bg-rose-950/20' },
]

// ── Page ─────────────────────────────────────────────────────────────────────

export default function HomelandPage() {
  return (
    <section className="space-y-6 max-w-screen-xl">

      {/* ── Cinematic Homeland Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(239,68,68,0.012) 2px, rgba(239,68,68,0.012) 4px)'}} />
          <div className="relative z-[3] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Home size={26} className="text-red-400 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-widest text-red-400 glow-red">
                  CONUS HOMELAND DEFENSE OPERATIONS
                </h1>
                <p className="text-[11px] text-zinc-500 tracking-wider mt-0.5">
                  DAY {CONFLICT_DAY} · {toShortDate(CONFLICT_DAY)} · ALL-SOURCE ASSESSMENT
                </p>
              </div>
            </div>
            <div className="text-right space-y-1">
              <div className="on-air-badge inline-block bg-red-900/60 text-red-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-red-800/60">
                ● NTAS ELEVATED
              </div>
              <div className="text-[9px] text-zinc-600 mt-0.5">DHS · CISA · FBI JTTF</div>
              <ShareButton
                title="Homeland Threat Brief — Epic Fury War Dashboard"
                text={`Day ${CONFLICT_DAY} Homeland Threat Status: NTAS Elevated — IRGC surveillance of CONUS CI confirmed`}
              />
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" />
      </div>

      {/* Live feeds — cyber/homeland intel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <LiveNewsBoard limit={20} warFilter={false} compact={false} />
        <TheaterIntelFeed theater="Cyber" limit={12} />
      </div>

      {/* NTAS Banner — cinematic critical */}
      <div className="video-feed-frame tac-card tac-card-critical border-red-900/70 bg-red-950/10 p-4 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
          <span className="text-[7px] text-red-400/60 font-bold tracking-[0.2em]">NTAS LIVE</span>
        </div>
        <div className="flex items-start gap-3">
          <AlertTriangle size={16} className="text-red-400 animate-pulse shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-3 flex-wrap">
              <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase">
                DHS · National Terrorism Advisory System
              </p>
              <span className="text-[9px] font-bold tracking-widest text-red-400 border border-red-800 bg-red-950/40 px-2 py-0.5 rounded-sm uppercase animate-pulse">
                ● ELEVATED
              </span>
              <span className="text-[9px] text-zinc-600 tracking-widest">
                {NTAS_BULLETIN.id} · ISSUED {NTAS_BULLETIN.issued} · {NTAS_BULLETIN.expires}
              </span>
            </div>
            <p className="text-xs font-bold text-red-300 tracking-wider uppercase leading-snug">
              {NTAS_BULLETIN.title}
            </p>
          </div>
        </div>
        <p className="text-[10px] text-zinc-400 leading-relaxed border-t border-red-900/40 pt-3">
          {NTAS_BULLETIN.summary}
        </p>
        <div className="flex flex-wrap items-center gap-4">
          {[
            { label: 'DHS NTAS',    url: 'https://www.dhs.gov/ntas' },
            { label: 'CISA Alerts', url: 'https://www.cisa.gov/news-events/alerts' },
            { label: 'FBI CT',      url: 'https://www.fbi.gov/investigate/counterterrorism' },
            { label: 'CISA KEV',    url: 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog' },
            { label: 'IC3 Report',  url: 'https://www.ic3.gov/' },
          ].map(({ label, url }) => (
            <a
              key={label}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-[10px] text-red-600 hover:text-red-400 tracking-widest uppercase transition-all min-h-[36px] px-2.5 rounded-md hover:bg-red-950/30 active:scale-95"
            >
              {label} <ExternalLink size={8} />
            </a>
          ))}
        </div>
      </div>

      {/* Intelligence Source Quick-Links */}
      <div>
        <p className="text-[9px] text-zinc-600 tracking-widest uppercase mb-2">Official US Intelligence & Security Sources</p>
        <div className="flex flex-wrap gap-1.5">
          {INTEL_SOURCES.map(({ label, url, color }) => (
            <a
              key={label}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'text-[9px] font-bold tracking-widest px-3 py-2 min-h-[36px] flex items-center border rounded-lg uppercase transition-all hover:opacity-80 active:scale-95',
                color,
              )}
            >
              {label} ↗
            </a>
          ))}
        </div>
      </div>

      {/* CI Domain Grid — cinematic */}
      <div>
        <p className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase mb-2">
          Critical Infrastructure Threat Status — CISA 16 Sectors (Priority Filtered)
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
          {CI_DOMAINS.map(({ label, level, dot, text, detail, levelText, levelBg }) => (
            <div key={label} className={cn('tac-card data-card-glow rounded-sm p-3 border space-y-1.5 relative overflow-hidden', levelBg)}>
              <div className="absolute inset-0 pointer-events-none" style={{background: level === 'HIGH' ? 'radial-gradient(ellipse at top, rgba(239,68,68,0.04), transparent 70%)' : 'none'}} />
              <div className="flex items-center gap-1.5">
                <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', dot, level === 'HIGH' ? 'animate-pulse' : '')} />
                <span className={cn('text-[9px] font-bold tracking-widest uppercase', text)}>
                  {label}
                </span>
              </div>
              <span className={cn('text-[8px] font-bold tracking-widest uppercase', levelText)}>{level}</span>
              <p className="text-[8px] text-zinc-600 leading-relaxed line-clamp-3">{detail}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 2-col: APT Campaigns + Federal Advisories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* APT Campaign Tracker */}
        <div className="lg:col-span-2 space-y-2">
          <p className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase">
            IRGC-Attributed APT Campaign Tracker — CONUS Active Targeting
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {APT_CAMPAIGNS.map((apt) => (
              <div
                key={apt.name}
                className={cn(
                  'tac-card rounded-sm p-3 space-y-1.5 border-l-2',
                  apt.borderColor,
                  apt.bgColor,
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className={cn('text-[10px] font-bold tracking-widest uppercase truncate', apt.statusColor)}>
                      {apt.name}
                    </p>
                    <p className="text-[8px] text-zinc-600 tracking-wider truncate">{apt.aliases}</p>
                  </div>
                  <div className="flex flex-col items-end gap-0.5 shrink-0">
                    <span
                      className={cn(
                        'text-[8px] font-bold tracking-widest border px-1 py-0.5 rounded-sm uppercase',
                        apt.statusColor,
                        apt.borderColor,
                      )}
                    >
                      {apt.status}
                    </span>
                    <span className="text-[8px] text-zinc-600">{apt.confidence}% CONF</span>
                  </div>
                </div>
                <p className="text-[9px] text-zinc-500 tracking-wider">
                  <span className="text-zinc-400">Sector:</span> {apt.sector}
                </p>
                <p className="text-[9px] text-zinc-500 tracking-widest leading-relaxed">
                  <span className="text-zinc-500">TTPs:</span>{' '}
                  <span className="text-zinc-600">{apt.ttps}</span>
                </p>
                <p className="text-[9px] text-zinc-400 leading-relaxed">{apt.detail}</p>
                <div className="flex items-center justify-between pt-0.5 border-t border-zinc-900">
                  <span className="text-[8px] text-zinc-700">Last seen: {apt.lastSeen}</span>
                  <a
                    href={apt.advisoryUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-0.5 text-[8px] text-zinc-600 hover:text-emerald-500 tracking-widest transition-colors"
                  >
                    {apt.advisoryId} <ExternalLink size={7} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Federal Advisories */}
        <div className="space-y-2">
          <p className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase">
            Active Federal Advisories
          </p>
          <div className="space-y-1.5">
            {FEDERAL_ADVISORIES.map((adv) => (
              <a
                key={adv.id}
                href={adv.url}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  'flex items-start gap-2 tac-card rounded-sm p-2.5 border-l-2 hover:border-l-emerald-600 transition-colors group',
                  adv.urgent ? 'border-l-red-700' : 'border-l-zinc-700',
                )}
              >
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={cn(
                        'text-[8px] font-bold tracking-widest border px-1 py-0.5 rounded-sm uppercase shrink-0',
                        adv.sourceColor,
                      )}
                    >
                      {adv.source}
                    </span>
                    <span className="text-[8px] text-zinc-600 tracking-widest shrink-0">{adv.id}</span>
                    {adv.urgent && (
                      <span className="text-[8px] font-bold text-red-500 tracking-widest shrink-0 animate-pulse">
                        URGENT
                      </span>
                    )}
                  </div>
                  <p className="text-[9px] text-zinc-400 leading-relaxed group-hover:text-zinc-300 transition-colors">
                    {adv.subject}
                  </p>
                  <p className="text-[8px] text-zinc-700">{adv.date}</p>
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* CISA KEV Table — cinematic */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <p className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase">
            CISA Known Exploited Vulnerabilities — Actively Exploited by Iranian APTs
          </p>
          <a
            href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-0.5 text-[9px] text-emerald-700 hover:text-emerald-500 tracking-widest uppercase transition-colors"
          >
            Full KEV Catalog <ExternalLink size={8} />
          </a>
        </div>
        <div className="video-feed-frame tac-card rounded-sm overflow-x-auto relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-amber-500/60 font-bold tracking-[0.2em]">KEV DB</span>
          </div>
          <table className="w-full text-xs min-w-[750px]">
            <thead>
              <tr className="border-b border-zinc-800">
                {['CVE', 'Product / Component', 'CVSS', 'Attributed Actor', 'Date Added to KEV', 'Context'].map(
                  (h) => (
                    <th
                      key={h}
                      className="text-left text-[9px] tracking-widest text-zinc-600 uppercase px-3 py-2 font-medium"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {KEV_ENTRIES.map((kev) => (
                <tr key={kev.cve} className="hover:bg-zinc-800/20 transition-colors">
                  <td className="px-3 py-2.5">
                    <a
                      href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-red-400 hover:text-red-300 font-mono tracking-wide text-[10px] whitespace-nowrap transition-colors flex items-center gap-1"
                    >
                      {kev.cve} <ExternalLink size={7} />
                    </a>
                  </td>
                  <td className="px-3 py-2.5 text-zinc-300 text-[10px] tracking-wide">{kev.product}</td>
                  <td className="px-3 py-2.5">
                    <span
                      className={cn(
                        'text-[10px] font-bold tracking-widest',
                        kev.cvss >= 9.0 ? 'text-red-400' : kev.cvss >= 7.0 ? 'text-amber-400' : 'text-yellow-400',
                      )}
                    >
                      {kev.cvss.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-amber-400/80 text-[9px] tracking-widest whitespace-nowrap">
                    {kev.actor}
                  </td>
                  <td className="px-3 py-2.5 text-zinc-600 text-[9px] tracking-widest whitespace-nowrap">
                    {kev.dateAdded}
                  </td>
                  <td className="px-3 py-2.5 text-zinc-500 text-[9px] leading-relaxed">{kev.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2-col: Border Security + Economic Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Border & Port Security */}
        <div className="tac-card p-5 space-y-3 relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(245,158,11,0.02) 0%, transparent 50%)'}} />
          <div className="tac-section-header relative z-[1]">
            <MapPin size={12} className="text-amber-400 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]" />
            <span className="glow-amber">Border &amp; Port Security Status</span>
          </div>
          <div className="space-y-2.5">
            {BORDER_STATUS.map((bs) => (
              <div key={bs.location} className="flex items-start gap-3 border-b border-zinc-900 pb-2 last:border-0">
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-bold tracking-widest text-zinc-300 uppercase">{bs.location}</p>
                  <p className="text-[9px] text-zinc-600 leading-relaxed mt-0.5">{bs.detail}</p>
                </div>
                <span className={cn('text-[9px] font-bold tracking-widest shrink-0 whitespace-nowrap', bs.color)}>
                  {bs.status}
                </span>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-zinc-700 tracking-widest border-t border-zinc-900 pt-2">
            Sources:{' '}
            <a href="https://www.cbp.gov" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 transition-colors">CBP</a>
            {' · '}
            <a href="https://www.tsa.gov" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 transition-colors">TSA</a>
            {' · '}
            <a href="https://www.uscg.mil" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 transition-colors">USCG</a>
            {' · '}
            <a href="https://www.fbi.gov/investigate/counterterrorism" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 transition-colors">FBI JTTF</a>
          </p>
        </div>

        {/* Economic Impact */}
        <div className="tac-card p-5 space-y-3">
          <div className="tac-section-header">
            <DollarSign size={12} className="text-lime-400" />
            <span>Homeland Economic Impact — Day {CONFLICT_DAY}</span>
          </div>
          <div className="space-y-2">
            {ECON_INDICATORS.map((ind) => (
              <div
                key={ind.label}
                className="flex items-center justify-between border-b border-zinc-900 pb-1.5 last:border-0"
              >
                <div>
                  <p className="text-[10px] text-zinc-500 tracking-widest">{ind.label}</p>
                  <p className="text-[8px] text-zinc-700">{ind.source}</p>
                </div>
                <div className="text-right">
                  <p className={cn('text-xs font-bold tabular-nums', ind.changeColor)}>{ind.value}</p>
                  <p className={cn('text-[8px] tracking-widest', ind.changeColor)}>{ind.change}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-zinc-700 tracking-widest border-t border-zinc-900 pt-2">
            Sources: Bloomberg · AAA ·{' '}
            <a href="https://www.eia.gov" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 transition-colors">EIA</a>
            {' · CME Group · '}
            <a href="https://www.bls.gov" target="_blank" rel="noopener noreferrer" className="hover:text-emerald-600 transition-colors">BLS</a>
          </p>
        </div>
      </div>

      {/* JTTF Active Investigations + DoD CONUS Installation Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* JTTF Active Investigations */}
        <div className="video-feed-frame tac-card p-5 space-y-3 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-10 z-[4] flex items-center gap-2">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <span className="text-[8px] text-red-400/80 font-bold tracking-[0.25em]">REC</span>
          </div>
          <div className="tac-section-header relative z-[1]">
            <AlertTriangle size={12} className="text-red-400 drop-shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            <span className="glow-red">FBI/JTTF Active Investigations — Day {CONFLICT_DAY}</span>
            <span className="ml-auto text-[9px] text-red-600 normal-case font-normal tracking-widest animate-pulse">12 OPEN</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[9px]">
              <thead>
                <tr className="border-b border-zinc-800">
                  {['Case #', 'Subject', 'Domain', 'Status', 'Field Office'].map((h) => (
                    <th key={h} className="text-left text-[8px] text-zinc-600 tracking-widest uppercase pb-1.5 pr-2 font-normal whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {[
                  { case: 'CP-26-0041', subject: 'IRGCQF-linked sleeper cell surveillance — NY Metro',  domain: 'CT',      status: 'ACTIVE / SURVEILLING', office: 'NY Field', sc: 'text-red-400' },
                  { case: 'CP-26-0044', subject: 'APT34 OT implant — Midwest EMS operator',             domain: 'CYBER',   status: 'INDICTED',             office: 'Chicago',  sc: 'text-emerald-400' },
                  { case: 'CP-26-0047', subject: 'Suspected IRGC courier network — TX / NM border',     domain: 'CT/BORDER',status: 'ACTIVE / ARREST PEND', office: 'Houston',  sc: 'text-amber-400' },
                  { case: 'CP-26-0049', subject: 'Iranian-linked financial SMFF — shell company LA',    domain: 'FINANCE', status: 'ACTIVE / GRAND JURY',  office: 'Los Angeles',sc:'text-amber-400' },
                  { case: 'CP-26-0051', subject: 'Pre-operational surveillance — San Diego NB',          domain: 'MILITARY',status: 'ACTIVE / SURVEILLING', office: 'San Diego',  sc: 'text-red-400' },
                  { case: 'CP-26-0053', subject: 'Moses Staff wiper suspect — defense contractor MI',   domain: 'CYBER',   status: 'ARREST WARRANT',       office: 'Detroit',  sc: 'text-red-400' },
                  { case: 'CP-26-0055', subject: 'Crypto sanctions evasion — OFAC coordination',        domain: 'FINANCE', status: 'ACTIVE / CIVIL',       office: 'NY Field', sc: 'text-zinc-400' },
                  { case: 'CP-26-0058', subject: 'Farsi-language incitement / material support inquiry',domain: 'CT',      status: 'PRELIMINARY',          office: 'DC Field', sc: 'text-zinc-500' },
                ].map(({ case: c, subject, domain, status, office, sc }) => (
                  <tr key={c} className="hover:bg-zinc-900/30 transition-colors">
                    <td className="text-zinc-600 pr-2 py-1.5 whitespace-nowrap tabular-nums">{c}</td>
                    <td className="text-zinc-400 pr-2 py-1.5 leading-snug max-w-[170px]">{subject}</td>
                    <td className="text-sky-500 pr-2 py-1.5 whitespace-nowrap tracking-widest">{domain}</td>
                    <td className={cn('pr-2 py-1.5 whitespace-nowrap font-bold tracking-widest', sc)}>{status}</td>
                    <td className="text-zinc-600 py-1.5 whitespace-nowrap">{office}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[8px] text-zinc-700 tracking-widest border-t border-zinc-900 pt-1.5">
            ⚠ Case numbers, subjects, and field offices are AI-synthesized from open-source reporting. FBI JTTF operations cited reference publicly reported Iranian CT activities 2022–2026.{' '}
            <a href="https://www.fbi.gov/investigate/counterterrorism" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 transition-colors">FBI CT</a>
          </p>
        </div>

        {/* DoD CONUS Installation Security */}
        <div className="tac-card p-5 space-y-3">
          <div className="tac-section-header">
            <Home size={12} className="text-sky-400" />
            <span>DoD CONUS Installation Security — Day {CONFLICT_DAY}</span>
          </div>
          <div className="space-y-2.5">
            {[
              { installation: 'NSA Fort Meade (MD)',             fpcon: 'CHARLIE', threat: 'Cyber reconnaissance detected on base perimeter NOSs — DIA bulletin Day 16', color: 'text-red-400',    bg: 'bg-red-950/20 border-red-900/50' },
              { installation: 'CENTCOM HQ — MacDill AFB (FL)',   fpcon: 'CHARLIE', threat: 'IRGCQF surveillance of staff housing near base — FBI JTTF CP-26-0051 parallel', color: 'text-red-400',    bg: 'bg-red-950/20 border-red-900/50' },
              { installation: 'Naval Station Norfolk (VA)',       fpcon: 'BRAVO+',  threat: 'Enhanced waterside security; MARSEC 2 in effect; vehicle barriers extended', color: 'text-amber-400',   bg: 'bg-amber-950/20 border-amber-900/50' },
              { installation: 'Peterson SFB — Space Command (CO)',fpcon: 'BRAVO+',  threat: 'SATCOM uplink facility hardened; cyber monitoring elevated post-APT35 activity', color: 'text-amber-400',   bg: 'bg-amber-950/20 border-amber-900/50' },
              { installation: 'Edwards AFB (CA)',                 fpcon: 'BRAVO',   threat: 'B-21 Raider maintenance security enhanced; foreign national access suspended', color: 'text-yellow-400',  bg: 'bg-yellow-950/15 border-yellow-900/40' },
              { installation: 'Kirtland AFB — Nuclear Weapons Center (NM)', fpcon: 'CHARLIE', threat: 'Nuclear weapon storage security: highest tier protocols enforced; NRC coordination', color: 'text-red-400', bg: 'bg-red-950/20 border-red-900/50' },
              { installation: 'JBSA-Randolph / Lackland (TX)',   fpcon: 'BRAVO',   threat: 'Personnel records facility enhanced access control; OPSEC briefing mandatory', color: 'text-yellow-400',  bg: 'bg-yellow-950/15 border-yellow-900/40' },
            ].map(({ installation, fpcon, threat, color, bg }) => (
              <div key={installation} className={cn('rounded border p-2.5 space-y-0.5', bg)}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-bold text-zinc-300">{installation}</span>
                  <span className={cn('text-[8px] font-bold tracking-widest shrink-0', color)}>FPCON {fpcon}</span>
                </div>
                <p className="text-[9px] text-zinc-500">{threat}</p>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-zinc-700 tracking-widest border-t border-zinc-900 pt-1.5">
            FPCON levels are AI-assessed estimates based on open-source threat reporting. DoD Installation FPCON per AR 525-13.{' '}
            <a href="https://www.defense.gov/" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-400 transition-colors">DoD.gov</a>
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="tac-card border-zinc-800 bg-zinc-900/20 p-3">
        <p className="text-[9px] text-zinc-700 leading-relaxed">
          ⚠ UNCLASSIFIED // AI LIVE ANALYSIS — Advisory IDs, CVE data, and agency citations reference real public
          sources. This is an AI-synthesized open-source intelligence product. CISA advisories AA22-257A, AA23-335A,
          AA23-165A, AA24-038A are real CISA publications. CVE data drawn from the public{' '}
          <a
            href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-700 hover:text-emerald-500 transition-colors"
          >
            CISA KEV catalog
          </a>
          . For live threat intelligence consult{' '}
          <a href="https://www.cisa.gov" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-500 transition-colors">
            cisa.gov
          </a>
          ,{' '}
          <a href="https://www.dhs.gov/ntas" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-500 transition-colors">
            dhs.gov/ntas
          </a>
          , and{' '}
          <a href="https://www.fbi.gov" target="_blank" rel="noopener noreferrer" className="text-emerald-700 hover:text-emerald-500 transition-colors">
            fbi.gov
          </a>
          .
        </p>
      </div>

    </section>
  )
}
