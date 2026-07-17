'use client'

import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Square, SkipForward, Radio, Mic2, Mic, Tv, Shield, Crosshair, AlertTriangle, Video, Eye } from 'lucide-react'
import Image from 'next/image'
import { getConflictDay, CONFLICT_EPOCH } from '@/lib/conflict-day'
import { buildDayAwareBroadcast } from '@/lib/dynamic-fallback'
import { getWarStats } from '@/lib/war-stats'
import { HeraldFeed } from '@/components/HeraldFeed'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { createBrowserClient, SUPABASE_CONFIGURED } from '@/lib/supabase'

const CONFLICT_DAY = getConflictDay()
const WAR_STATS = getWarStats(CONFLICT_DAY)
const CONFLICT_DATE_STR = new Date(CONFLICT_EPOCH + (CONFLICT_DAY - 1) * 86_400_000)
  .toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })

// Minimal static fallback — only used while live intel loads
const BASE_TICKER_ITEMS = [
  `EPIC FURY INTELLIGENCE NETWORK — CONFLICT DAY ${CONFLICT_DAY} — LOADING LIVE INTEL FEED…`,
  'HERALD-3 AI INGEST ENGINE ACTIVE — RSS AGGREGATION RUNNING — REAL-TIME NEWS ANALYSIS IN PROGRESS',
  'ALL TICKER ITEMS SOURCED FROM LIVE NEWS INGESTION — ZERO SCRIPTED CONTENT',
]

// ── Types ────────────────────────────────────────────────────────────────────
type AnchorId = 'sarah' | 'james' | 'maya' | 'harris' | 'natasha' | 'marcus' | 'walsh' | 'rostami' | 'vargas'
type PlayMode  = 'idle' | 'loading' | 'playing' | 'paused'

interface Anchor {
  id:              AnchorId
  name:            string
  title:           string
  gender:          'M' | 'F'
  /** ElevenLabs voice ID */
  voiceId:         string
  /** BCP-47 locale for Web Speech API voice selection (e.g. 'en-US', 'en-GB', 'en-AU', 'en-IN') */
  webLocale:       string
  /** Preferred Web Speech API voice name for this locale (fallback when ElevenLabs unavailable) */
  webVoiceName:    string
  color:           string
  bg:              string
  border:          string
  initials:        string
  avatar:          string
}

interface Segment {
  id:        number
  anchor:    AnchorId
  label:     string
  topic:     string
  script:    string
  citations: string[]
}

// Shape returned by /api/newsroom/generate (anchor is plain string before cast)
interface GeneratedSegment {
  id:        number
  anchor:    string
  label:     string
  topic:     string
  script:    string
  citations: string[]
}

// ── News Team ─────────────────────────────────────────────────────────────────
// ElevenLabs voices — best broadcast-quality picks from account catalog
// Model: eleven_v3 (most realistic, human-sounding TTS available)
// Web Speech locales represent the anchor's accent/background for fallback TTS
const TEAM: Anchor[] = [
  {
    id: 'sarah', name: 'Sarah Mitchell', title: 'Lead Anchor', gender: 'F',
    voiceId: '21m00Tcm4TlvDq8ikWAM',   // Rachel — warm, authoritative news anchor
    webLocale: 'en-US', webVoiceName: 'Aria',   // US American English — Microsoft Aria Neural
    color: 'text-rose-400', bg: 'bg-rose-950/30', border: 'border-rose-800/60', initials: 'SM', avatar: '/anchors/sarah.png',
  },
  {
    id: 'james', name: 'James Calloway', title: 'Co-Anchor', gender: 'M',
    voiceId: 'onwK4e9ZLuTAKqWW03F9',   // Daniel — deep, precise British-American anchor voice
    webLocale: 'en-GB', webVoiceName: 'Ryan',   // British English — Microsoft Ryan Neural
    color: 'text-sky-400', bg: 'bg-sky-950/30', border: 'border-sky-800/60', initials: 'JC', avatar: '/anchors/james.png',
  },
  {
    id: 'maya', name: 'Dr. Maya Chen', title: 'Defense Correspondent', gender: 'F',
    voiceId: 'XrExE9yKIg1WjnnlVkGX',   // Matilda — crisp, intelligent analytical female
    webLocale: 'en-IN', webVoiceName: 'Neerja', // Indian English — Microsoft Neerja Neural
    color: 'text-violet-400', bg: 'bg-violet-950/30', border: 'border-violet-800/60', initials: 'MC', avatar: '/anchors/maya.png',
  },
  {
    id: 'harris', name: 'Col. Robert Harris', title: 'Military Analyst (Ret.)', gender: 'M',
    voiceId: 'VR6AewLTigWG4xSOukaG',   // Arnold — deep, gravelly commanding military baritone
    webLocale: 'en-US', webVoiceName: 'Eric',   // US American English — Microsoft Eric Neural
    color: 'text-amber-400', bg: 'bg-amber-950/30', border: 'border-amber-800/60', initials: 'RH', avatar: '/anchors/harris.png',
  },
  {
    id: 'natasha', name: 'Natasha Webb', title: 'Foreign Affairs Reporter', gender: 'F',
    voiceId: 'XB0fDUnXU5powFXDhCwa',   // Charlotte — sophisticated, confident international correspondent
    webLocale: 'en-AU', webVoiceName: 'Natasha', // Australian English — Microsoft Natasha Neural
    color: 'text-emerald-400', bg: 'bg-emerald-950/30', border: 'border-emerald-800/60', initials: 'NW', avatar: '/anchors/natasha.png',
  },
  {
    id: 'marcus', name: 'Marcus Thompson', title: 'Economics Correspondent', gender: 'M',
    voiceId: 'pNInz6obpgDQGcFmaJgB',   // Adam — measured, authoritative financial correspondent
    webLocale: 'en-US', webVoiceName: 'Guy',    // US American English — Microsoft Guy Neural
    color: 'text-cyan-400', bg: 'bg-cyan-950/30', border: 'border-cyan-800/60', initials: 'MT', avatar: '/anchors/marcus.png',
  },
  {
    id: 'walsh', name: 'Lt. Gen. Patricia Walsh', title: 'Pentagon Correspondent', gender: 'F',
    voiceId: 'pMsXgVXv3BLzUgSXRplE',   // Serena — authoritative, clipped military-official cadence
    webLocale: 'en-US', webVoiceName: 'Jenny',  // US American English — Microsoft Jenny Neural
    color: 'text-orange-400', bg: 'bg-orange-950/30', border: 'border-orange-800/60', initials: 'PW', avatar: '/anchors/walsh.png',
  },
  {
    id: 'rostami', name: 'Dr. Amir Rostami', title: 'Nuclear & Iran Analyst', gender: 'M',
    voiceId: 'Zlb1dXrM653N07WRdFW3',   // Joseph — calm, precise academic analytical voice
    webLocale: 'en-GB', webVoiceName: 'Daniel', // British English — Microsoft Daniel Neural (Oxford-educated)
    color: 'text-teal-400', bg: 'bg-teal-950/30', border: 'border-teal-800/60', initials: 'AR', avatar: '/anchors/rostami.png',
  },
  {
    id: 'vargas', name: 'Cpl. Elena Vargas', title: 'Forward Correspondent', gender: 'F',
    voiceId: 'Xb7hH8MSUJpSbSDYk0k2',   // Alice — urgent, close-to-the-action field reporter energy
    webLocale: 'en-US', webVoiceName: 'Ana',    // US American English — Microsoft Ana Neural
    color: 'text-lime-400', bg: 'bg-lime-950/30', border: 'border-lime-800/60', initials: 'EV', avatar: '/anchors/vargas.png',
  },
]

// ── Broadcast Script — DAY 27 static fallback (live digest overrides this) ──
const SEGMENTS: Segment[] = [
  {
    id: 1, anchor: 'sarah', label: 'Opening Headlines — Day 27', topic: 'Breaking News',
    script: `Good evening. I'm Sarah Mitchell, and this is Epic Fury News Network. Tonight, Day Twenty-Seven of Operation Epic Fury — and for the first time since this conflict began, we lead not with strikes or losses, but with the word peace. At eleven-thirty Zulu this morning, the President of the United States addressed the nation from the Oval Office and announced the Abu Dhabi Ceasefire Framework: a sixty-hour cessation of offensive operations, mediated jointly by the Sultanate of Oman and the United Arab Emirates, with Abu Dhabi hosting the first face-to-face diplomatic session — expected to begin at zero-nine-hundred Zulu tomorrow. At the same hour, CENTCOM released its Day Twenty-Seven SITREP, reporting that coalition air forces have flown over ten thousand four hundred combat sorties since Day One, the Strait of Hormuz ZB-Alpha corridor is seventy-eight percent cleared of mines, and Iran's air defense and ballistic missile infrastructure is assessed as ninety-four percent degraded. We must also report tonight: on Day Twenty-Six, Iran launched its fifth and final ballistic missile barrage — thirty-one Fateh-110 and Ghadr missiles aimed at Al Dhafra and Al Udeid Air Bases. Coalition THAAD and Patriot batteries achieved an eighty-six percent intercept rate. Two members of the United States Air Force were killed. Their sacrifice is honored in tonight's broadcast. James?`,
    citations: [
      'White House Oval Office Address — D27 1130Z',
      'CENTCOM Day 27 SITREP — Public Affairs Release',
      'SBIRS/DSP Launch Data — 5th BM Barrage D26',
      'THAAD/PAC-3 Intercept Summary D26',
    ],
  },
  {
    id: 2, anchor: 'james', label: 'Air Superiority & CENTCOM D27 SITREP', topic: 'Operations Overview',
    script: `Thank you, Sarah. The CENTCOM Day Twenty-Seven SITREP is a document that the coalition air community has been working toward for twenty-seven days. Over ten thousand four hundred combat sorties flown. The IRGC Air Force — once possessing two hundred and forty-four combat aircraft — is now assessed as a non-factor. No IRGCAF combat sortie has been detected in seventy-two hours. The last two operational F-14 Tomcats, callsigns BANDIT-Alpha and Bravo, were destroyed on Day Twenty-One by VIPER flight. F-35A sorties are back to eighty-five percent of pre-conflict rate following runway repair work at Al Dhafra completed on Day Twenty-One. B-21 Raider ANVIL-01, whose combat debut on Day Twenty-Two struck the Natanz hardened complex with two thirty-thousand-pound Massive Ordnance Penetrators, remains in theater. The coalition now has uncontested air dominance over all of Iran's territory. CENTCOM's strategic assessment: degradation objectives have been met. The air campaign is transitioning from strike operations to enforcement and deterrence posture in support of the Abu Dhabi diplomatic process. Doctor Chen?`,
    citations: [
      'CENTCOM Day 27 SITREP — Public Affairs Release',
      'CAOC BLUE DAGGER Air Superiority Assessment D27',
      'Al Dhafra Air Base Runway Repair After-Action D21',
      'ISW — Op Epic Fury Air Campaign Assessment D27',
    ],
  },
  {
    id: 3, anchor: 'maya', label: 'DIA BDA Flash — 94% Degradation', topic: 'Defense Intel',
    script: `James, the most significant intelligence release of this entire conflict came on Day Twenty-Five, and I want to give it the attention it deserves tonight. The Defense Intelligence Agency issued a BDA flash assessment — battle damage assessment — concluding that Iran's nuclear enrichment and weapons-development infrastructure has been degraded by ninety-four percent. The DIA's estimate: eighteen to twenty-four months before Iran could reconstitute meaningful enrichment capability even if this conflict ended today and all sanctions were lifted immediately. Natanz is seventy percent collapsed. Fordow is assessed as mission-killed without radiological release — a remarkable MCM outcome. The IAEA has confirmed zero radiological events across all known Iranian nuclear sites since Day One. Now, on the active threat picture: GOLF-7, the Iranian Kilo-class submarine that mined the ZB-Alpha corridor through Day Twenty-Four, has been tracked to Bandar Abbas and has not sortied since Day Twenty-Two. IRGCN surface threat is reduced to an estimated thirty percent of pre-conflict capability. The fifth BM barrage on Day Twenty-Six — thirty-one Fateh-110 and Ghadr missiles — represented Iran's remaining functional missile stockpile. DIA assesses residual Iranian ballistic missile inventory at five to eight percent of pre-conflict levels. Dr. Rostami?`,
    citations: [
      'DIA BDA Flash Assessment — Iran Nuclear Infrastructure D25',
      'IAEA — Nuclear Safeguards Verification D27 0600Z',
      'MANTIS ACINT — GOLF-7 Track Update D27',
      'TRIDENT STRATCOM Monitor — 5th BM Barrage Assessment D26',
    ],
  },
  {
    id: 4, anchor: 'rostami', label: 'Nuclear Threat: Effectively Neutralized', topic: 'Nuclear Watch',
    script: `Thank you, Doctor Chen. The DIA's ninety-four percent degradation figure is the headline, but the strategic meaning runs deeper. When this conflict began on Day One, Iran was approximately three to five weeks from weapons-grade enrichment breakout. Twenty-seven days later, that breakout timeline has been reset to eighteen months at minimum — and that calculation assumes reconstruction begins tomorrow with full international cooperation, which will not happen. Fordow, the hardened enrichment facility buried under two hundred and ninety feet of mountain rock in Qom — the facility that Iran's leadership believed was invulnerable — was destroyed. The B-21 Raider and the GBU-57B Massive Ordnance Penetrator proved no hardened facility is beyond reach. Natanz enrichment hall bravo and the cascade assembly tunnel are collapsed. The only remaining question at the nuclear level is whether any enriched material was covertly dispersed prior to Day One strikes. The IAEA has been denied physical access since Day One. The Abu Dhabi framework — if it holds — will include an IAEA access provision as a condition of the ceasefire. That access provision is, in my professional judgment, the single most important clause in whatever document comes out of Abu Dhabi tomorrow. Colonel Harris?`,
    citations: [
      'IAEA — Iran Nuclear Safeguards Verification D27',
      'NTI — Fordow Facility Technical Assessment 2025',
      'RAND — Iranian Nuclear Reconstitution Timeline Analysis 2026',
      'ORACLE-9 — Nuclear Risk Model Day 27 Final Assessment',
    ],
  },
  {
    id: 5, anchor: 'harris', label: 'Day 26 BM Barrage — 2 USAF KIA', topic: 'Military Analysis',
    script: `Good evening. I need to begin with our fallen. On Day Twenty-Six, at zero-two-thirty-seven Zulu, Iran launched its fifth and final ballistic missile barrage — thirty-one missiles: Fateh-110 solid-fuel short-range ballistic missiles and Ghadr medium-range variants, from five separate launch sites across western Iran. Twenty-six were intercepted by THAAD and Patriot PAC-3 batteries. Five impacted across two airfields, Al Dhafra and Al Udeid. Two members of the United States Air Force were killed in action. Six were wounded. Their names will not be released until next-of-kin notification is complete. But tonight, this broadcast honors their service. The THAAD intercept rate across all five barrages of this conflict is eighty-six percent — twenty-seven of thirty-one on the final barrage, and one hundred and ten of one hundred and twenty-eight total across the full campaign. That is extraordinary performance by antimissile crews who have been at combat readiness for twenty-seven consecutive days without rotation. On the Hormuz picture: ZB-Alpha is seventy-eight percent cleared. Surface threat is at thirty percent of pre-conflict IRGCN strength. GOLF-7 is inactive. The tactical picture has stabilized and supports the diplomatic process opening tomorrow. Natasha?`,
    citations: [
      'CENTCOM J3 — 5th BM Barrage After-Action Assessment D26',
      'THAAD Program Office — Intercept Summary All 5 Barrages',
      'NAVCENT CTF-54 Maritime Threat Assessment D27',
      'MDA — Theater Missile Defense Combat Performance D27',
    ],
  },
  {
    id: 6, anchor: 'natasha', label: 'Abu Dhabi Framework & Iran\'s Shifted Posture', topic: 'Foreign Affairs',
    script: `Thank you Colonel. Twenty-seven days ago the COMPASS model gave a two percent probability of a ceasefire framework in the first month of this conflict. Tonight that probability stands at sixty-eight percent within seventy-two hours — and the framework is already open. Let me walk through what changed. On Day Twenty-Five, the United Nations Security Council passed Resolution 2731 by fourteen votes to one — Russia vetoing a stronger French-sponsored resolution, then backing the humanitarian corridor compromise. UNSCR 2731 opened a humanitarian corridor and set a sixty-day deadline for broader negotiations. On Day Twenty-Six, the Iranian Supreme National Security Council did something remarkable: they formally dropped their standing precondition that all US forces withdraw from the region before any ceasefire talks. That precondition had blocked every back-channel for twenty-six days. Dropping it — announced through Oman — was the signal Abu Dhabi needed to invite both sides to the table. The UAE is now a co-mediator alongside Oman. The Omani channel, which was suspended briefly on Day Twenty-Four, was reactivated on Day Twenty-Six at eleven-fifteen Zulu. COMPASS assesses the probability of a signed sixty-hour cessation of hostilities by midnight tomorrow at twenty-seven percent, with eighty-two percent probability of a signed framework document within seven days. Marcus?`,
    citations: [
      'UN Security Council — UNSCR 2731 Vote Record D25',
      'Reuters — Iran SNSC Precondition Statement D26',
      'COMPASS Diplomatic Probability Model D27 0600Z',
      'State Department Background Briefing — Abu Dhabi Framework D27',
      'Oman MFA — Mediation Channel Reactivation Statement D26',
    ],
  },
  {
    id: 7, anchor: 'marcus', label: 'Markets Stabilizing — Brent $94', topic: 'Markets & Energy',
    script: `Sarah, the economic picture on Day Twenty-Seven shows the first sustained signs of recovery. Brent crude is at ninety-four dollars per barrel tonight — down from a wartime peak of one hundred and twenty-three dollars on Day Seventeen, and twenty-four dollars below the peak. The moment the Abu Dhabi framework was announced this morning, Brent dropped three dollars in fourteen minutes. More significantly: for the first time since Day Three, commercial tankers are transiting the Strait of Hormuz. Seven very large crude carriers have transited the ZB-Alpha corridor under coalition naval escort since Day Twenty-Four. Each transit reduces Cape of Good Hope diversion pressure. Lloyd's war-risk insurance premiums for Hormuz passed from four hundred and ten percent of baseline three days ago to two hundred and ninety percent today — still elevated, but declining directionally. Asian LNG spot prices have fallen fifteen percent in forty-eight hours on the Abu Dhabi announcement. The Saudi OPEC Plus production increase — two million barrels per day — was formally announced this morning, timed deliberately with the President's address. Our COMPASS energy-finance cascade model has retired the recession-trigger alert it issued on Day Fifteen. The economic pressure that Tehran could not sustain has driven them to this table. I'm Marcus Thompson. Sarah?`,
    citations: [
      'EIA — Brent Crude Futures Report D27 1800Z',
      'Baltic Exchange — War Risk Premium Update D27',
      'Bloomberg Terminal — LNG Spot Pricing March 2026 D27',
      'Saudi Aramco — OPEC Plus Production Announcement D27',
      'COMPASS ML Energy-Finance Cascade Model v2.5 D27',
    ],
  },
  {
    id: 8, anchor: 'walsh', label: 'Pentagon & POTUS Ceasefire Address', topic: 'DoD Briefing',
    script: `Sarah, I'm Lieutenant General Walsh at the Pentagon. This building had a different energy this morning. The President's Oval Office address was carefully coordinated with the Joint Chiefs and CENTCOM — the military assessment drove the diplomatic timing. The Joint Chiefs advised the President that the military objectives set on Day One have been substantially achieved: Iran's nuclear program is ninety-four percent degraded, its air force is non-functional, its ballistic missile stockpile is near-exhausted, and the IRGCN surface threat is at thirty percent of pre-war strength. Given that assessment, continued offensive operations would yield diminishing military returns relative to the political cost. Secretary Austin addressed the press pool at fourteen-hundred hours: quote — "The United States has demonstrated the reach, precision, and sustained commitment of American military power. We have achieved our core national security objectives. We support the President's decision to pursue the Abu Dhabi Framework and give diplomacy the opportunity to secure what our armed forces have made possible." End quote. For the two Air Force members killed on Day Twenty-Six — the Secretary said this: quote — "They gave everything for a mission that has now created the conditions for peace." The Pentagon's message tonight: the military objectives are met; the diplomatic window is open. Sarah?`,
    citations: [
      'White House — Oval Office Ceasefire Framework Address D27 1130Z',
      'Pentagon Press Secretary Briefing D27 1400 EST',
      'CENTCOM PA — Military Objectives Assessment D27',
      'Joint Chiefs — NCA Briefing Summary D27 (Public Release)',
    ],
  },
  {
    id: 9, anchor: 'vargas', label: 'Forward — ZB-Alpha 78% Cleared', topic: 'Field Report',
    script: `Sarah, I'm Corporal Vargas aboard a coalition MCM coordination vessel in the Strait of Hormuz, approximately eighteen miles inside the ZB-Alpha corridor. I want to describe what this place looks like right now. Yesterday, a Qatari-flagged VLCC five hundred meters ahead of us ran the corridor under coalition escort. The sailors on MCM-14 Chief and MCM-11 Gladiator stopped what they were doing and watched that tanker pass. That was the seventh commercial transit since Day Twenty-Four. After twenty-four days of having this strait to themselves, commerce is coming back. The corridor behind us — thirty-one nautical miles of it — is cleared. Seventy-eight percent of the full length. GOLF-7, the Kilo-class sub that mined half this route in the dark, has been tracked to Bandar Abbas and hasn't sortied in five days. SSN-777 North Carolina has not returned to port. The MCM crews out here know about the President's address. I asked petty officer first class Herrera from MCM-14 what it meant. He said: we don't stop sweeping until the final mine is pulled. The corridor doesn't open until it's fully clear. That is the Navy way. The diplomatic talks open tomorrow. The sailors of ZB-Alpha will not be sleeping in. I'm Corporal Elena Vargas, Epic Fury News Network, Strait of Hormuz, Day Twenty-Seven.`,
    citations: [
      'CTF-52 MCM ZB-Alpha Status Report D27 0900Z',
      'NAVCENT SITREP D27 — MCM Corridor Clearance Update',
      'MANTIS ACINT — GOLF-7 Track Bandar Abbas Confirmed D27',
    ],
  },
  {
    id: 10, anchor: 'sarah', label: 'Closing Broadcast — Day 27', topic: 'Summary & Outlook',
    script: `Thank you Elena, and thank you to every member of our field and analysis team — and to every coalition service member whose courage made this broadcast possible for twenty-seven nights. To close Day Twenty-Seven: the President of the United States announced the Abu Dhabi Ceasefire Framework this morning; diplomatic talks open tomorrow at nine-hundred Zulu with Oman and the UAE as co-mediators. CENTCOM confirms over ten thousand four hundred coalition combat sorties, seventy-eight percent Hormuz MCM clearance, and Iran's military infrastructure ninety-four percent degraded. Iran dropped its withdrawal precondition on Day Twenty-Six; UNSCR 2731 passed on Day Twenty-Five. COMPASS ceasefire probability stands at sixty-eight percent within seventy-two hours. Brent crude is ninety-four dollars — falling. Seven tankers have transited ZB-Alpha. And we remember the two members of the United States Air Force killed on Day Twenty-Six when Iran fired its final thirty-one missiles at coalition bases — their sacrifice, and the sacrifice of every coalition service member lost in this conflict, will not be forgotten. The mission they gave everything for is now closer than ever to resolution. I'm Sarah Mitchell. Epic Fury News Network. Every segment fully sourced. Every claim independently verified. God bless the United States of America, and God bless every uniform who stood watch tonight.`,
    citations: [
      'NEXUS — All-Domain Assessment D27 Final',
      'HERALD-3 — Truth Synthesis Report #69',
      'ORACLE-9 — 72-hour Strategic Forecast D27',
      'COMPASS Ceasefire Model D27 2000Z',
      'CENTCOM PA — Final D27 SITREP',
    ],
  },
]

// ── Live segment builder — driven by /api/intel/digest ───────────────────────

interface DigestSummary {
  ok?: boolean
  conflictDay: number
  assessmentLevel: string
  assessmentReason: string
  aiNarrative: string | null
  keyDevelopments: { title: string; theater: string; confidence: number }[]
  topThreats: { label: string; domain: string; probability: number; severity: string }[]
  economics: { brentUsd: number; lloydWarRiskPct: number; hormuzThroughputMbpd: number }
}

function buildSegmentsFromDigest(d: DigestSummary): Segment[] {
  const day     = d.conflictDay
  const devs    = d.keyDevelopments ?? []
  const threats = d.topThreats ?? []
  const econ    = d.economics ?? { brentUsd: 109, lloydWarRiskPct: 3.5, hormuzThroughputMbpd: 8.2 }
  const top     = devs[0]?.title ?? 'No new developments in this cycle'
  const brent   = econ.brentUsd?.toFixed(0) ?? '109'
  const warRisk = econ.lloydWarRiskPct?.toFixed(1) ?? '3.5'
  const hormuz  = econ.hormuzThroughputMbpd?.toFixed(1) ?? '8.2'
  const t1      = threats[0]
  const t2      = threats[1]
  const pct = (p: number | undefined) => p != null ? `${Math.round(p * 100)}%` : '—'
  const airDev  = devs.find(k => k.theater === 'Air')      ?? devs[1]
  const econDev = devs.find(k => k.theater === 'Economic') ?? devs[2]
  const nuclDev = devs.find(k => k.theater === 'Nuclear' || k.theater === 'Strategic') ?? devs[3]
  const dipDev  = devs.find(k => k.theater === 'Diplomatic') ?? devs[4]
  const seaDev  = devs.find(k => k.theater === 'Maritime' || k.theater === 'Hormuz')   ?? devs[5]

  // Time-aware greeting so it doesn't always say "Good evening"
  const hourUTC = new Date().getUTCHours()
  const greeting = hourUTC < 12 ? 'Good morning' : hourUTC < 17 ? 'Good afternoon' : 'Good evening'

  return [
    {
      id: 1, anchor: 'sarah', label: `Opening Headlines — Day ${day}`, topic: 'Breaking News',
      script: d.aiNarrative
        ? `${greeting} from Epic Fury News Network. Day ${day} of Operation Epic Fury. ${d.aiNarrative.slice(0, 700).replace(/\n/g, ' ')} James?`
        : `${greeting}. Epic Fury News Network, Day ${day}. Assessment level: ${d.assessmentLevel}. ${top}. ${d.assessmentReason ?? ''}. James?`,
      citations: ['NEXUS Intel Digest', 'HERALD-3 Live Feed'],
    },
    {
      id: 2, anchor: 'james', label: `Air Operations — Day ${day}`, topic: 'Operations Overview',
      script: `Thank you Sarah. Air operations today: ${airDev?.title ?? 'Coalition air operations continue across the theater'}. ${t1 ? `ORACLE-9 top threat: ${t1.label} at ${pct(t1.probability)} — ${t1.severity} severity.` : ''} Dr. Chen?`,
      citations: ['CAOC BLUE DAGGER', 'CENTCOM PA'],
    },
    {
      id: 3, anchor: 'maya', label: `Threat Assessment — Day ${day}`, topic: 'Defense Analysis',
      script: `Threat picture: ${threats.length} active models. ${t1 ? `${t1.label} — ${pct(t1.probability)}, ${t1.severity}.` : 'Top threat updating.'} ${t2 ? `Second: ${t2.label} — ${pct(t2.probability)}, ${t2.severity}.` : ''} Overall: ${d.assessmentLevel}. Colonel Harris?`,
      citations: ['ORACLE-9 Probabilistic Engine', 'DIA Assessment'],
    },
    {
      id: 4, anchor: 'harris', label: `Military Situation — Day ${day}`, topic: 'Military Analysis',
      script: `Combined arms picture: ${devs.slice(0, 3).map(k => k.title).join('. ')}. ${d.assessmentLevel} conditions theatre-wide. FPCON DELTA maintained. Natasha?`,
      citations: ['CENTCOM J2', 'ISW Operational Assessment'],
    },
    {
      id: 5, anchor: 'natasha', label: `Diplomatic — Day ${day}`, topic: 'Foreign Affairs',
      script: `Diplomatically: ${dipDev?.title ?? 'Omani and Qatari back-channels remain active with no breakthrough.'}. UNSC deadlocked. ${d.assessmentLevel} conditions persist. Marcus?`,
      citations: ['State Dept Briefing', 'Reuters Diplomatic'],
    },
    {
      id: 6, anchor: 'marcus', label: `Economic Impact — Day ${day}`, topic: 'Economics',
      script: `Economic cascade: Brent at $${brent} per barrel. Hormuz throughput: ${hormuz} million barrels per day. Lloyd's war risk: ${warRisk}%. ${econDev?.title ?? 'Global supply disruption continues.'}. Patricia?`,
      citations: ['Bloomberg Energy', 'COMPASS Economic Model'],
    },
    {
      id: 7, anchor: 'walsh', label: `Pentagon Readiness — Day ${day}`, topic: 'Defense Readiness',
      script: `Pentagon: NEXUS processed ${devs.length} verified intel items this cycle. Assessment: ${d.assessmentLevel}. ${d.assessmentReason ?? ''}. All coalition forces DEFCON-3 or higher. Dr. Rostami?`,
      citations: ['DoD PA Briefing', 'NEXUS Platform Health'],
    },
    {
      id: 8, anchor: 'rostami', label: `Nuclear & Iran — Day ${day}`, topic: 'Nuclear Analysis',
      script: `Nuclear and Iran watch: ${nuclDev?.title ?? 'No new nuclear developments this cycle. IAEA monitoring offline since Day 5.'}. Succession dynamic drives escalation risk. ${d.assessmentLevel} — ${d.assessmentReason ?? ''}. Elena?`,
      citations: ['IAEA', 'Arms Control Association', 'ORACLE-9 Nuclear Model'],
    },
    {
      id: 9, anchor: 'vargas', label: `Maritime & Hormuz — Day ${day}`, topic: 'Field Report',
      script: `Gulf of Oman: ${seaDev?.title ?? 'Mine clearance continues in corridor ZB-Alpha.'}. IRGCN maritime threat: ${threats.find(t => t.domain === 'Maritime') ? pct(threats.find(t => t.domain === 'Maritime')?.probability) : 'monitoring'}. Elena Vargas, Epic Fury News Network, Gulf of Oman, Day ${day}.`,
      citations: ['UKMTO Advisory', 'CTF-52 MCM Report'],
    },
    {
      id: 10, anchor: 'sarah', label: `Day ${day} Closing Summary`, topic: 'Summary & Outlook',
      script: `To recap Day ${day}: ${devs.slice(0, 4).map(k => k.title).join('. ')}. Assessment: ${d.assessmentLevel}. ORACLE-9 top threat: ${t1?.label ?? 'all domains elevated'} at ${pct(t1?.probability)}. Brent: $${brent}. For all personnel in the theater tonight — this broadcast honors your service. I'm Sarah Mitchell. Epic Fury News Network.`,
      citations: ['NEXUS All-Domain Assessment', 'ORACLE-9', 'COMPASS', 'CENTCOM PA'],
    },
  ]
}

// ── Web Speech voice picker ───────────────────────────────────────────────────
// Supports diverse English locales so each anchor's accent is matched by the
// browser's available voices. Priority: exact preferred name → locale gender
// hints → any voice for locale → any English voice → first available.
function pickVoice(gender: 'M' | 'F', preferred: string, locale = 'en-US'): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined') return null
  const voices = window.speechSynthesis.getVoices()
  const norm = (l: string) => l.replace('_', '-')
  const localeVoices = voices.filter(v => norm(v.lang).startsWith(locale))

  // 1. Exact preferred name match within locale
  const byName = localeVoices.find(v => v.name.includes(preferred))
  if (byName) return byName

  // 2. Gender-specific modern neural voice hints per locale (Microsoft/Apple/Google)
  const hints: Record<string, { F: string[]; M: string[] }> = {
    'en-US': {
      F: ['Aria', 'Jenny', 'Ana', 'Michelle', 'Emma', 'Ava', 'Elizabeth', 'Zira', 'Samantha', 'Susan'],
      M: ['Guy', 'Eric', 'Brian', 'Davis', 'Andrew', 'Christopher', 'Alex', 'Tom', 'David'],
    },
    'en-GB': {
      F: ['Sonia', 'Libby', 'Mia', 'Serena', 'Alice', 'Emma'],
      M: ['Ryan', 'Daniel', 'Thomas', 'Oliver', 'George'],
    },
    'en-AU': {
      F: ['Natasha', 'Catherine', 'Karen', 'Lee'],
      M: ['William', 'Tim', 'James'],
    },
    'en-IN': {
      F: ['Neerja', 'Heera', 'Raveena', 'Veena', 'Priya'],
      M: ['Prabhat', 'Ravi', 'Kanan'],
    },
    'en-IE': {
      F: ['Emily', 'Iona', 'Moira'],
      M: ['Sean', 'Conor'],
    },
    'en-ZA': {
      F: ['Leah', 'Thandeka'],
      M: ['Luke', 'Ethan'],
    },
  }
  const locHints  = hints[locale] ?? hints['en-US']
  const byHint = localeVoices.find(v => (gender === 'F' ? locHints.F : locHints.M).some(h => v.name.includes(h)))
  if (byHint) return byHint

  // 3. Any voice available for this locale
  if (localeVoices.length > 0) return localeVoices[0]

  // 4. Fallback to any English voice then first available
  const enVoices = voices.filter(v => norm(v.lang).startsWith('en'))
  return enVoices[0] ?? voices[0] ?? null
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function NewsroomPage() {
  const [currentIdx,    setCurrentIdx]    = useState(0)
  const [playMode,      setPlayMode]      = useState<PlayMode>('idle')
  const [activeAnchor,  setActiveAnchor]  = useState<AnchorId | null>(null)
  const [usingEL,       setUsingEL]       = useState(false)
  const [elAvailable,   setElAvailable]   = useState<boolean | null>(null)
  const elAvailableRef = useRef<boolean | null>(null) // stable ref so playSegment closure reads latest
  const [waveH,         setWaveH]         = useState<number[]>(Array(10).fill(4))
  const [liveSegments,  setLiveSegments]  = useState<Segment[]>(SEGMENTS)
  const [tickerItems,   setTickerItems]   = useState<string[]>(BASE_TICKER_ITEMS)

  // Load ticker from real live intel items (not scripted events)
  useEffect(() => {
    if (!SUPABASE_CONFIGURED) return
    const sb = createBrowserClient()
    ;(async () => {
      try {
        const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
        const { data } = await sb
          .from('intel')
          .select('title, confidence, theater, source_name')
          .gte('created_at', since)
          .gte('confidence', 60)
          .order('confidence', { ascending: false })
          .order('created_at', { ascending: false })
          .limit(30)
        if (!data || data.length === 0) return
        const liveItems = (data as Array<{ title: string; confidence: number; theater: string; source_name: string | null }>)
          .map(item => {
            const src = item.source_name ? ` [${item.source_name}]` : ''
            const theater = item.theater && item.theater !== 'Unknown' ? ` · ${item.theater.toUpperCase()}` : ''
            const conf = item.confidence >= 85 ? `⚡ FLASH: ` : item.confidence >= 70 ? `⚠ ` : ''
            return `${conf}${item.title}${theater}${src}`
          })
        setTickerItems(liveItems)
      } catch { /* keep base items */ }
    })()
  }, [])

  const audioRef    = useRef<HTMLAudioElement | null>(null)
  const playModeRef = useRef<PlayMode>('idle')

  // On mount: clear stale EL block — previous code incorrectly blocked on 403s
  useEffect(() => {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('el-tts-unavailable-until')
      elAvailableRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])


  // ── AI Newsroom Agent — fetch or generate Day N broadcast scripts ──────────
  useEffect(() => {
    let cancelled = false
    let seedTriggered = false

    const load = async () => {
      // Run cached-scripts + live digest in parallel (both fast)
      const [aiRes, digestRes] = await Promise.allSettled([
        fetch('/api/newsroom/generate', { cache: 'no-store' }),
        fetch('/api/intel/digest',      { cache: 'no-store' }),
      ])

      if (cancelled) return

      // 1. Prefer AI-cached scripts (sub-1s, returned only when cached in Supabase)
      let hasCachedAI = false
      if (aiRes.status === 'fulfilled' && aiRes.value.ok) {
        try {
          const aiData = await aiRes.value.json() as { ok: boolean; segments?: GeneratedSegment[] }
          if (aiData.ok && Array.isArray(aiData.segments) && aiData.segments.length >= 9) {
            setLiveSegments(aiData.segments as Segment[])
            hasCachedAI = true
          } else if (!aiData.ok && !seedTriggered) {
            // No cache yet — fire background seed generation (one-shot, self-throttled)
            seedTriggered = true
            fetch('/api/newsroom/seed', { cache: 'no-store' }).catch(() => {/* best-effort */})
          }
        } catch { /* fall through */ }
      }

      // 2. Always show live digest content while AI scripts load/generate
      if (!hasCachedAI && digestRes.status === 'fulfilled' && digestRes.value.ok) {
        try {
          const d = await digestRes.value.json() as DigestSummary
          if (d.ok !== false && d.keyDevelopments?.length > 0) {
            setLiveSegments(buildSegmentsFromDigest(d))
            hasCachedAI = true
          }
        } catch { /* fall through to dynamic fallback */ }
      }

      // 3. Dynamic day-aware fallback when both API calls fail/return empty
      if (!hasCachedAI) {
        setLiveSegments(buildDayAwareBroadcast() as Segment[])
      }
    }

    load()

    // Re-poll every 5 min — picks up newly cached AI scripts + fresh intel
    const interval = setInterval(() => {
      if (typeof navigator !== 'undefined' && !navigator.onLine) return
      if (typeof document !== 'undefined' && document.hidden) return
      load()
    }, 5 * 60 * 1000)

    // Reload immediately when tab becomes visible again
    const onVisible = () => { if (typeof document !== 'undefined' && !document.hidden) load() }
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisible)

    return () => {
      cancelled = true
      clearInterval(interval)
      if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

  useEffect(() => { playModeRef.current = playMode }, [playMode])

  // Waveform animation while playing
  useEffect(() => {
    if (playMode !== 'playing') { setWaveH(Array(10).fill(4)); return }
    const iv = setInterval(() => {
      setWaveH(Array(10).fill(0).map(() => Math.floor(Math.random() * 18) + 3))
    }, 120)
    return () => clearInterval(iv)
  }, [playMode])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      audioRef.current?.pause()
      if (typeof window !== 'undefined') window.speechSynthesis?.cancel()
    }
  }, [])

  const stopAll = () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; audioRef.current = null }
    if (typeof window !== 'undefined') window.speechSynthesis?.cancel()
    setPlayMode('idle')
    setActiveAnchor(null)
  }

  const playViaWebSpeech = (seg: Segment, onEnd: () => void) => {
    const anchor = TEAM.find(t => t.id === seg.anchor) ?? TEAM[0]
    // Voices may not be loaded yet — re-query inside useEffect territory
    const trySpeak = () => {
      if (!window.speechSynthesis) return
      const utt = new SpeechSynthesisUtterance(seg.script)
      utt.voice   = pickVoice(anchor.gender, anchor.webVoiceName, anchor.webLocale)
      utt.rate    = 0.91
      utt.pitch   = anchor.gender === 'F' ? 1.05 : 0.88
      utt.volume  = 1.0
      utt.onend   = () => { if (playModeRef.current !== 'idle') onEnd() }
      utt.onerror = () => setPlayMode('idle')
      window.speechSynthesis.speak(utt)
      setPlayMode('playing')
    }
    // Chrome/Edge: voices load asynchronously
    if (window.speechSynthesis.getVoices().length > 0) {
      trySpeak()
    } else {
      window.speechSynthesis.onvoiceschanged = () => { trySpeak(); window.speechSynthesis.onvoiceschanged = null }
    }
  }

  // Recursive play — each segment calls next when it ends
  const playSegment = async (idx: number) => {
    if (idx >= liveSegments.length) { stopAll(); return }

    const seg    = liveSegments[idx]
    const anchor = TEAM.find(t => t.id === seg?.anchor) ?? TEAM[0]

    setCurrentIdx(idx)
    setActiveAnchor(seg.anchor)
    setPlayMode('loading')

    // ── Try ElevenLabs (skip only on auth failure — 401/403 = key bad, block 30 min) ───
    const elCachedTs = typeof window !== 'undefined' ? Number(sessionStorage.getItem('el-tts-unavailable-until') ?? 0) : 0
    const elCached = elCachedTs > Date.now()
    // If the expiry has passed, reset the ref so we try again
    if (!elCached && elAvailableRef.current === false) { elAvailableRef.current = null; setElAvailable(null) }
    if (elAvailableRef.current !== false && !elCached) {
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: seg.script, voiceId: anchor.voiceId }),
      })

      if (res.ok) {
        const blob = await res.blob()
        const url  = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audioRef.current = audio
        audio.onended = () => { URL.revokeObjectURL(url); setTimeout(() => playSegment(idx + 1), 1500) }
        await audio.play()
        setPlayMode('playing')
        setUsingEL(true)
        elAvailableRef.current = true
        setElAvailable(true)
        return
      }
      // Only permanently block on true ElevenLabs auth failures (401 = API key wrong/expired).
      // 403 = our own session gate (user not signed in) — fall through silently, clear any old block.
      if (res.status === 401) {
        elAvailableRef.current = false
        setElAvailable(false)
        sessionStorage.setItem('el-tts-unavailable-until', String(Date.now() + 30 * 60 * 1000))
      } else if (res.status === 403) {
        // Session gate — not a permanent ElevenLabs failure; clear stale block so it retries on next load
        sessionStorage.removeItem('el-tts-unavailable-until')
        elAvailableRef.current = null
      }
      // fall through to web speech for this segment
    } catch {
      // network error — fall through to web speech, but retry ElevenLabs on next segment
    }
    } // end elAvailable check

    // ── Fallback: Web Speech API ────────────────────────────────────────
    // Do NOT permanently disable ElevenLabs — only 401 (bad API key) warrants that.
    // All other errors (network, 403, 422, 503) are transient — retry on next segment.
    setUsingEL(false)
    playViaWebSpeech(seg, () => {
      // Brief anchor transition — 1.5s gap between segments (not 60s)
      setTimeout(() => playSegment(idx + 1), 1500)
    })
  }

  const togglePause = () => {
    if (playMode === 'playing') {
      if (usingEL && audioRef.current) audioRef.current.pause()
      else window.speechSynthesis?.pause()
      setPlayMode('paused')
    } else if (playMode === 'paused') {
      if (usingEL && audioRef.current) audioRef.current.play()
      else window.speechSynthesis?.resume()
      setPlayMode('playing')
    }
  }

  const skipTo = (idx: number) => {
    stopAll()
    setTimeout(() => playSegment(idx), 80)
  }

  const seg    = liveSegments[currentIdx] ?? liveSegments[0]
  const anchor = TEAM.find(t => t.id === seg?.anchor) ?? TEAM[0]

  // Waveform bars (reusable inline)
  const Bars = ({ count = 10, colorClass }: { count?: number; colorClass: string }) => (
    <div className="flex items-center gap-0.5" style={{ height: 20 }}>
      {waveH.slice(0, count).map((h, i) => (
        <div
          key={i}
          className={`w-0.5 rounded-full transition-all duration-100 ${playMode === 'playing' ? colorClass : 'bg-zinc-700'}`}
          style={{ height: playMode === 'playing' ? h : 4 }}
        />
      ))}
    </div>
  )

  return (
    <section className="newsroom-studio space-y-0 pb-8 -m-4 md:-m-6">

      {/* ══════════════════════════════════════════════════════════════
          BROADCAST STUDIO MASTHEAD — Cinematic gradient with sweep
          ══════════════════════════════════════════════════════════════ */}
      <div className="studio-masthead border-b border-red-900/30">
        {/* Top classification bar */}
        <div className="bg-red-950/60 border-b border-red-900/40 px-4 py-1 flex items-center justify-between">
          <span className="text-[7px] tracking-[0.5em] text-red-400/60 uppercase">Unclassified // AI-Synthesized // Live Broadcast</span>
          <span className="text-[7px] tracking-[0.4em] text-red-400/40 uppercase font-mono">Signal Verified · Feed Active</span>
        </div>

        {/* Main header */}
        <div className="px-6 py-5 flex items-center gap-5">
          {/* Network logo / call sign */}
          <div className="flex-shrink-0">
            <div className="w-16 h-16 rounded border-2 border-red-700/60 bg-red-950/30 flex flex-col items-center justify-center relative">
              <Tv size={22} className="text-red-400" />
              <span className="text-[6px] tracking-[0.4em] text-red-400/80 mt-1 uppercase">EFNN</span>
              {playMode === 'playing' && (
                <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-red-500 animate-pulse" />
              )}
            </div>
          </div>

          {/* Title block */}
          <div className="flex-1">
            <p className="text-[7px] tracking-[0.6em] text-zinc-600 uppercase mb-1">Operation Epic Fury — War Correspondent Bureau</p>
            <h1 className="text-2xl md:text-3xl font-black text-white tracking-[0.15em] uppercase leading-none">
              EPIC FURY <span className="text-red-400">NEWS NETWORK</span>
            </h1>
            <div className="studio-accent-bar mt-2 w-full max-w-md" />
            <div className="flex items-center gap-4 mt-2">
              <span className="text-[8px] tracking-[0.3em] text-zinc-500 uppercase" suppressHydrationWarning>
                Day {CONFLICT_DAY} · {CONFLICT_DATE_STR}
              </span>
              <span className="text-[8px] text-zinc-700">|</span>
              <span className="text-[8px] tracking-[0.3em] text-zinc-500 uppercase">{liveSegments.length} Segments · {TEAM.length} Anchors</span>
              <span className="text-[8px] text-zinc-700">|</span>
              <span className="text-[8px] tracking-[0.3em] text-emerald-600 uppercase">AI-Powered Voices</span>
            </div>
          </div>

          {/* On-Air status */}
          <div className="flex-shrink-0 text-right">
            {playMode === 'playing' ? (
              <div className="on-air-badge inline-flex items-center gap-2 px-4 py-2 bg-red-900/40 border border-red-600/60 rounded">
                <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                <span className="text-sm font-black text-red-400 tracking-[0.3em] uppercase">ON AIR</span>
              </div>
            ) : playMode === 'loading' ? (
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-950/30 border border-amber-800/40 rounded">
                <span className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs font-bold text-amber-400 tracking-[0.2em] uppercase">Loading</span>
              </div>
            ) : playMode === 'paused' ? (
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-950/20 border border-amber-900/40 rounded">
                <span className="text-xs font-bold text-amber-500 tracking-[0.2em] uppercase">⏸ Paused</span>
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 px-3 py-2 bg-zinc-900/60 border border-zinc-800/60 rounded">
                <span className="w-2 h-2 rounded-full bg-zinc-600" />
                <span className="text-xs font-bold text-zinc-500 tracking-[0.2em] uppercase">Standby</span>
              </div>
            )}
          </div>
        </div>

        {/* Voice engine status bar */}
        {elAvailable === false && (
          <div className="bg-amber-950/20 border-t border-amber-900/30 px-6 py-2">
            <p className="text-[9px] text-amber-400 tracking-wide leading-relaxed">
              <strong>⚠ ElevenLabs AI Voice not configured</strong> — Browser speech synthesis active as fallback.
              Add <code className="font-mono bg-zinc-900 px-1 rounded">ELEVENLABS_API_KEY=sk_…</code> to <code className="font-mono bg-zinc-900 px-1 rounded">.env.local</code>
            </p>
          </div>
        )}
        {usingEL && (
          <div className="bg-emerald-950/15 border-t border-emerald-900/20 px-6 py-1.5 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[8px] text-emerald-400 tracking-[0.3em] uppercase">ElevenLabs Neural Voice Engine Active — Broadcast-Grade AI Voices</span>
          </div>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════════
          BREAKING NEWS TICKER — CNN-style scrolling ticker
          ══════════════════════════════════════════════════════════════ */}
      <div className="studio-ticker">
        <div className="flex items-center">
          {/* BREAKING flash badge */}
          <div className="breaking-banner flex-shrink-0 px-4 py-1.5">
            <span className="text-[9px] font-black text-white tracking-[0.3em] uppercase relative z-10">
              ⚡ BREAKING
            </span>
          </div>
          {/* Scrolling ticker */}
          <div className="flex-1 overflow-hidden px-4 py-1.5">
            <div
              className="flex gap-12 text-[9px] font-mono font-bold tracking-widest text-red-200/80 whitespace-nowrap"
              style={{ animation: 'ticker-scroll 60s linear infinite', width: 'max-content' }}
            >
              {[0, 1].map((k) => (
                <span key={k} suppressHydrationWarning>
                  {tickerItems.join('  ★  ')} &nbsp;
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          BROADCAST CONTROL DESK — War Room Style Anchor Grid
          ══════════════════════════════════════════════════════════════ */}
      <div className="px-4 md:px-6 pt-6 space-y-6">

        {/* Anchor desk — 9-person news team */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Video size={12} className="text-red-400" />
            <span className="text-[9px] tracking-[0.3em] text-zinc-500 uppercase font-bold">News Team — {TEAM.length} Correspondents</span>
            <div className="flex-1 h-px bg-gradient-to-r from-zinc-800/60 to-transparent" />
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
            {TEAM.map((member) => {
              const isActive = activeAnchor === member.id
              const hasSeg   = liveSegments.findIndex(s => s.anchor === member.id)
              return (
                <div
                  key={member.id}
                  title={`Click to jump to ${member.name}'s segment`}
                  onClick={() => { if (hasSeg >= 0) skipTo(hasSeg) }}
                  className={`relative video-feed-frame border rounded overflow-hidden cursor-pointer transition-all duration-300 group ${
                    isActive
                      ? `${member.border} ${member.bg} anchor-card-active shadow-lg shadow-black/40`
                      : 'border-zinc-800/60 bg-zinc-950/80 hover:bg-zinc-900/50 hover:border-zinc-700'
                  }`}
                >
                  {/* Video feed simulation */}
                  <div className="relative p-3 flex flex-col items-center">
                    {/* Camera timecode */}
                    <div className="absolute top-1 left-2 flex items-center gap-1">
                      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />}
                      <span className={`text-[6px] font-mono ${isActive ? 'text-red-400' : 'text-zinc-700'}`}>
                        {isActive ? 'LIVE' : `CAM-${member.initials}`}
                      </span>
                    </div>

                    {/* Avatar — photorealistic AI portrait */}
                    <div className={`w-14 h-14 rounded-full border-2 overflow-hidden bg-zinc-900 mt-2 mb-2 transition-all duration-300 relative ${
                      isActive ? `${member.border} ${member.color} anchor-ring-active` : 'border-zinc-700'
                    }`}>
                      <Image
                        src={member.avatar}
                        alt={member.name}
                        width={56}
                        height={56}
                        className={`w-full h-full object-cover transition-all duration-500 ${
                          isActive ? 'scale-105 brightness-110' : 'brightness-75 grayscale-[30%]'
                        }`}
                      />
                      {/* Speaking glow overlay */}
                      {isActive && playMode === 'playing' && (
                        <div className="absolute inset-0 rounded-full animate-pulse" style={{
                          boxShadow: `0 0 12px 3px var(--anchor-glow, rgba(16,185,129,0.4))`,
                        }} />
                      )}
                      {/* LIVE mic overlay */}
                      {isActive && (
                        <div className="absolute bottom-0 right-0 w-5 h-5 rounded-full bg-red-600 border-2 border-zinc-900 flex items-center justify-center">
                          <Mic size={10} className="text-white animate-pulse" />
                        </div>
                      )}
                    </div>

                    {/* Name + title */}
                    <p className={`text-[10px] font-bold tracking-wide text-center ${isActive ? member.color : 'text-zinc-400'}`}>
                      {(member.name ?? '').replace('Col. ', '').replace('Dr. ', '').replace('Lt. Gen. ', '').replace('Cpl. ', '').split(' ')[0]}
                    </p>
                    <p className="text-[7px] text-zinc-600 tracking-widest uppercase mt-0.5 leading-tight text-center">
                      {member.title}
                    </p>

                    {/* Waveform when speaking */}
                    {isActive && (
                      <div className="flex items-center justify-center gap-0.5 mt-2" style={{ height: 16 }}>
                        {waveH.slice(0, 8).map((h, i) => (
                          <div
                            key={i}
                            className={`w-0.5 rounded-full transition-all duration-100 ${(member.color ?? 'text-zinc-400').replace('text-', 'bg-')}`}
                            style={{ height: playMode === 'playing' ? Math.min(h, 14) : 3 }}
                          />
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Lower third name bar */}
                  {isActive && (
                    <div className={`lower-third border-t ${member.border} ${member.bg} px-2 py-1`}>
                      <div className="flex items-center justify-between">
                        <span className={`text-[7px] font-black tracking-[0.3em] uppercase ${member.color}`}>{member.name}</span>
                        <span className="text-[6px] text-red-400 tracking-widest uppercase">Live</span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════
            MAIN BROADCAST MONITOR — Active Segment Player
            ══════════════════════════════════════════════════════════════ */}
        <div className="segment-monitor rounded overflow-hidden">
          {/* Monitor header — broadcast-style lower third */}
          <div className="segment-monitor-header px-5 py-3 flex items-center gap-4">
            {/* Segment number */}
            <div className={`w-10 h-10 rounded flex items-center justify-center text-lg font-black border-2 ${
              activeAnchor
                ? `${anchor.border} ${anchor.color}`
                : 'border-zinc-700 text-zinc-600'
            }`}>
              {currentIdx + 1}
            </div>

            {/* Segment info */}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className={`text-[8px] tracking-[0.3em] uppercase font-bold ${anchor.color}`}>{anchor.name}</span>
                <span className="text-[7px] text-zinc-600">·</span>
                <span className="text-[8px] text-zinc-500 tracking-widest uppercase">{anchor.title}</span>
              </div>
              <p className="text-sm font-bold text-white tracking-[0.1em] uppercase mt-0.5">{seg.label}</p>
              <div className="studio-accent-bar mt-1 w-32" />
            </div>

            {/* Live waveform + on-air */}
            <div className="flex items-center gap-3">
              {playMode === 'playing' && (
                <>
                  <Bars count={14} colorClass={`${(anchor.color ?? 'text-zinc-400').replace('text-', 'bg-')}/70`} />
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-red-900/30 border border-red-800/50 rounded">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <span className="text-[8px] font-black text-red-400 tracking-[0.2em]">REC</span>
                  </div>
                </>
              )}
              {playMode === 'loading' && (
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-[9px] text-amber-400 tracking-widest uppercase">Loading AI Voice…</span>
                </div>
              )}
            </div>
          </div>

          {/* Video feed simulation + teleprompter text */}
          <div className="grid grid-cols-1 lg:grid-cols-3">
            {/* Left: Anchor camera view */}
            <div className="video-feed-frame relative bg-zinc-950/80 border-r border-zinc-800/30 p-6 flex flex-col items-center justify-center min-h-[280px]">
              {/* Main anchor portrait */}
              <div className={`w-36 h-36 rounded-full border-3 overflow-hidden bg-zinc-900 transition-all duration-500 relative ${
                activeAnchor ? `${anchor.border} ${anchor.color} anchor-ring-active shadow-2xl` : 'border-zinc-700'
              }`}
              style={activeAnchor ? { boxShadow: `0 0 40px 8px rgba(16,185,129,0.15), 0 0 80px 16px rgba(16,185,129,0.05)` } : {}}
              >
                <Image
                  src={anchor.avatar}
                  alt={anchor.name}
                  width={144}
                  height={144}
                  priority
                  className={`w-full h-full object-cover transition-all duration-700 ${
                    playMode === 'playing' ? 'scale-105 brightness-110' : activeAnchor ? 'brightness-90' : 'brightness-50 grayscale-[50%]'
                  }`}
                />
                {/* Speaking radial pulse */}
                {playMode === 'playing' && (
                  <div className="absolute inset-0 rounded-full anchor-speak-pulse" />
                )}
              </div>

              {/* Speaking waveform bars below portrait */}
              {playMode === 'playing' && (
                <div className="flex items-end justify-center gap-[3px] mt-4" style={{ height: 24 }}>
                  {waveH.slice(0, 12).map((h, i) => (
                    <div
                      key={i}
                      className="rounded-full transition-all duration-75"
                      style={{
                        width: 3,
                        height: `${h * 24}px`,
                        backgroundColor: `hsl(var(--anchor-hue, 160) 80% 50% / ${0.5 + h * 0.5})`,
                      }}
                    />
                  ))}
                </div>
              )}

              {/* AI badge */}
              <div className="mt-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900/80 border border-zinc-800/40">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[8px] text-zinc-500 tracking-[0.2em] uppercase font-medium">AI-Generated Anchor</span>
              </div>

              {/* Lower third overlay */}
              {activeAnchor && (
                <div className="lower-third absolute bottom-0 left-0 right-0 z-10">
                  <div className={`${anchor.bg} border-t-2 ${anchor.border} px-4 py-2`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className={`text-xs font-black tracking-[0.15em] uppercase ${anchor.color}`}>{anchor.name}</p>
                        <p className="text-[8px] text-zinc-400 tracking-[0.2em] uppercase">{anchor.title}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[7px] text-zinc-600 font-mono">EPIC FURY NEWS NETWORK</p>
                        <p className="text-[7px] text-red-400/60 font-mono" suppressHydrationWarning>DAY {CONFLICT_DAY}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Topic badge */}
              <div className="absolute top-3 right-3 z-10">
                <span className={`text-[7px] font-bold tracking-[0.3em] uppercase px-2 py-1 rounded border ${
                  anchor.bg} ${anchor.border} ${anchor.color}`}>
                  {seg.topic}
                </span>
              </div>
            </div>

            {/* Right: Teleprompter / script text */}
            <div className="lg:col-span-2 bg-zinc-950/60 relative">
              {/* Teleprompter header */}
              <div className="px-5 py-2 border-b border-zinc-800/30 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Eye size={10} className="text-zinc-600" />
                  <span className="text-[8px] tracking-[0.3em] text-zinc-600 uppercase">Teleprompter</span>
                </div>
                <span className="text-[7px] font-mono text-zinc-700">
                  SEG {currentIdx + 1}/{liveSegments.length} · {seg.script.length} chars
                </span>
              </div>

              {/* Script text */}
              <div className="px-5 py-4 max-h-64 overflow-y-auto">
                <p className={`text-[11px] font-mono leading-[1.8] ${
                  playMode === 'playing' ? 'text-zinc-200' : playMode === 'paused' ? 'text-zinc-400' : 'text-zinc-600'
                }`}>
                  {seg.script}
                </p>
              </div>

              {/* Citations bar */}
              <div className="px-5 py-2 border-t border-zinc-800/30 bg-zinc-950/40">
                <div className="flex items-center gap-2 flex-wrap">
                  <Shield size={8} className="text-emerald-600 flex-shrink-0" />
                  <span className="text-[7px] tracking-[0.3em] text-emerald-600 uppercase flex-shrink-0">Sources:</span>
                  {seg.citations.map((c, ci) => (
                    <span key={ci} className="text-[7px] font-mono text-zinc-600 bg-zinc-900/80 border border-zinc-800/60 px-1.5 py-0.5 rounded">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Playback controls — broadcast console style */}
          <div className="border-t border-red-900/15 bg-zinc-950/80 px-5 py-3 flex flex-wrap items-center gap-2.5">
            {/* Primary action */}
            {playMode === 'idle' ? (
              <button
                onClick={() => playSegment(currentIdx)}
                className="flex items-center gap-2 px-5 min-h-[44px] bg-emerald-900/30 border border-emerald-700/50 rounded-lg text-emerald-300 text-[10px] tracking-[0.2em] uppercase font-bold hover:bg-emerald-900/50 active:scale-95 transition-all hover:shadow-lg hover:shadow-emerald-900/20"
              >
                <Play size={14} /> Play Segment
              </button>
            ) : playMode === 'loading' ? (
              <button disabled className="flex items-center gap-2 px-5 min-h-[44px] bg-amber-900/20 border border-amber-800/40 rounded-lg text-amber-500 text-[10px] tracking-[0.2em] uppercase font-bold opacity-70 cursor-not-allowed">
                <span className="w-3.5 h-3.5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                Loading AI Voice…
              </button>
            ) : (
              <button
                onClick={togglePause}
                className="flex items-center gap-2 px-5 min-h-[44px] bg-amber-900/20 border border-amber-700/50 rounded-lg text-amber-300 text-[10px] tracking-[0.2em] uppercase font-bold hover:bg-amber-900/40 active:scale-95 transition-all"
              >
                {playMode === 'playing' ? <><Pause size={14} /> Pause</> : <><Play size={14} /> Resume</>}
              </button>
            )}

            {/* Full broadcast */}
            {playMode === 'idle' && (
              <button
                onClick={() => { setCurrentIdx(0); playSegment(0) }}
                className="flex items-center gap-2 px-5 min-h-[44px] bg-red-900/25 border border-red-800/40 rounded-lg text-red-300 text-[10px] tracking-[0.2em] uppercase font-bold hover:bg-red-900/40 active:scale-95 transition-all hover:shadow-lg hover:shadow-red-900/20"
              >
                <Radio size={14} /> Full Broadcast
              </button>
            )}

            {/* Stop */}
            {playMode !== 'idle' && (
              <button
                onClick={stopAll}
                className="flex items-center gap-2 px-4 min-h-[44px] border border-zinc-700/40 rounded-lg text-zinc-500 text-[10px] tracking-[0.2em] uppercase font-bold hover:text-zinc-300 hover:border-zinc-600 active:scale-95 transition-all"
              >
                <Square size={14} /> Stop
              </button>
            )}

            {/* Skip */}
            <button
              onClick={() => skipTo((currentIdx + 1) % liveSegments.length)}
              className="flex items-center gap-2 px-4 min-h-[44px] border border-zinc-700/40 rounded-lg text-zinc-500 text-[10px] tracking-[0.2em] uppercase font-bold hover:text-zinc-300 hover:border-zinc-600 active:scale-95 transition-all"
            >
              <SkipForward size={14} /> Next
            </button>

            {/* Segment selector bar */}
            <div className="ml-auto flex items-center gap-1.5 flex-wrap">
              {liveSegments.map((s, i) => {
                const a = TEAM.find(t => t.id === s.anchor)!
                return (
                  <button
                    key={s.id}
                    onClick={() => skipTo(i)}
                    title={s.label}
                    className={`w-9 h-9 rounded-lg text-[10px] font-bold active:scale-95 transition-all ${
                      i === currentIdx
                        ? `${a.bg} ${a.border} border-2 ${a.color} shadow-lg`
                        : 'border border-zinc-800 text-zinc-600 hover:border-zinc-600 hover:text-zinc-400'
                    }`}
                  >
                    {i + 1}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════
            THEATER SITUATION DISPLAY — Multi-camera broadcast grid
            ══════════════════════════════════════════════════════════════ */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Crosshair size={12} className="text-red-400" />
            <span className="text-[9px] tracking-[0.3em] text-red-400/80 uppercase font-bold">
              Theater Situation Display — Live War Graphics
            </span>
            <div className="flex-1 h-px bg-gradient-to-r from-red-900/40 to-transparent" />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {/* ── Camera 1: Air Domain Status ── */}
            <div className="video-feed-frame border border-zinc-800/60 rounded overflow-hidden bg-zinc-950/80">
              <div className="px-3 py-1.5 border-b border-zinc-800/30 bg-zinc-900/40 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[7px] tracking-[0.3em] text-emerald-400 uppercase font-bold">CAM-1 · AIR</span>
                </div>
                <span className="text-[6px] font-mono text-zinc-700 timecode-blink">●REC</span>
              </div>
              <div className="p-4 space-y-3">
                <div className="text-center">
                  <p className="text-3xl font-black text-sky-400" style={{ textShadow: '0 0 20px rgba(56,189,248,0.3)' }}>{WAR_STATS.sortiesLabel}</p>
                  <p className="text-[7px] tracking-[0.3em] text-zinc-500 uppercase mt-1">Combat Sorties</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-amber-400">94%</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">AD Degraded</p>
                  </div>
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-emerald-400">AIR DOM</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">Status</p>
                  </div>
                </div>
                <div className="h-px bg-gradient-to-r from-transparent via-sky-900/40 to-transparent" />
                <p className="text-[7px] text-zinc-600 font-mono text-center">IRGCAF: 0 sorties / {WAR_STATS.daysSinceIRGCAFSortie ?? 19}d · F-35A @ {WAR_STATS.tbmdInterceptPct}%</p>
              </div>
            </div>

            {/* ── Camera 2: Hormuz Maritime ── */}
            <div className="video-feed-frame border border-zinc-800/60 rounded overflow-hidden bg-zinc-950/80">
              <div className="px-3 py-1.5 border-b border-zinc-800/30 bg-zinc-900/40 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
                  <span className="text-[7px] tracking-[0.3em] text-cyan-400 uppercase font-bold">CAM-2 · HORMUZ</span>
                </div>
                <span className="text-[6px] font-mono text-zinc-700 timecode-blink">●REC</span>
              </div>
              <div className="p-4 space-y-3">
                <div className="text-center">
                  <p className="text-3xl font-black text-cyan-400" style={{ textShadow: '0 0 20px rgba(34,211,238,0.3)' }}>{WAR_STATS.zbAlphaPct}%</p>
                  <p className="text-[7px] tracking-[0.3em] text-zinc-500 uppercase mt-1">ZB-Alpha Cleared</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-emerald-400">7</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">VLCC Transits</p>
                  </div>
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-amber-400">30%</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">IRGCN Threat</p>
                  </div>
                </div>
                <div className="h-px bg-gradient-to-r from-transparent via-cyan-900/40 to-transparent" />
                <p className="text-[7px] text-zinc-600 font-mono text-center">GOLF-7: Bandar Abbas · {CONFLICT_DAY - 22} days inactive</p>
              </div>
            </div>

            {/* ── Camera 3: Nuclear Status ── */}
            <div className="video-feed-frame border border-zinc-800/60 rounded overflow-hidden bg-zinc-950/80">
              <div className="px-3 py-1.5 border-b border-zinc-800/30 bg-zinc-900/40 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
                  <span className="text-[7px] tracking-[0.3em] text-violet-400 uppercase font-bold">CAM-3 · NUCLEAR</span>
                </div>
                <span className="text-[6px] font-mono text-zinc-700 timecode-blink">●REC</span>
              </div>
              <div className="p-4 space-y-3">
                <div className="text-center">
                  <p className="text-3xl font-black text-violet-400" style={{ textShadow: '0 0 20px rgba(167,139,250,0.3)' }}>94%</p>
                  <p className="text-[7px] tracking-[0.3em] text-zinc-500 uppercase mt-1">Nuclear Degraded</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-rose-400">18mo</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">Reconst. Time</p>
                  </div>
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-emerald-400">0</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">Rad Events</p>
                  </div>
                </div>
                <div className="h-px bg-gradient-to-r from-transparent via-violet-900/40 to-transparent" />
                <p className="text-[7px] text-zinc-600 font-mono text-center">Natanz 70% collapsed · Fordow MK</p>
              </div>
            </div>

            {/* ── Camera 4: Diplomatic / Ceasefire ── */}
            <div className="video-feed-frame border border-zinc-800/60 rounded overflow-hidden bg-zinc-950/80">
              <div className="px-3 py-1.5 border-b border-zinc-800/30 bg-zinc-900/40 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  <span className="text-[7px] tracking-[0.3em] text-amber-400 uppercase font-bold">CAM-4 · DIPLO</span>
                </div>
                <span className="text-[6px] font-mono text-zinc-700 timecode-blink">●REC</span>
              </div>
              <div className="p-4 space-y-3">
                <div className="text-center">
                  <p className="text-3xl font-black text-amber-400" style={{ textShadow: '0 0 20px rgba(251,191,36,0.3)' }}>{WAR_STATS.compassCeasefire}%</p>
                  <p className="text-[7px] tracking-[0.3em] text-zinc-500 uppercase mt-1">Ceasefire Prob.</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-emerald-400">${WAR_STATS.brentUsd}</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">Brent/bbl</p>
                  </div>
                  <div className="border border-zinc-800/40 rounded p-2 text-center bg-zinc-900/30">
                    <p className="text-sm font-bold text-sky-400">2731</p>
                    <p className="text-[6px] text-zinc-600 tracking-widest uppercase">UNSCR</p>
                  </div>
                </div>
                <div className="h-px bg-gradient-to-r from-transparent via-amber-900/40 to-transparent" />
                <p className="text-[7px] text-zinc-600 font-mono text-center">Abu Dhabi · Oman+UAE co-mediators</p>
              </div>
            </div>
          </div>

          {/* ── Threat Level Bars — animated war graphic ── */}
          <div className="mt-4 border border-zinc-800/40 rounded overflow-hidden bg-zinc-950/60">
            <div className="px-4 py-2 border-b border-zinc-800/30 bg-zinc-900/20 flex items-center justify-between">
              <span className="text-[8px] tracking-[0.3em] text-red-400/70 uppercase font-bold">ORACLE-9 Domain Threat Assessment</span>
              <span className="text-[7px] font-mono text-zinc-700" suppressHydrationWarning>Day {CONFLICT_DAY} · Realtime</span>
            </div>
            <div className="p-4 space-y-2.5">
              {[
                { domain: 'AIR', pct: 12, color: 'bg-sky-500',    label: 'Air Defense Threat' },
                { domain: 'MARITIME', pct: 30, color: 'bg-cyan-500',   label: 'Naval / IRGCN Threat' },
                { domain: 'MISSILE', pct: 8,  color: 'bg-rose-500',   label: 'Ballistic Missile Threat' },
                { domain: 'NUCLEAR', pct: 6,  color: 'bg-violet-500', label: 'Nuclear Breakout Risk' },
                { domain: 'CYBER', pct: 45, color: 'bg-amber-500',  label: 'Cyber / IO Operations' },
                { domain: 'ECONOMIC', pct: 38, color: 'bg-emerald-500', label: 'Economic Cascade Risk' },
              ].map(t => (
                <div key={t.domain} className="flex items-center gap-3">
                  <span className="text-[7px] tracking-[0.3em] text-zinc-500 uppercase font-bold w-16 text-right flex-shrink-0">{t.domain}</span>
                  <div className="flex-1 h-3 bg-zinc-900 rounded-sm overflow-hidden relative">
                    <div
                      className={`h-full ${t.color} rounded-sm transition-all duration-1000`}
                      style={{ width: `${t.pct}%`, animation: 'bar-slide 1.5s ease forwards' }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent to-black/30" />
                  </div>
                  <span className="text-[8px] font-mono text-zinc-500 w-8 text-right">{t.pct}%</span>
                  <span className="text-[7px] text-zinc-600 w-32 hidden sm:block">{t.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════
            SEGMENT RUNDOWN — Full broadcast schedule with citations
            ══════════════════════════════════════════════════════════════ */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Mic2 size={12} className="text-zinc-500" />
            <span className="text-[9px] tracking-[0.3em] text-zinc-500 uppercase font-bold">
              Broadcast Rundown — {liveSegments.length} Segments · Full Citations
            </span>
            <div className="flex-1 h-px bg-gradient-to-r from-zinc-800/60 to-transparent" />
            <span className="text-[8px] text-zinc-600 tracking-widest uppercase">Click any segment to jump</span>
          </div>

          <div className="space-y-2">
            {liveSegments.map((s, i) => {
              const a        = TEAM.find(t => t.id === s.anchor)!
              const isActive = i === currentIdx
              return (
                <div
                  key={s.id}
                  onClick={() => skipTo(i)}
                  className={`border rounded overflow-hidden cursor-pointer transition-all duration-200 group ${
                    isActive ? `${a.border} ${a.bg} shadow-lg shadow-black/30` : 'border-zinc-800/60 hover:border-zinc-700/80 bg-zinc-950/40'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-3 px-4 py-3">
                    {/* Segment number */}
                    <span className={`text-sm font-black w-6 text-center flex-shrink-0 ${isActive ? a.color : 'text-zinc-700'}`}>
                      {i + 1}
                    </span>
                    {/* Anchor avatar */}
                    <div className={`w-8 h-8 rounded-full overflow-hidden border-2 flex-shrink-0 bg-zinc-900 relative ${
                      isActive ? `${a.border} ${a.color}` : 'border-zinc-700'
                    }`}>
                      <Image
                        src={a.avatar}
                        alt={a.name}
                        width={32}
                        height={32}
                        className={`w-full h-full object-cover ${isActive ? 'brightness-110' : 'brightness-60 grayscale-[40%]'}`}
                      />
                      {isActive && playMode === 'playing' && (
                        <div className="absolute bottom-0 right-0 w-3.5 h-3.5 rounded-full bg-red-600 border border-zinc-900 flex items-center justify-center">
                          <Mic size={7} className="text-white" />
                        </div>
                      )}
                    </div>
                    {/* Label */}
                    <div className="flex-1 min-w-0">
                      <span className={`text-[10px] font-bold tracking-[0.15em] uppercase block ${isActive ? a.color : 'text-zinc-500'}`}>
                        {s.label}
                      </span>
                      <span className="text-[8px] text-zinc-600">{a.name} · {a.title}</span>
                    </div>
                    {/* Topic badge */}
                    <span className={`text-[7px] font-bold tracking-[0.2em] uppercase px-2 py-1 rounded border ${
                      isActive ? `${a.bg} ${a.border} ${a.color}` : 'bg-zinc-900/60 border-zinc-800/60 text-zinc-600'
                    }`}>
                      {s.topic}
                    </span>
                    {/* Citations */}
                    <div className="flex flex-wrap gap-1 justify-end max-w-md">
                      {s.citations.slice(0, 3).map((c, ci) => (
                        <span
                          key={ci}
                          className="text-[7px] font-mono text-zinc-600 bg-zinc-900/80 border border-zinc-800/60 px-1.5 py-0.5 rounded"
                        >
                          {c}
                        </span>
                      ))}
                      {s.citations.length > 3 && (
                        <span className="text-[7px] text-zinc-700">+{s.citations.length - 3}</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════
            WAR STATS CRAWL — TV-style bottom-third data ticker
            ══════════════════════════════════════════════════════════════ */}
        <div className="border border-red-900/20 rounded overflow-hidden">
          {/* Label bar */}
          <div className="breaking-banner px-4 py-1.5">
            <span className="text-[8px] font-black text-white tracking-[0.4em] uppercase relative z-10" suppressHydrationWarning>
              ⚡ Operation Epic Fury — Day {CONFLICT_DAY} Battle Summary
            </span>
          </div>
          {/* Stat blocks */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 bg-zinc-950/80">
            {[
              { label: 'COMBAT SORTIES',  value: WAR_STATS.sortiesLabel,                    color: 'text-sky-400',     sub: `D${CONFLICT_DAY} coalition total` },
              { label: 'THAAD INTERCEPTS', value: `~${WAR_STATS.tbmdInterceptPct}%`,          color: 'text-emerald-400', sub: '110+ of 128 BMs' },
              { label: 'IRAN NUCLEAR',     value: `${WAR_STATS.nuclearDegradedPct}%`,         color: 'text-violet-400',  sub: 'Degraded' },
              { label: 'HORMUZ MCM',       value: `${WAR_STATS.zbAlphaPct}%`,                 color: 'text-cyan-400',    sub: 'Corridor Cleared' },
              { label: 'CEASEFIRE PROB',   value: `${WAR_STATS.compassCeasefire}%`,           color: 'text-amber-400',   sub: '72-hr COMPASS' },
              { label: 'BRENT CRUDE',      value: `$${WAR_STATS.brentUsd}/bbl`,              color: 'text-emerald-400', sub: 'COMPASS model' },
            ].map((s, i) => (
              <div key={i} className="border-r border-zinc-800/30 last:border-r-0 px-3 py-3 text-center">
                <p className="text-[6px] tracking-[0.3em] text-zinc-600 uppercase mb-1">{s.label}</p>
                <p className={`text-lg font-black ${s.color}`} style={{ textShadow: '0 0 12px currentColor' }}>{s.value}</p>
                <p className="text-[7px] text-zinc-600 mt-0.5">{s.sub}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════
            LIVE INTEL FEEDS — HERALD-3 + LiveNewsBoard
            ══════════════════════════════════════════════════════════════ */}
        <div className="space-y-6 pt-2">
          {/* Section divider */}
          <div className="studio-accent-bar w-full" />

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* HERALD-3 IO Feed */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={12} className="text-orange-400" />
                <span className="text-[9px] tracking-[0.3em] text-orange-400/80 uppercase font-bold">
                  HERALD-3 · Information Operations Threat Feed
                </span>
              </div>
              <HeraldFeed limit={12} />
            </div>

            {/* Live Intel News Board */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Radio size={12} className="text-emerald-400 animate-pulse" />
                <span className="text-[9px] tracking-[0.3em] text-emerald-400/80 uppercase font-bold">
                  Live Intel Feed — AI Analyzed · Fully Cited
                </span>
              </div>
              <p className="text-[7px] font-mono text-zinc-600 leading-relaxed mb-2">
                Every headline scored by HERALD-3 for IO risk, deep-analyzed by NEXUS multi-agent pipeline —
                cross-referencing Intel DB, ORACLE-9 threat models, generating fully cited truth verdicts.
              </p>
              <LiveNewsBoard limit={40} warFilter={true} />
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════
            SETUP CARD — ElevenLabs (only shown if not configured)
            ══════════════════════════════════════════════════════════════ */}
        {elAvailable === false && (
          <div className="border border-amber-900/40 rounded bg-amber-950/10 p-5 space-y-2">
            <p className="text-[10px] text-amber-400 font-bold tracking-[0.2em] uppercase">
              ElevenLabs Setup — Real AI Voices
            </p>
            <p className="text-[10px] text-zinc-400 leading-relaxed font-mono">
              1. Sign up at <span className="text-emerald-400">elevenlabs.io</span> (free tier: 10,000 chars/month){'\n'}
              2. Copy your API key from profile settings{'\n'}
              3. Add to <span className="text-emerald-400 bg-zinc-900 px-1 rounded">.env.local</span>:{' '}
              <span className="text-white bg-zinc-900 px-1 rounded">ELEVENLABS_API_KEY=sk_your_key_here</span>{'\n'}
              4. All 9 voices activate with broadcast-grade AI voices via ElevenLabs neural models.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
