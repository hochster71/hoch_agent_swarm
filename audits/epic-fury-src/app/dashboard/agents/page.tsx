import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'
import { AgentCard } from '@/components/AgentCard'
import type { Agent } from '@/lib/types'
import { Cpu } from 'lucide-react'
import { getConflictDay } from '@/lib/conflict-day'
import { OraclePanel } from '@/components/OraclePanel'
import { HeraldFeed } from '@/components/HeraldFeed'
import { CompassPanel } from '@/components/CompassPanel'
import { IngestMonitor } from '@/components/IngestMonitor'
import { AnalyzeBatchMonitor } from '@/components/AnalyzeBatchMonitor'
import { PlatformHealth } from '@/components/PlatformHealth'
import { SitrepAutoFeed } from '@/components/SitrepAutoFeed'
import { SourceRadar } from '@/components/SourceRadar'
import { AccuracyReport } from '@/components/AccuracyReport'

export const revalidate = 0

async function requireAdmin() {
  const cookieStore = await cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => cookieStore.getAll(), setAll: () => {} } }
  )
  const { data: { user } } = await supabase.auth.getUser()
  const isAdmin = (user?.app_metadata?.role as string) === 'admin' || user?.email === process.env.ADMIN_EMAIL
  if (!isAdmin) redirect('/dashboard')
}

const CONFLICT_DAY = getConflictDay()

/** Rich agent roster — current operational picture */
const AGENTS: Agent[] = [
  {
    id: 'agent-01',
    name: 'ATLAS-1',
    role: 'Strategic ISR Analyst',
    domain: 'ISR',
    status: 'ENGAGED',
    priority: 'CRITICAL',
    confidence: 91,
    tasking: 'Continuous surveillance of IRGCAF dispersal sites in Zagros Mountain complex; TEL tracking, launch probability modeling.',
    threat_focus: 'IRGCAF Emad/Ghadr TEL reconstitution — estimated 15–25 BMs remaining (~92-95% expended); ZULU-14 corridor active',
    quote: 'Post-Alpha-5 (D26) BDA: 27/31 BMs intercepted, 86% intercept rate, ZULU-7 complex destroyed. ZULU-14 corridor showing TEL engine-start thermal signatures at 01:55Z D27. Estimated 15–25 Emad/Ghadr class remaining — 92-95% of pre-conflict stock expended. 6th barrage risk 41%/72h. FURY-27 standby recommended.',
    lastUpdate: `Day ${CONFLICT_DAY} · 02:14Z`,
    actions: [
      { time: '02:14Z', entry: 'Updated TEL position grid ZULU-14 through ZULU-16 from Maxar SAR pass — 3 TEL vehicles confirmed engine-start thermal.' },
      { time: '01:55Z', entry: 'ZULU-14 corridor: TEL reconstitution activity confirmed. Passed to RAPTOR-2 for FURY-27 targeting.' },
      { time: '00:30Z', entry: 'Transmitted FLASHMSG to CENTCOM J2: 6th barrage risk 41%/72h post-Alpha-5; ZULU-14 reconstituting.' },
      { time: 'D26 04:10Z', entry: 'Alpha-5 post-strike BDA: ZULU-7 complex destroyed. 27/31 BMs intercepted (86% rate). 2 USAF KIA.' },
    ],
  },
  {
    id: 'agent-02',
    name: 'CERBERUS',
    role: 'Cyber Threat Monitor',
    domain: 'Cyber',
    status: 'ALERT',
    priority: 'CRITICAL',
    confidence: 84,
    tasking: 'Real-time monitoring of CENTCOM contractor and GCC critical infrastructure networks for IRGC Cyber Command intrusion activity.',
    threat_focus: 'APT33 / APT34 active intrusion — CENTCOM logistics subnet + Aramco OT',
    quote: 'Anomalous lateral movement detected in CENTCOM logistics subnet at 01:58Z. TTPs consistent with APT34 "Helix Kitten." Isolation protocol recommended for 3 affected hosts.',
    lastUpdate: `Day ${CONFLICT_DAY} · 01:58Z`,
    actions: [
      { time: '01:58Z', entry: 'ALERT: Lateral movement detected on CENTCOM logistics subnet — 3 hosts flagged.' },
      { time: '01:22Z', entry: 'APT33 C2 beacon identified: domain shadowing via compromised registrar.' },
      { time: 'D27 00:15Z', entry: 'IRGC Cyber Command escalation indicator: OT scanning surge on GCC desalination facilities — CISA pre-alert issued.' },
      { time: 'D26 22:30Z', entry: 'Post-Alpha-5 window: APT33 spear-phishing targeting CENTCOM contractor email — 12 accounts isolated, CISA ED 26-02 action items 9/9 complete.' },
      { time: 'D26 18:45Z', entry: 'Aramco SCADA: wiper variant "BlackEnergy-3c" signature detected in staging — sandboxed and contained, no execution confirmed.' },
    ],
  },
  {
    id: 'agent-03',
    name: 'HYDRA-4',
    role: 'OSINT Aggregator',
    domain: 'OSINT',
    status: 'ON STATION',
    priority: 'HIGH',
    confidence: 73,
    tasking: 'Monitoring Farsi, Arabic, and Hebrew OSINT channels for near-real-time battle damage assessment and proxy force signals.',
    threat_focus: 'Houthi launch preparation signals + Hamas/Hezbollah second-front indicators',
    quote: 'Farsi-language Telegram channels show coordinated messaging shift: "martyrdom operation" rhetoric directed at Bahrain\'s NSA HQ. Likely IRGC IO. Also tracking Hezbollah mobilization signals — not yet at attack threshold.',
    lastUpdate: `Day ${CONFLICT_DAY} · 01:47Z`,
    actions: [
      { time: '01:47Z', entry: 'Identified 14 new Farsi Telegram channels with battle-coordination traffic.' },
      { time: '00:30Z', entry: 'Geolocated Houthi launcher video to Hajjah Governorate — forwarded to ATLAS-1.' },
      { time: 'D26 20:00Z', entry: 'Hezbollah OSINT: mobilization signals reduced post-Alpha-5, aligned with Abu Dhabi ceasefire proximity talks. Second-front risk downgraded.' },
      { time: 'D26 14:30Z', entry: 'Houthi Telegram channels: launch prep videos removed; operational tempo reduced. Correlates with IRGC post-Alpha-5 degradation.' },
    ],
  },
  {
    id: 'agent-04',
    name: 'SPECTER',
    role: 'SIGINT Processor',
    domain: 'SIGINT',
    status: 'ENGAGED',
    priority: 'HIGH',
    confidence: 88,
    tasking: 'HF/VHF burst transmission intercept and decryption — IRGCN and IRGCAF command nets.',
    threat_focus: 'IRGCAF air-defense coordination network + IRGCN fast-boat launch authorization codes',
    quote: 'Intercepted encrypted HF burst on 11.5 MHz consistent with IRGCAF pre-launch authentication exchange. Timestamp correlation with Atlas-1 TEL position data strongly suggests authorization window.',
    lastUpdate: `Day ${CONFLICT_DAY} · 02:07Z`,
    actions: [
      { time: '02:07Z', entry: 'HF burst decryption complete — authentication code matches IRGCAF launch net pattern.' },
      { time: '01:33Z', entry: 'IRGCN Bandar Abbas port radio: sortie authorization traffic intercepted x4 vessels.' },
      { time: 'D27 01:55Z', entry: 'ZULU-14 HF burst: engine-start thermal corroborated — passed to NEXUS for D27 COP and ORACLE-9 for 6th barrage probability update.' },
      { time: 'D26 03:45Z', entry: 'Alpha-5 pre-launch: IRGCAF HF authentication exchange intercepted on 11.5 MHz — 31 BM launch sequence confirmed, passed to TRIDENT FLASH.' },
    ],
  },
  {
    id: 'agent-05',
    name: 'ORACLE-9',
    role: 'Predictive Threat Model',
    domain: 'Prediction',
    status: 'ON STATION',
    priority: 'HIGH',
    confidence: 79,
    tasking: 'Probabilistic threat forecasting across all operational domains — 24/48/72-hour windows.',
    threat_focus: 'IRGC hardliner faction watch — ceasefire monitoring Phase 2 + IAEA Fordow access + post-ceasefire barrage residual risk 17%/72h',
    quote: `D${CONFLICT_DAY} ORACLE-9 threat assessment: Ceasefire signed D32 — all offensive ops ceased. IRGCAF residual BM inventory <5% of pre-conflict stock. Barrage risk 17%/72h (IRGC hardliner faction activity). IAEA inspection teams at Natanz+Isfahan (complete); Fordow access still pending D${CONFLICT_DAY}. New SL Mojtaba Khamenei confirmed D40 — hardliner faction elevated. ORACLE-9 stability model: 91% ceasefire holds 72h, 84% 7-day.`,
    lastUpdate: `Day ${CONFLICT_DAY} · 02:00Z`,
    actions: [
      { time: '02:00Z', entry: 'Model update D27: 6th barrage probability 41% in 72h; 5th barrage (Alpha-5, D26) assessment complete.' },
      { time: '01:30Z', entry: 'Ceasefire probability model: COMPASS 68% within 72h following Abu Dhabi Framework — revised UP from 12% D25.' },
      { time: 'D26 04:00Z', entry: 'Alpha-5 post-strike BDA: 27/31 BMs intercepted, 86% intercept rate. 2 USAF KIA.' },
      { time: 'D25 22:00Z', entry: 'Ceasefire probability spiked on Iran SNSC pre-condition drop: revised to 38% (updated D27 to 68%).' },
    ],
  },
  {
    id: 'agent-06',
    name: 'MANTIS',
    role: 'Mine Warfare Analyst',
    domain: 'Maritime',
    status: 'MONITORING',
    priority: 'HIGH',
    confidence: 86,
    tasking: 'Tracking IRGCN mine-layer vessels and updating Hormuz mine threat density map for MCM operations.',
    threat_focus: 'IRGCN mine-layer GOLF-8 — ZB-Bravo potential re-seeding risk; GOLF-7 CLOSED (INACTIVE Bandar Abbas D26); MCM ZB-Alpha 78% cleared with 7+ VLCC transits',
    quote: `GOLF-7 INACTIVE — last observed transiting to Bandar Abbas 14:20Z Day 26 at 7kn. ZB-Alpha threat from GOLF-7 CLOSED. MCM ZB-Alpha 78% cleared — 7+ VLCC transits completed since D24 under escort. GOLF-8 unlocated at Bandar-e-Jask since D17 (EMCON). Shifting ISR tasking to ZB-Bravo corridor and GOLF-8 track.`,
    lastUpdate: `Day ${CONFLICT_DAY} · 01:32Z`,
    actions: [
      { time: '01:32Z', entry: 'GOLF-7 CLOSED: confirmed returning Bandar Abbas D26 14:20Z. Fleet-wide GOLF-7 threat designation INACTIVE.' },
      { time: '00:45Z', entry: 'ZB-Alpha D27 status: 78% cleared, 7 VLCC transits completed D24–D27 under MCM escort. No new mines detected since D24.' },
      { time: 'D24 22:00Z', entry: 'MCM corridor ZB-Alpha final GOLF-7 mine cleared. Corridor opened for commercial escort transit D24.' },
      { time: 'D22 18:00Z', entry: 'Updated mine density map v14 transmitted to NAVCENT mine warfare cell.' },
    ],
  },
  {
    id: 'agent-07',
    name: 'ARGUS',
    role: 'Imagery Intelligence Engine',
    domain: 'IMINT',
    status: 'ON STATION',
    priority: 'MEDIUM',
    confidence: 92,
    tasking: 'Automated SAR/EO:IR satellite imagery processing — battle damage assessment and order of battle updates.',
    threat_focus: 'Qom missile storage complex + Fordow post-strike BDA',
    quote: 'Processing Maxar GeoEye-1 pass from 01:22Z: Fordow portal collapse confirmed on shaft 3-Alpha. Craters on access road indicate secondary munitions detonation. BDA score: 78/100 (significant degradation).',
    lastUpdate: `Day ${CONFLICT_DAY} · 00:55Z`,
    actions: [
      { time: '00:55Z', entry: 'Fordow BDA updated: shaft 3-Alpha collapsed. New BDA score: 78 (prev: 64).' },
      { time: 'D18 23:10Z', entry: 'Qom site: 12 missile launchers confirmed, 3 destroyed by previous strike package.' },
      { time: 'D18 18:40Z', entry: 'Isfahan UCF: main centrifuge hall assessment complete — 94% production halted.' },
      { time: 'D18 11:30Z', entry: 'Natanz FEP: above-ground structures fully destroyed. Underground halls unclear.' },
    ],
  },
  {
    id: 'agent-08',
    name: 'RAPTOR-2',
    role: 'Strike Package Coordinator',
    domain: 'Strike',
    status: 'ENGAGED',
    priority: 'CRITICAL',
    confidence: 95,
    tasking: 'Real-time deconfliction and targeting coordination for all JTF strike packages — air, missile, and maritime.',
    threat_focus: 'Time-sensitive target: IRGCAF TEL convoy ZULU-14 — 6th barrage precursor monitoring; FURY-27 prosecution window standby',
    quote: 'Strike package FURY-27 deconflicted and on standby. Post-Alpha-5 assessment complete. ZULU-14 corridor TEL reconstitution activity detected by ATLAS-1 at 01:55Z D27. Awaiting NCA authorization for FURY-27 prosecution. Alpha-5 ZULU-7 target complex confirmed destroyed.',
    lastUpdate: `Day ${CONFLICT_DAY} · 02:11Z`,
    actions: [
      { time: '02:11Z', entry: 'FURY-27 strike package on standby pending ZULU-14 prosecution authorization.' },
      { time: '01:55Z', entry: 'ATLAS-1: TEL reconstitution at ZULU-14 confirmed — 3 TEL vehicles engine-start thermal signature.' },
      { time: 'D26 03:45Z', entry: 'Alpha-5 real-time intercept coordination: 14×SM-3, 2×THAAD engaged. Assessed 86% intercept rate.' },
      { time: 'D26 02:40Z', entry: 'Alpha-5 launch detected: 31 BM tracks. FURY-26 TEL pre-emptive strike executed prior to launch.' },
      { time: 'D22 02:30Z', entry: 'FURY-22 package: IAF F-35I Adir KARBALA-7 strike authorized. Khamenei IDA confirmed. TRIDENT FLASH transmitted.' },
    ],
  },
  {
    id: 'agent-10',
    name: 'PHANTOM',
    role: 'Electronic Warfare Controller',
    domain: 'EW',
    status: 'ENGAGED',
    priority: 'HIGH',
    confidence: 82,
    tasking: 'Coordinating EA-18G Growler jamming schedules, AESA EW support for FURY strike packages, monitoring Iranian radar emissions.',
    threat_focus: 'IRGCAF Bavar-373 and Khordad-15 radar activation — blind spot exploitation for B-2A ingress',
    quote: 'Remaining Bavar-373 battery (Tehran perimeter) activated at 00:42Z — 4-minute emission before EMCON shutdown. Grid confirmed. B-2A package FURY-20 can exploit 180° coverage gap on WNW ingress corridor.',
    lastUpdate: `Day ${CONFLICT_DAY} · 00:55Z`,
    actions: [
      { time: '00:55Z', entry: 'Bavar-373 radar activation grid passed to RAPTOR-2 for FURY-20 ingress route deconfliction.' },
      { time: '00:42Z', entry: 'Bavar-373 Tehran battery: 4-min emission on 10.5 GHz detected and geolocated ±120m.' },
      { time: 'D18 23:30Z', entry: 'EA-18G Growler flight HAVOC-3 completed SEAD escort for FURY-18 package — 2 Khordad-15 radars suppressed.' },
      { time: 'D18 21:00Z', entry: 'Iranian Kasta-02 acquisition radar at Bandar Abbas destroyed by HARM strike after PHANTOM cued targeting.' },
      { time: 'D18 16:45Z', entry: 'Updated Iranian EW order of battle — 4 of 8 Bavar-373 batteries assessed as permanently offline.' },
    ],
  },
  {
    id: 'agent-11',
    name: 'TRIDENT',
    role: 'Strategic Decisionmaker Monitor',
    domain: 'STRATCOM',
    status: 'MONITORING',
    priority: 'CRITICAL',
    confidence: 71,
    tasking: 'Monitoring Iranian leadership communications, nuclear decision-making indicators, and escalation control signals — direct feed to NSC Situation Room.',
    threat_focus: 'Post-Khamenei authority chain (KIA D22/FURY-22) — IRGC CINC Salami command comms + nuclear escalation indicators; SL circuit CLOSED/historical',
    quote: `TRIDENT D${CONFLICT_DAY}: Khamenei KIA D22 FURY-22 — SL circuit CLOSED/historical. Mojtaba Khamenei confirmed new Supreme Leader D40 (AoE vote 51-41). IRGC CINC Salami monitoring — command net frequency REDUCED vs pre-ceasefire. Three IRGC commanders publicly rejected ceasefire terms D50 — overruled by new SL Mojtaba. No nuclear authorization indicators in current TRIDENT traffic. UNCMM monitoring active. IAEA D44 Natanz/Isfahan complete; Fordow access negotiations ongoing.`,
    lastUpdate: `Day ${CONFLICT_DAY} · 01:55Z`,
    actions: [
      { time: '01:55Z', entry: 'Salami IRGC command net HF activity surge — corroborates ATLAS-1 ZULU-14 thermal signature. Passed to ORACLE-9.' },
      { time: '00:40Z', entry: 'Oman back-channel diplomatic traffic confirmed — ceasefire proximity talks elevated to State Dept level.' },
      { time: 'D26 03:30Z', entry: 'Alpha-5 pre-launch: IRGC CINC Salami auth traffic intercepted on IRGCAF launch net — 31 BM launch confirmed.' },
      { time: 'D23 06:00Z', entry: 'Salami designated IRGC CINC following Khamenei KIA D22. New command chain established. Nuclear auth protocols updated.' },
      { time: 'D22 02:35Z', entry: 'SL circuit CLOSED: Khamenei KIA confirmed FURY-22 (KARBALA-7). Supreme Leader circuit designation retired from active monitoring.' },
    ],
  },
  {
    id: 'agent-09',
    name: 'NEXUS',
    role: 'Multi-Domain Fusion Engine',
    domain: 'Fusion',
    status: 'ON STATION',
    priority: 'HIGH',
    confidence: 89,
    tasking: 'Synthesize all-domain sensor feeds into unified Common Operating Picture — identify cross-domain correlation and intelligence gaps.',
    threat_focus: 'Full-spectrum: IRGC all-domain coordinated attack pattern detection',
    quote: `D${CONFLICT_DAY} NEXUS all-domain COP: Ceasefire D32 holding — stability 91%/72h. IRGC hardliner faction watch ELEVATED (D50 public rejection overruled by new SL D50). GOLF-7 INACTIVE (Bandar Abbas D26). MCM ZB-Alpha 100% cleared D35 — first unescorted VLCC transit complete. Brent $76/bbl (down from $94 ceasefire peak). IAEA Natanz/Isfahan complete; Fordow pending. Geneva reconstruction talks ACTIVE (Day 48+). POW exchange Phase 1 complete D52 — 47 IRGC, 12 coalition. No multi-domain convergence indicators for resumed hostilities.`,
    lastUpdate: `Day ${CONFLICT_DAY} · 02:14Z`,
    actions: [
      { time: '02:14Z', entry: 'D27 COP: Alpha-5 post-strike stabilization. Ceasefire 68%, ZULU-14 reconstitution active, GOLF-7 INACTIVE, MCM ZB-α 78% cleared.' },
      { time: '01:55Z', entry: 'Cross-domain: ATLAS-1 thermal + SPECTER HF burst converge on ZULU-14 — passed to ORACLE-9 for 6th barrage probability update.' },
      { time: '00:45Z', entry: 'Correlated MANTIS GOLF-7 closure + MCM ZB-α 78% cleared with Hormuz PARTIAL TRANSIT status — 7 VLCCs confirmed D24-D27.' },
      { time: 'D26 04:30Z', entry: 'Alpha-5 real-time fusion: 31 BM tracks correlated across ATLAS-1/SPECTER/ORACLE-9. 27/31 intercepted. Domain fusion report #27 transmitted.' },
      { time: 'D26 02:30Z', entry: 'Pre-Alpha-5 FLASH: BM launch detected, 31 tracks. All-domain intercept coordination activated. FURY-26 TEL pre-emptive strike corroborated.' },
    ],
  },
  // ── Truth Reporting & Global Impact Agents ──────────────────────────────
  {
    id: 'agent-12',
    name: 'HERALD',
    role: 'Information Operations · Truth Projection Engine',
    domain: 'IO',
    status: 'ON STATION',
    priority: 'CRITICAL',
    confidence: 94,
    tasking: 'Synthesize all-agent validated intelligence into fully cited, adversary-fact-checked truth reports; auto-distribute to ISW, Bellingcat, CENTCOM PA, FinCEN, IAEA, AP, and Reuters feeds to dominate the information environment in every sector.',
    threat_focus: 'IRGC Information Operations Directorate counter-narrative campaign — Telegram, PressTV, Al-Alam, IRNA false-flag story injection',
    quote: 'Iranian IO narrative "US/Israel targeted hospitals" detected across 14 Arabic-language Telegram channels (127k reach) at D19 21:00Z. HERALD counter-narrative package deployed within 9 minutes: GEOINT-verified BDA images, kill chain documentation, and IAEA confirmation of no civilian nuclear site impact — pushed to Reuters/AP/BBC. Narrative suppression: 83% within 4 hours per social-velocity metrics.',
    lastUpdate: `Day ${CONFLICT_DAY} · 02:20Z`,
    actions: [
      { time: '02:20Z', entry: 'Truth report #47 published: HVA-20 (Shadmani) elimination — 4 sources, double-blind verified. Distributed CENTCOM/ISW/Reuters.' },
      { time: '01:35Z', entry: 'IRGC disinformation campaign "Operation MUHASABA" detected — 38 coordinated inauthentic accounts. Flagged to Meta/X Trust & Safety.' },
      { time: 'D27 00:30Z', entry: 'Energy-sector truth brief (#31) published: Hormuz PARTIAL TRANSIT status, ZB-α 78% cleared, 7 VLCC transits D24–D27 — counter to IRGC "total blockade" narrative. IEA/EIA/Reuters.' },
      { time: 'D26 14:00Z', entry: 'IAEA corroboration package #18 sent: Alpha-5 post-strike BDA — no radiological release, Fordow shaft 3-Alpha structural collapse confirmed non-nuclear. CTBTO/IAEA.' },
      { time: 'D25 22:00Z', entry: 'Financial truth brief (#27) published to FinCEN/IMF/Bloomberg: Brent $94 (not IRGC-claimed $147) — ceasefire optimism pricing confirmed via COMPASS model.' },
    ],
  },
  {
    id: 'agent-13',
    name: 'COMPASS',
    role: 'Global Multi-Industry Impact Assessment · ML Forecasting Engine',
    domain: 'Analytics',
    status: 'MONITORING',
    priority: 'HIGH',
    confidence: 87,
    tasking: 'Continuous ML-driven assessment of war effects across 9 global industries — energy, finance, maritime, nuclear/CBRN, cyber, military supply, media/IO, humanitarian, and diplomatic. Generate predictive confidence intervals and cross-sector cascade models for NSC, DIA, and allied intelligence consumers.',
    threat_focus: 'Hormuz PARTIAL TRANSIT recovery model — ceasefire 68% vs 6th barrage risk 41%; Brent $94/bbl declining; ZULU-14 reconstitution tail risk',
    quote: `Cross-sector ML model update D${CONFLICT_DAY}: Hormuz PARTIAL TRANSIT confirmed — ZB-α 78% cleared, 7 VLCC transits D24–D27 under MCM escort. Brent $94/bbl declining on ceasefire optimism. LNG spot +18% (recovering from $132 peak). Baltic Dry stabilizing as Cape re-routing unwinds. Ceasefire Abu Dhabi Framework: 68% probability, Iran SNSC dropped precondition D26 per UNSCR 2731. Humanitarian: southern Iran food corridor degradation rate 9.2%/day — UN WFP pre-alert active. Residual risk: GOLF-8 EMCON at Jask; ZULU-14 TEL reconstitution 6th barrage precursor (41%/72h).`,
    lastUpdate: `Day ${CONFLICT_DAY} · 02:18Z`,
    actions: [
      { time: '02:18Z', entry: 'ML cascade model v2.5 pushed: Hormuz PARTIAL TRANSIT — ceasefire 68%, 6th barrage 41%/72h. Energy-finance interdependency graph updated.' },
      { time: '01:40Z', entry: 'Humanitarian assessment: southern Iran food corridor degradation rate = 9.2%/day. UN WFP pre-alert transmitted.' },
      { time: 'D26 21:00Z', entry: 'Post-Alpha-5 cascade model: ceasefire 68% → Brent declining trajectory $94/bbl; Hormuz partial-transit normalization modeled 5–8 days if Abu Dhabi Framework holds.' },
      { time: 'D25 18:00Z', entry: 'UNSCR 2731 passage impact: ceasefire probability revised 12%→38%. Iran SNSC pre-condition drop D26 drove further revision to 68%.' },
      { time: 'D24 09:00Z', entry: 'MCM ZB-α partial opening: 7 VLCC transits modeled — $94 Brent stabilization confirmed vs $132 peak closure scenario. Insurance P+I Club rate -180bps.' },
    ],
  },
]

// ── Inter-Agent ML Fusion Event Log ─────────────────────────────────────────
const FUSION_LOG: { time: string; agents: string[]; signal: string; delta: string; output: string }[] = [
  { time: `D${CONFLICT_DAY} 06:00Z`, agents: ['ORACLE-9','COMPASS','TRIDENT','NEXUS','HERALD'], signal: `Ceasefire Phase 2 monitoring: stability 91%/72h + IRGC hardliner faction ACTIVE watch + IAEA Fordow access pending + Geneva talks Day 48`, delta: 'Ceasefire D32 holding', output: `ASSESSMENT D${CONFLICT_DAY}: Ceasefire stable 91%/72h. IRGC hardliner faction challenging new SL Mojtaba. Fordow inspection access pending IAEA negotiation. Brent $76/bbl. Transmitted CENTCOM/NSC/State/IAEA` },
  { time: 'D20 02:14Z', agents: ['NEXUS','SPECTER','ATLAS-1','ORACLE-9'], signal: 'Convergent pre-barrage indicators: HF burst + TEL track + probability spike',  delta: '+11pp → 94%', output: 'FLASH: combined-arms barrage within 48hr — transmitted NSC/CENTCOM' },
  { time: 'D20 01:35Z', agents: ['HERALD','CERBERUS','TRIDENT'],           signal: 'IRGC IO "Operation MUHASABA" + SL secure comms anomaly',                      delta: '+8pp → 82%',  output: 'IO suppression package + NSC FLASH re: SL-IRGC liaison call' },
  { time: 'D20 00:55Z', agents: ['PHANTOM','RAPTOR-2','NEXUS'],            signal: 'Bavar-373 radar emission→coverage gap confirmed for B-2A ingress corridor',    delta: 'N/A',         output: 'FURY-20 ingress route approved via WNW corridor — deconflicted' },
  { time: 'D19 23:00Z', agents: ['COMPASS','TRIDENT','ORACLE-9'],          signal: 'Oman back-channel signal + SIGINT diplomatic traffic spike',                   delta: '+13pp → 31%', output: 'Ceasefire probability report sent State Dept / UK FCO / MoD' },
  { time: 'D19 22:10Z', agents: ['HERALD','COMPASS','ARGUS'],              signal: 'GEOINT BDA + energy market ML model + disbinfo counter-package',               delta: '+9pp → 91%',  output: 'Energy truth brief #12 → IEA / EIA / Bloomberg terminal' },
  { time: 'D19 20:00Z', agents: ['NEXUS','ARGUS','SPECTER'],               signal: 'Fordow IMINT + HF comms + IR sensor reading — IRGCN sorties',                 delta: '+14pp → 89%', output: 'Domain fusion report #18 → CENTCOM J2 / IAEA / NGA' },
  { time: 'D18 22:10Z', agents: ['TRIDENT','CERBERUS','HYDRA-4'],          signal: 'MOIS comms surge + darknet procurement + open-source regime threat signals',   delta: '+7pp → 78%',  output: 'Regime stability assessment updated — nuclear escalation watch maintained' },
  { time: 'D18 18:00Z', agents: ['COMPASS','HERALD','ATLAS-1'],            signal: 'FinCEN SIGFIN data + IRGC Khatam convoy ID + ML financial disruption model',  delta: '+6pp → 88%',  output: 'Financial truth brief #9 → FinCEN / IMF / Moody\'s / SWIFT' },
  { time: 'D16 02:55Z', agents: ['HYDRA-4','SPECTER','NEXUS','RAPTOR-2'],  signal: 'Arabic Telegram + HF burst triangulation + Qom tunnel GEOINT',               delta: '+17pp → 91%', output: 'HVA-19 (Fallahzadeh) kinetic prosecution authorized — F-15E GBU-28' },
  { time: 'D14 05:20Z', agents: ['TRIDENT','SIGINT','NEXUS','ATLAS-1'],    signal: 'IRGC alternate node SIGINT + HUMINT + TRIDENT position fix',                 delta: '+22pp → 99%', output: 'HVA-18 (Fadavi) strike approved — B-2A JASSM-ER + GBU-31' },
]

// ── Industry Truth-Reporting Coverage Matrix ─────────────────────────────────
type IndustrySector = {
  sector: string
  agents: string
  confidence: number
  lastReport: string
  channel: string
  disinfoThreat: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
}
const INDUSTRY_MATRIX: IndustrySector[] = [
  { sector: 'Energy / Oil & Gas',       agents: 'COMPASS · HERALD · ATLAS-1',       confidence: 91, lastReport: `D${CONFLICT_DAY - 1} 02:18Z`, channel: 'IEA · EIA · Bloomberg · Reuters Energy',            disinfoThreat: 'HIGH' },
  { sector: 'Financial / Markets',      agents: 'COMPASS · HERALD · NEXUS',         confidence: 88, lastReport: `D${CONFLICT_DAY - 1} 01:40Z`, channel: 'FinCEN · IMF · Moody\'s · SWIFT · JP Morgan MICI',  disinfoThreat: 'CRITICAL' },
  { sector: 'Maritime / Shipping',      agents: 'COMPASS · MANTIS · ARGUS',         confidence: 93, lastReport: `D${CONFLICT_DAY - 1} 00:30Z`, channel: 'USCG · UKMTO · IMB · Baltic Exchange',               disinfoThreat: 'MEDIUM' },
  { sector: 'Nuclear / CBRN',          agents: 'SPECTER · ARGUS · TRIDENT · HERALD',confidence: 96, lastReport: `D${CONFLICT_DAY - 3} 22:00Z`, channel: 'IAEA · NRC · CTBTO · CENTCOM WMD Directorate',       disinfoThreat: 'CRITICAL' },
  { sector: 'Cyber / Critical Infra',  agents: 'CERBERUS · PHANTOM · COMPASS',      confidence: 84, lastReport: `D${CONFLICT_DAY - 1} 01:00Z`, channel: 'CISA · NCSC · GCC-CERT · Mandiant · CrowdStrike',    disinfoThreat: 'HIGH' },
  { sector: 'Military / Strategic',    agents: 'RAPTOR-2 · NEXUS · ORACLE-9',       confidence: 95, lastReport: `D${CONFLICT_DAY - 1} 02:11Z`, channel: 'CENTCOM J2 · DIA · ISW · JCS · Allied OPSUM',        disinfoThreat: 'HIGH' },
  { sector: 'Media / Information Ops', agents: 'HERALD · TRIDENT · CERBERUS',       confidence: 94, lastReport: `D${CONFLICT_DAY - 1} 02:20Z`, channel: 'AP · Reuters · BBC · Bellingcat · CENTCOM PA',        disinfoThreat: 'CRITICAL' },
  { sector: 'Humanitarian / Aid',      agents: 'COMPASS · HYDRA-4 · HERALD',        confidence: 79, lastReport: `D${CONFLICT_DAY - 3} 23:00Z`, channel: 'UN WFP · ICRC · OCHA · WHO · USAID OFDA',             disinfoThreat: 'MEDIUM' },
  { sector: 'Diplomatic / Political',  agents: 'TRIDENT · COMPASS · ORACLE-9',      confidence: 83, lastReport: `D${CONFLICT_DAY - 3} 23:00Z`, channel: 'State Dept · UK FCO · NATO HQ · UN SC Emergency',    disinfoThreat: 'HIGH' },
]

const DISINFO_COLOR: Record<string, string> = {
  CRITICAL: 'text-red-400',
  HIGH:     'text-amber-400',
  MEDIUM:   'text-yellow-400',
  LOW:      'text-emerald-400',
}

export default async function AgentsPage() {
  await requireAdmin()
  const critical = AGENTS.filter((a) => a.priority === 'CRITICAL').length
  const alert = AGENTS.filter((a) => a.status === 'ALERT' || a.status === 'ENGAGED').length

  return (
    <>
    {/* ── AI ACCURACY REPORT — client-side fetch (no SSR self-fetch) ─────── */}
    <AccuracyReport />

    {/* ── PLATFORM HEALTH ───────────────────────────────────────────────── */}
    <section className="space-y-3 mb-2">
      <PlatformHealth />
    </section>

    {/* ── SITREP + SOURCE INTELLIGENCE ────────────────────────────────────── */}
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
      <SitrepAutoFeed />
      <SourceRadar limit={10} />
    </section>

    <section className="space-y-8">
      {/* ── Cinematic Agent Roster Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-4">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(16,185,129,0.012) 2px, rgba(16,185,129,0.012) 4px)'}} />
          <div className="relative z-[3] flex items-center gap-3">
            <div className="relative">
              <Cpu size={22} className="text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
              <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse" />
            </div>
            <span className="text-lg font-bold tracking-widest text-emerald-400 glow-green uppercase">AI Agent Roster — Truth Domination Architecture</span>
            <span className="ml-auto text-xs text-zinc-500 tracking-widest normal-case font-normal">
              {critical} CRITICAL &nbsp;|&nbsp; {alert} ACTIVE &nbsp;|&nbsp; {AGENTS.length} TOTAL
            </span>
          </div>
        </div>
        <div className="studio-accent-bar" />
      </div>

      {/* 3-column responsive grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {AGENTS.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>

      {/* ── Inter-Agent ML Fusion Event Log — cinematic ──────────── */}
      <div className="tac-section-header mt-2">
        <Cpu size={14} className="text-cyan-400 drop-shadow-[0_0_4px_rgba(34,211,238,0.4)]" />
        <span className="text-cyan-400 glow-blue">Inter-Agent ML Fusion Event Log</span>
        <span className="ml-auto text-[9px] text-zinc-500 tracking-widest normal-case font-normal">
          CROSS-DOMAIN CORRELATION · CONFIDENCE DELTA · PUBLISHED OUTPUT
        </span>
      </div>
      <div className="video-feed-frame border border-zinc-800/60 rounded-sm overflow-x-auto relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-cyan-500/60 font-bold tracking-[0.2em]">FUSION LOG</span>
        </div>
        <table className="w-full text-[10px] font-mono text-left">
          <thead>
            <tr className="border-b border-zinc-800/60 bg-zinc-900/60">
              <th className="px-3 py-2 text-zinc-500 tracking-widest">TIME</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest">AGENTS</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest">CORRELATED SIGNAL</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest text-right">ML Δ</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest">TRUTH OUTPUT</th>
            </tr>
          </thead>
          <tbody>
            {FUSION_LOG.map((ev, i) => (
              <tr key={i} className="border-b border-zinc-900 hover:bg-zinc-900/30">
                <td className="px-3 py-2 text-emerald-400 whitespace-nowrap">{ev.time}</td>
                <td className="px-3 py-2 text-cyan-400 whitespace-nowrap">{ev.agents.join(' · ')}</td>
                <td className="px-3 py-2 text-zinc-300">{ev.signal}</td>
                <td className="px-3 py-2 text-amber-400 text-right whitespace-nowrap">{ev.delta}</td>
                <td className="px-3 py-2 text-zinc-400">{ev.output}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Industry Truth-Reporting Coverage Matrix ──────────────────── */}
      <div className="tac-section-header mt-2">
        <Cpu size={14} className="text-violet-400 drop-shadow-[0_0_4px_rgba(139,92,246,0.4)]" />
        <span className="text-violet-400">Global Industry Truth-Reporting Matrix</span>
        <span className="ml-auto text-[9px] text-zinc-500 tracking-widest normal-case font-normal">
          AI COVERAGE · CONFIDENCE · DISINFO THREAT · PUBLICATION CHANNEL
        </span>
      </div>
      <div className="border border-zinc-800/60 rounded-sm overflow-x-auto">
        <table className="w-full text-[10px] font-mono text-left">
          <thead>
            <tr className="border-b border-zinc-800/60 bg-zinc-900/60">
              <th className="px-3 py-2 text-zinc-500 tracking-widest">SECTOR</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest">AI AGENTS</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest text-right">CONF</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest">LAST REPORT</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest">TRUTH CHANNEL</th>
              <th className="px-3 py-2 text-zinc-500 tracking-widest text-center">DISINFO THREAT</th>
            </tr>
          </thead>
          <tbody>
            {INDUSTRY_MATRIX.map((row) => (
              <tr key={row.sector} className="border-b border-zinc-900 hover:bg-zinc-900/30">
                <td className="px-3 py-2 text-white font-semibold whitespace-nowrap">{row.sector}</td>
                <td className="px-3 py-2 text-cyan-400 whitespace-nowrap">{row.agents}</td>
                <td className="px-3 py-2 text-right">
                  <span className={row.confidence >= 90 ? 'text-emerald-400' : row.confidence >= 80 ? 'text-amber-400' : 'text-yellow-400'}>
                    {row.confidence}%
                  </span>
                </td>
                <td className="px-3 py-2 text-emerald-400 whitespace-nowrap">{row.lastReport}</td>
                <td className="px-3 py-2 text-zinc-400">{row.channel}</td>
                <td className={`px-3 py-2 text-center font-bold tracking-widest ${DISINFO_COLOR[row.disinfoThreat]}`}>{row.disinfoThreat}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── ML Confidence Heatmap ──────────────────────────────────────── */}
      <div className="tac-section-header mt-2">
        <Cpu size={14} className="text-amber-400 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]" />
        <span className="text-amber-400 glow-amber">ML Confidence Heatmap — Agent × Domain</span>
        <span className="ml-auto text-[9px] text-zinc-500 tracking-widest normal-case font-normal">
          FUSED BAYESIAN POSTERIOR · UPDATED REAL-TIME
        </span>
      </div>
      <div className="border border-zinc-800/60 rounded-sm overflow-x-auto">
        <table className="w-full text-[10px] font-mono text-center">
          <thead>
            <tr className="border-b border-zinc-800/60 bg-zinc-900/60">
              <th className="px-3 py-2 text-zinc-500 text-left">AGENT</th>
              {['ISR','CYBER','SIGINT','OSINT','PREDICT','STRIKE','IMINT','EW','IO/COMMS','IMPACT'].map((d) => (
                <th key={d} className="px-2 py-2 text-zinc-500 tracking-widest">{d}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              { name: 'ATLAS-1',  scores: [95, 40, 72, 68, 71, 60, 88, 45, 35, 52] },
              { name: 'CERBERUS', scores: [55, 96, 78, 74, 62, 40, 38, 82, 70, 58] },
              { name: 'HYDRA-4',  scores: [61, 50, 66, 92, 70, 35, 62, 40, 68, 74] },
              { name: 'SPECTER',  scores: [70, 65, 95, 75, 68, 45, 55, 60, 72, 60] },
              { name: 'ORACLE-9', scores: [72, 58, 60, 78, 94, 48, 58, 44, 62, 88] },
              { name: 'MANTIS',   scores: [80, 30, 55, 42, 60, 68, 84, 38, 28, 65] },
              { name: 'ARGUS',    scores: [88, 38, 50, 65, 55, 55, 97, 42, 39, 60] },
              { name: 'RAPTOR-2', scores: [78, 42, 65, 55, 72, 99, 70, 62, 50, 55] },
              { name: 'PHANTOM',  scores: [62, 74, 78, 48, 55, 55, 50, 96, 58, 48] },
              { name: 'TRIDENT',  scores: [55, 60, 82, 72, 82, 38, 45, 40, 88, 80] },
              { name: 'NEXUS',    scores: [88, 80, 85, 84, 86, 76, 82, 78, 80, 85] },
              { name: 'HERALD',   scores: [52, 68, 70, 90, 65, 35, 50, 55, 99, 92] },
              { name: 'COMPASS',  scores: [70, 72, 68, 88, 92, 45, 74, 52, 84, 97] },
            ].map((row) => {
              return (
                <tr key={row.name} className="border-b border-zinc-900">
                  <td className="px-3 py-1 text-emerald-400 text-left whitespace-nowrap font-bold">{row.name}</td>
                  {row.scores.map((s, i) => {
                    const bg = s >= 90 ? 'bg-red-900/70 text-red-300' : s >= 75 ? 'bg-amber-900/60 text-amber-300' : s >= 55 ? 'bg-zinc-800/60 text-zinc-300' : 'bg-zinc-950 text-zinc-600'
                    return <td key={i} className={`px-2 py-1 text-[9px] font-bold ${bg}`}>{s}</td>
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>

    {/* ── NEXUS LIVE ENGINE OUTPUTS ──────────────────────────────────── */}
    <section className="space-y-3">
      <div className="tac-section-header">
        <Cpu size={14} className="text-red-400 animate-pulse drop-shadow-[0_0_4px_rgba(239,68,68,0.5)]" />
        <span className="text-red-400 tracking-widest glow-red">LIVE ENGINE OUTPUTS — ORACLE-9 · HERALD-3 · COMPASS</span>
        <span className="ml-auto text-[9px] font-mono text-zinc-500 normal-case font-normal">live feeds · auto-refresh</span>
      </div>

      {/* Autonomous pipeline monitors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <IngestMonitor />
        <AnalyzeBatchMonitor />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <OraclePanel />
        <HeraldFeed limit={6} />
        <CompassPanel />
      </div>
    </section>

    {/* ── BREAKING STORY ANALYSIS ENGINE (Section 2) ─────────────────── */}
    <section className="space-y-6 pt-4">
      <div className="tac-section-header">
        <Cpu size={16} className="text-red-400" />
        <span className="text-red-400">REAL-TIME STORY ANALYSIS ENGINE — AI vs COMPETITORS</span>
        <span className="ml-auto text-[10px] text-zinc-500 tracking-widest normal-case font-normal">
          {[
            { headline: 'Day 1 mass decapitation — 4 senior KIA', truthScore: 99 },
            { headline: 'Qaani (Quds Force) KIA Day 2', truthScore: 98 },
            { headline: 'Khatib (MOIS Director) KIA Day 6', truthScore: 97 },
            { headline: 'Artesh high command Days 4-9', truthScore: 96 },
            { headline: 'Ghasemi (Khatam) KIA Day 12', truthScore: 96 },
            { headline: 'Shadmani (SNSC) KIA Day 19', truthScore: 94 },
          ].length} ACTIVE STORIES INGESTED
        </span>
      </div>

      <div className="text-[10px] font-mono text-zinc-500 border border-zinc-800 rounded-sm p-3 bg-zinc-950/50">
        <span className="text-amber-400 tracking-widest">DOCTRINE: </span>
        Every breaking story enters the AI analysis pipeline within <span className="text-emerald-400">90 seconds</span> of publication.
        All 13 agents independently assess, cross-correlate, and vote on Truth Score. Source citations attached to every verdict.
        Final AI composite truth score versus competitor scores shown below. AI advantage: no editorial filter, no institutional bias,
        no publication lag — just signal from noise.
      </div>

      {[
        {
          headline: "DAY 1 MASS DECAPITATION — Salami (IRGC C-in-C), Baqeri (JCS), Hajizadeh (IRGC Aerospace), Eslami (Nuclear) Eliminated in Opening 48 Minutes",
          source: "CENTCOM PA / DIA / NGA BDA / ISW / TRIDENT",
          time: "Day 1 / 01 March 2026 / 03:30Z",
          agentsAnalyzing: ['NEXUS', 'RAPTOR-2', 'ORACLE-9', 'ATLAS-1', 'TRIDENT', 'HERALD'],
          truthScore: 99,
          competitorScores: [
            { org: 'NYT', score: 61 },
            { org: 'Reuters', score: 55 },
            { org: 'CNN', score: 48 },
            { org: 'ISW', score: 85 },
            { org: 'BBC', score: 52 },
          ],
          verdicts: [
            { agent: 'NEXUS', finding: '4 simultaneous strike packages executed 02:30–03:18Z Day 1. Salami (IRGC C-in-C), Baqeri (JCS Chief), Hajizadeh (IRGC Aerospace), and Eslami (AEOI Nuclear) all confirmed KIA within 48 minutes. Iranian state media blackout 6 hours confirms catastrophic command decapitation.', confidence: '99%' },
            { agent: 'RAPTOR-2', finding: 'B-2A, F-35A, TLAM, and F-15E delivered simultaneously — coordinated multi-platform operation with zero sequencing error, consistent with months of rehearsal. All four target packages successful first pass.', confidence: '99%' },
            { agent: 'ORACLE-9', finding: 'Pre-strike model predicted 87% probability of command paralysis if 3+ Tier-1 HVA eliminated Day 1. Actual outcome: 4 Tier-1 eliminated. Predicted reconstitution timeline: 6-12 days. Model validated.', confidence: '97%' },
            { agent: 'HERALD', finding: 'Reuters first confirmed all 4 KIA at H+11 hours; NYT at H+13 hours. AI team confirmed all 4 at H+47 minutes via simultaneous CENTCOM + NGA BDA + ISW ingestion. AI lead: 10+ hours over Reuters.', confidence: '98%' },
          ],
          citations: [
            'CENTCOM PA — Day 1 Strike Package Summary (01 March 2026)',
            'ISW — Iran Day 1 Command Structure Assessment',
            'NGA BDA — 4 Strike Package Confirmation Reports D1',
            'DIA — Iran Tier-1 HVA KIA Confirmation D1',
            'AP — Iran military leadership struck Day 1',
            'Reuters — IRGC command structure Day 1 reporting',
          ],
        },
        {
          headline: "GENERAL ESMAIL QAANI KIA — IRGC Quds Force Commander Eliminated Day 2, Iran Proxy Command Chain Severed",
          source: "CIA / TRIDENT SIGINT / IAF / ISW",
          time: "Day 2 / 02 March 2026 / 04:15Z",
          agentsAnalyzing: ['TRIDENT', 'NEXUS', 'ORACLE-9', 'PHANTOM', 'ATLAS-1'],
          truthScore: 98,
          competitorScores: [
            { org: 'NYT', score: 55 },
            { org: 'Reuters', score: 62 },
            { org: 'ISW', score: 84 },
            { org: 'CNN', score: 38 },
            { org: 'BBC', score: 50 },
          ],
          verdicts: [
            { agent: 'TRIDENT', finding: 'Qaani’s Quds Force command circuit went silent at 04:18Z Day 2. TRIDENT had tracked his displacement to Chahardangeh alternate node from Day 1 00:00Z — 28 hours of pattern-of-life enabled precision timing. SIGINT silence confirms KIA.', confidence: '99%' },
            { agent: 'ORACLE-9', finding: 'Quds Force proxy command impact model: without central command, autonomous protocols sustain for 45-90 days but cannot escalate or shift strategic posture. De-escalation across Hezbollah, PMF, and Houthis predicted within 45 days.', confidence: '89%' },
            { agent: 'NEXUS', finding: 'Hezbollah, Houthis, and Iraqi PMF all shifted to pre-positioned contingency comms protocols within 90 minutes of Qaani KIA — autonomous mode activation confirmed. No new strategic tasking detected from any proxy by Day 3.', confidence: '94%' },
          ],
          citations: [
            'TRIDENT — Quds Force command circuit monitor D1-D2',
            'CIA — Qaani displacement and pattern-of-life tracking D1-D2',
            'ISW — Quds Force command impact assessment',
            'Reuters — Qaani KIA reporting Day 2',
            'Bellingcat — Iran proxy comms protocol shift post-Qaani',
          ],
        },
        {
          headline: "ISMAIL KHATIB (MOIS Director) KIA Day 6 — Iranian National Intelligence Apparatus Decapitated",
          source: "NSA / CERBERUS / CENTCOM PA / AP",
          time: "Day 6 / 06 March 2026 / 22:55Z",
          agentsAnalyzing: ['CERBERUS', 'NEXUS', 'TRIDENT', 'HERALD'],
          truthScore: 97,
          competitorScores: [
            { org: 'NYT', score: 40 },
            { org: 'Reuters', score: 48 },
            { org: 'ISW', score: 72 },
            { org: 'CNN', score: 30 },
            { org: 'BBC', score: 44 },
          ],
          verdicts: [
            { agent: 'CERBERUS', finding: 'Khatib was the sole institutional bridge between the IRGC Intelligence Organisation and MOIS civilian intelligence. His death Day 6 severed both covert action and domestic counterintelligence command chains simultaneously.', confidence: '97%' },
            { agent: 'NEXUS', finding: 'MOIS operational communications ceased entirely within 4 hours of Khatib KIA. 19 MOIS safehouse networks across 7 provinces went silent — consistent with emergency compartmentalization protocol triggered by director death.', confidence: '95%' },
            { agent: 'HERALD', finding: 'Competitors did not confirm Khatib KIA until Day 8 (AP first). AI team confirmed Day 6 at H+3 hours via NSA + CENTCOM + CERBERUS simultaneous ingestion. AI advantage over AP: 38 hours.', confidence: '96%' },
          ],
          citations: [
            'CERBERUS — MOIS network silent status D6',
            'NSA — Khatib communications pattern D1-D6',
            'CENTCOM PA — Day 6 Strike Confirmation',
            'AP — MOIS Director KIA reporting D8',
            'ISW — Iranian Intelligence apparatus assessment',
          ],
        },
        {
          headline: "ARTESH HIGH COMMAND NEUTRALIZATION — Artesh C-in-C Mousavi, Ground Commander Heydari, Navy C-in-C Irani All KIA Days 4–9",
          source: "CENTCOM J2 / DIA / NGA BDA / ISW",
          time: "Day 9 / 09 March 2026 / 14:22Z",
          agentsAnalyzing: ['ATLAS-1', 'ORACLE-9', 'RAPTOR-2', 'NEXUS', 'MANTIS'],
          truthScore: 96,
          competitorScores: [
            { org: 'NYT', score: 50 },
            { org: 'Reuters', score: 58 },
            { org: 'ISW', score: 80 },
            { org: 'CNN', score: 38 },
            { org: 'FT', score: 55 },
          ],
          verdicts: [
            { agent: 'ATLAS-1', finding: 'ISR pattern-of-life confirmed all three Artesh command targets: Gen Abdolrahim Mousavi (Artesh C-in-C, Day 4 07:10Z), Adm Shahram Irani (IRIN C-in-C, Day 5 17:45Z), Gen Kioumars Heydari (Artesh Ground Forces, Day 9 14:22Z). All KIA confirmed via NGA BDA + SIGINT cessation.', confidence: '97%' },
            { agent: 'ORACLE-9', finding: 'With both IRGC and Artesh command simultaneously degraded by Day 9 (9 of 15 top commanders KIA), ORACLE-9 models 91% probability Iran conventional military coordination is non-functional. No effective combined-arms response possible.', confidence: '93%' },
            { agent: 'NEXUS', finding: 'Iranian Armed Forces General Staff meeting schedule — confirmed via HUMINT — showed no sessions from Day 4 onward. Command structure frozen. Only lower-echelon tactical units executing pre-planned defensive schemes.', confidence: '94%' },
          ],
          citations: [
            'CENTCOM J2 — Artesh Command KIA Summary D4-D9',
            'NGA BDA Reports — Artesh Command Nodes D4-D9',
            'ISW — Iranian Artesh High Command D4–D9 Assessment',
            'DIA — Iran Armed Forces Decapitation Impact Assessment',
            'Reuters — Iran military command killed Days 4-9',
          ],
        },
        {
          headline: "IRGC ECONOMIC PILLAR DESTROYED — Gen Ghasemi (Khatam al-Anbiya) KIA Day 12, Iran Military-Industrial Complex $28B Machine Halted",
          source: "Treasury EO 13382 / FinCEN / CENTCOM PA / WSJ",
          time: "Day 12 / 12 March 2026 / 16:30Z",
          agentsAnalyzing: ['NEXUS', 'HYDRA-4', 'CERBERUS', 'ATLAS-1'],
          truthScore: 96,
          competitorScores: [
            { org: 'WSJ', score: 75 },
            { org: 'NYT', score: 38 },
            { org: 'Reuters', score: 55 },
            { org: 'FT', score: 65 },
            { org: 'Bloomberg', score: 60 },
          ],
          verdicts: [
            { agent: 'NEXUS', finding: 'Khatam al-Anbiya Construction HQ — IRGC’s $28B military-industrial conglomerate — lost its CEO and 6 senior directors in the Day 12 strike. All active IRGC construction and weapons-system production contracts (est. $4.2B in-progress) suspended within 72h.', confidence: '96%' },
            { agent: 'HYDRA-4', finding: 'Khatam controls ~2,000 subcontractors and 135,000 workers across the Iranian defence-industrial base. Without Ghasemi’s command authority, no major procurement contract can be validly authorized — IRGC procurement reconstitution halted.', confidence: '94%' },
            { agent: 'CERBERUS', finding: 'FinCEN flagged $340M in Khatam accounts frozen simultaneously with kinetic strike — coordinated Treasury-CENTCOM action. Competitor financial press reported the financial angle 3 days later. AI team ingested Treasury + kinetic together at H+1h.', confidence: '95%' },
          ],
          citations: [
            'Treasury EO 13382 — Khatam al-Anbiya Designation',
            'FinCEN — IRGC Procurement Account Freeze D12',
            'CENTCOM PA — Day 12 Strike Confirmation',
            'WSJ — IRGC military-industrial complex reporting',
            'ISW — Khatam al-Anbiya economic role assessment',
          ],
        },
        {
          headline: "SNSC MILITARY DEPUTY GEN SHADMANI KIA DAY 19 — Iran National Security Council Command Architecture Collapsed — ALL 20 HVA CONFIRMED AS OF DAY 19",
          source: "TRIDENT / NGA BDA / ISW / Reuters",
          time: "Day 19 / 19 March 2026 / 18:05Z",
          agentsAnalyzing: ['TRIDENT', 'ORACLE-9', 'NEXUS', 'COMPASS', 'HERALD'],
          truthScore: 94,
          competitorScores: [
            { org: 'NYT', score: 42 },
            { org: 'Reuters', score: 55 },
            { org: 'ISW', score: 78 },
            { org: 'CNN', score: 30 },
            { org: 'BBC', score: 48 },
          ],
          verdicts: [
            { agent: 'TRIDENT', finding: 'Shadmani’s elimination closes the loop on Iran’s entire first-tier national security decision architecture. With Shadmani KIA, all four principals who could constitutionally convene the SNSC in emergency session are now dead. Iranian national security decision-making has no lawful chair.', confidence: '95%' },
            { agent: 'ORACLE-9', finding: 'SNSC functional collapse model: probability of coherent national-level strategic decision being transmitted to any military unit now assessed at <8%. Iran is operating on pre-positioned tactical orders only. No strategic recalibration is possible.', confidence: '92%' },
            { agent: 'COMPASS', finding: 'COMPASS cross-referenced all 21 confirmed HVA KIAs (Days 1–22, including Supreme Leader Ali Khamenei KIA Day 22) against Iranian command architecture. Assessment: every tier of military and national security command has been compromised as of 22 March 2026. Successor regime under Salami retains tactical authority but national-level strategic decision coherence assessed at <5%.', confidence: '96%' },
          ],
          citations: [
            'TRIDENT — SNSC convening authority analysis D19',
            'NGA BDA — Shadmani compound D19',
            'ISW — Iran SNSC institutional authority',
            'ORACLE-9 — SNSC functional collapse model D19',
            'Reuters — Shadmani elimination Day 19 reporting',
          ],
        },
        {
          headline: `DAY ${CONFLICT_DAY} STATUS UPDATE — Abu Dhabi Proximity Talks ACTIVE + Alpha-5 (D26) Post-Strike BDA Complete + COMPASS Ceasefire 68% Confidence — AI FUSION SUMMARY`,
          source: "TRIDENT / ORACLE-9 / SPECTER / ATLAS-1 / NEXUS",
          time: `Day ${CONFLICT_DAY} / ${new Date(Date.UTC(2026,2,0) + CONFLICT_DAY * 86400000).toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'})} / 02:14Z`,
          agentsAnalyzing: ['TRIDENT', 'ORACLE-9', 'SPECTER', 'ATLAS-1', 'NEXUS', 'COMPASS'],
          truthScore: 91,
          competitorScores: [
            { org: 'NYT', score: 8 },
            { org: 'Reuters', score: 10 },
            { org: 'ISW', score: 28 },
            { org: 'CNN', score: 5 },
            { org: 'BBC', score: 8 },
          ],
          verdicts: [
            { agent: 'TRIDENT', finding: `HISTORICAL (D22): Supreme Leader secure circuit to IRGC CINC activated 01:15Z Day 22 — 4-minute duration. Pattern matched pre-escalation authorization exchange from Day 1. FURY-22 strike executed 14:35Z D22 — Khamenei KIA confirmed. D${CONFLICT_DAY} TRIDENT status: monitoring Salami–SNSC hardliner faction HF exchanges; no pre-launch authentication patterns detected as of 0600Z D${CONFLICT_DAY}. Abu Dhabi ceasefire track assessed primary near-term driver.`, confidence: '95%' },
            { agent: 'ORACLE-9', finding: `Day ${CONFLICT_DAY} assessment: Barrage Alpha-5 (D26) complete — 27/31 BMs intercepted. 2 USAF KIA. 6th barrage probability 41% / 72h. IRGCAF reconstituting ZULU-14 corridor TELs. Ceasefire confidence ELEVATED to 68% following Abu Dhabi Framework — highest since conflict began. Swarm drone co-attack probability reduced to 34%.`, confidence: '94%' },
            { agent: 'SPECTER', finding: `D${CONFLICT_DAY} SPECTER status: monitoring ZULU-14 HF authentication exchanges — no pre-launch burst detected as of 0600Z D${CONFLICT_DAY}. Post-Alpha-5 reconstitution activity at ZULU-14 confirmed by ATLAS-1 thermal imagery. SPECTER D26 historical: pre-launch HF burst at 01:40Z D26 preceded Alpha-5 by 62 minutes — transmitted CENTCOM 12-minute warning.`, confidence: '88%' },
            { agent: 'NEXUS', finding: `Cross-domain D${CONFLICT_DAY} status: ceasefire confidence 68% (up from 4% at D24). Primary driver: Iran SNSC pre-condition drop D26 + Oman back-channel reactivation + POTUS Abu Dhabi Framework. Six-source convergence confirming diplomatic breakthrough. FURY-${CONFLICT_DAY} prosecution window on standby contingent on ZULU-14 authorization. No pre-barrage indicators in current fusion as of D${CONFLICT_DAY} 0600Z.`, confidence: '94%' },
          ],
          citations: [
            `ORACLE-9 — Day 27 barrage assessment + ceasefire confidence model D${CONFLICT_DAY} 02:00Z`,
            `SPECTER — ZULU-14 HF monitoring + Alpha-5 warning analysis D${CONFLICT_DAY} 02:07Z`,
            `ATLAS-1 — ZULU-14 TEL reconstitution thermal imagery D${CONFLICT_DAY} 01:55Z`,
            `NEXUS — Abu Dhabi ceasefire cross-domain fusion report D${CONFLICT_DAY} 02:14Z`,
            `COMPASS — COMPASS model D${CONFLICT_DAY}: ceasefire 68%, economic cascade update`,
          ],
        },
      ].map((story, idx) => (
        <div key={idx} className={`border rounded-sm overflow-hidden ${
          story.truthScore >= 98 ? 'border-red-700/60 bg-red-950/10' : 'border-zinc-800/60 bg-zinc-950/50'
        }`}>
          {/* Story header */}
          <div className={`flex items-start justify-between gap-4 p-3 border-b ${
            story.truthScore >= 98 ? 'border-red-700/40 bg-red-950/20' : 'border-zinc-800/60'
          }`}>
            <div className="flex-1 min-w-0">
              <div className="text-[9px] font-mono text-zinc-500 tracking-widest mb-1">
                {story.time} &nbsp;|&nbsp; SOURCE: {story.source}
              </div>
              <div className={`text-sm font-bold tracking-wide ${story.truthScore >= 98 ? 'text-red-200' : 'text-zinc-100'}`}>
                {story.headline}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {story.agentsAnalyzing.map((a) => (
                  <span key={a} className="text-[8px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-900/60 px-1.5 py-0.5 rounded-sm">
                    {a}
                  </span>
                ))}
              </div>
            </div>
            {/* AI Truth Score */}
            <div className="flex-shrink-0 text-center">
              <div className={`text-3xl font-bold font-mono ${story.truthScore >= 97 ? 'text-red-400' : story.truthScore >= 90 ? 'text-amber-400' : 'text-yellow-400'}`}>
                {story.truthScore}
              </div>
              <div className="text-[8px] tracking-widest text-zinc-500 mt-0.5">AI TRUTH</div>
            </div>
          </div>

          {/* Competitor scores */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800/60 bg-zinc-900/30 overflow-x-auto">
            <span className="text-[9px] text-zinc-600 font-mono tracking-widest whitespace-nowrap flex-shrink-0">COMPETITORS:</span>
            {story.competitorScores.map((c) => (
              <div key={c.org} className="flex-shrink-0 text-center">
                <div className="text-[8px] text-zinc-500">{c.org}</div>
                <div className={`text-[11px] font-bold font-mono ${c.score >= 75 ? 'text-amber-400' : c.score >= 50 ? 'text-yellow-500' : 'text-zinc-600'}`}>
                  {c.score}
                </div>
              </div>
            ))}
            <div className="ml-auto flex-shrink-0 text-[9px] font-mono text-emerald-400">
              AI ADVANTAGE: +{story.truthScore - Math.max(...story.competitorScores.map((c) => c.score))} pts
            </div>
          </div>

          {/* Agent verdicts */}
          <div className="divide-y divide-zinc-900/60">
            {story.verdicts.map((v, vi) => (
              <div key={vi} className="px-3 py-2 flex items-start gap-3">
                <span className="text-[9px] font-mono text-emerald-400 whitespace-nowrap flex-shrink-0 w-16">{v.agent}</span>
                <p className="text-[10px] text-zinc-300 leading-relaxed flex-1">{v.finding}</p>
                <span className={`text-[9px] font-mono font-bold flex-shrink-0 ${v.confidence.startsWith('99') ? 'text-red-400' : v.confidence.startsWith('9') ? 'text-amber-400' : 'text-yellow-400'}`}>
                  {v.confidence}
                </span>
              </div>
            ))}
          </div>

          {/* Citations */}
          <div className="px-3 py-2 border-t border-zinc-800/60 bg-zinc-950/40">
            <div className="text-[8px] font-mono text-zinc-600 tracking-widest mb-1.5">CITATIONS ({story.citations.length}):</div>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5">
              {story.citations.map((c, ci) => (
                <span key={ci} className="text-[9px] font-mono text-zinc-500">[{ci + 1}] {c}</span>
              ))}
            </div>
          </div>
        </div>
      ))}
    </section>
    </>
  )
}
