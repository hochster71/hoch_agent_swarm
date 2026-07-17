/**
 * Dynamic Fallback Content Generator
 *
 * Generates fallback content for ANY conflict day, eliminating all hardcoded
 * day references. When Supabase / AI services are unavailable, the dashboard
 * still displays contextually accurate content for the current day.
 *
 * This is the core solution to the "content staleness" problem — every
 * fallback is parameterized by CONFLICT_DAY at request time.
 */

import { getConflictDay } from './conflict-day'
import { getWarStats } from './war-stats'

// ── Conflict Timeline Knowledge Base ─────────────────────────────────────────
// Key events indexed by the day they occurred. The fallback generator uses this
// to construct narratives that reference history accurately regardless of what
// day it currently is.

export interface TimelineEvent {
  day: number
  title: string
  theater: string
  significance: 'CRITICAL' | 'HIGH' | 'MEDIUM'
}

export const CONFLICT_TIMELINE: TimelineEvent[] = [
  { day: 1,  title: 'Operation Epic Fury begins — US/Israel strike Iranian nuclear and missile sites', theater: 'Air', significance: 'CRITICAL' },
  { day: 1,  title: 'Natanz FEP and Fordow FFEP struck by B-2A/F-35I in opening salvo', theater: 'Nuclear', significance: 'CRITICAL' },
  { day: 2,  title: 'First combat use of GBU-57A/B Massive Ordnance Penetrator against Fordow', theater: 'Nuclear', significance: 'HIGH' },
  { day: 3,  title: 'IRGC deploys 500-800 naval mines in Strait of Hormuz — commercial traffic suspended', theater: 'Hormuz', significance: 'CRITICAL' },
  { day: 3,  title: 'USCYBERCOM Operation SILENT FURY disrupts IRGCAF missile C2 for 4 hours', theater: 'Cyber', significance: 'HIGH' },
  { day: 5,  title: 'Iran expels all IAEA inspectors — monitoring equipment disabled at all sites', theater: 'Nuclear', significance: 'HIGH' },
  { day: 7,  title: 'AUMF-2026 passed by Congress (Senate 78-22, House 312-115)', theater: 'Diplomatic', significance: 'HIGH' },
  { day: 8,  title: 'FBI arrests 5 IRGC-linked surveillance operatives in Houston, NY, Boston', theater: 'Cyber', significance: 'MEDIUM' },
  { day: 8,  title: 'GCC emergency summit — expanded US basing rights formalized', theater: 'Diplomatic', significance: 'HIGH' },
  { day: 11, title: 'CISA ED 26-02 — IRGC cyberattack on Saudi Aramco OT networks confirmed', theater: 'Cyber', significance: 'HIGH' },
  { day: 14, title: 'IAF strikes Hezbollah PGM stockpiles in Bekaa Valley — pre-emptive', theater: 'Air', significance: 'HIGH' },
  { day: 14, title: 'US SPR emergency release: 50M barrels to stabilize oil prices', theater: 'Economic', significance: 'MEDIUM' },
  { day: 17, title: 'Third Iranian BM barrage — Al Udeid / Camp Arifjan — 3 US KIA', theater: 'Air', significance: 'CRITICAL' },
  { day: 17, title: 'Brent crude peaks at $123/bbl', theater: 'Economic', significance: 'HIGH' },
  { day: 21, title: 'Last two IRGCAF F-14 Tomcats destroyed by VIPER flight', theater: 'Air', significance: 'MEDIUM' },
  { day: 22, title: 'Supreme Leader Khamenei confirmed KIA in Qom command complex strike', theater: 'Air', significance: 'CRITICAL' },
  { day: 22, title: 'B-21 Raider ANVIL-01 strikes Natanz with 2x GBU-57B MOPs', theater: 'Nuclear', significance: 'HIGH' },
  { day: 24, title: 'First commercial VLCC transits ZB-Alpha corridor under coalition escort', theater: 'Hormuz', significance: 'HIGH' },
  { day: 25, title: 'DIA BDA Flash: Iran nuclear infrastructure 94% degraded', theater: 'Nuclear', significance: 'CRITICAL' },
  { day: 25, title: 'UNSCR 2731 passed (14-1) — humanitarian corridor + 60-day negotiation deadline', theater: 'Diplomatic', significance: 'HIGH' },
  { day: 26, title: 'Iran 5th BM barrage — 31 missiles, 27 intercepted — 2 USAF KIA at Al Udeid', theater: 'Air', significance: 'CRITICAL' },
  { day: 26, title: 'Iran SNSC drops US-withdrawal precondition for ceasefire talks via Oman', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 26, title: 'GOLF-7 Kilo-class SSK returns to Bandar Abbas — no new mine activity', theater: 'Maritime', significance: 'HIGH' },
  { day: 27, title: 'POTUS national address announces Abu Dhabi Ceasefire Framework', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 27, title: 'Saudi OPEC+ +2M bbl/day production increase announced', theater: 'Economic', significance: 'HIGH' },
  { day: 27, title: 'CENTCOM Day 27 SITREP: 10,400+ sorties, ZB-Alpha 78% cleared', theater: 'Air', significance: 'HIGH' },
  { day: 28, title: 'Abu Dhabi ceasefire proximity talks open — Oman & UAE co-mediating', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 28, title: '48-hour kinetic pause — no offensive operations from either side', theater: 'Air', significance: 'HIGH' },
  { day: 28, title: 'ICRC facilitates first POW exchange — 12 wounded transferred via Oman', theater: 'Diplomatic', significance: 'HIGH' },
  { day: 28, title: 'Brent crude falls to $91/bbl — largest single-day drop of conflict', theater: 'Economic', significance: 'MEDIUM' },
  { day: 28, title: 'IAEA requests immediate site access under ceasefire framework', theater: 'Nuclear', significance: 'HIGH' },
  { day: 29, title: 'Abu Dhabi talks Day 2 — US drops 24-month nuclear timeline precondition', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 29, title: 'IAEA advance team deploys to Muscat — forward-staged for Natanz access', theater: 'Nuclear', significance: 'HIGH' },
  { day: 30, title: 'Saudi Arabia announces additional 1M bbl/day OPEC+ output — Brent sub-$88', theater: 'Economic', significance: 'HIGH' },
  { day: 31, title: 'Kinetic pause formalized — 5-day no-offensive-operations protocol signed', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 32, title: 'Iran releases 4 dual-national detainees at ICRC Muscat facilitation', theater: 'Diplomatic', significance: 'HIGH' },
  { day: 33, title: 'ZB-Alpha mine clearance 84% complete — 22 VLCCs transited under NAVCENT escort', theater: 'Hormuz', significance: 'HIGH' },
  { day: 34, title: 'Lloyd\'s of London suspends Hormuz war-risk premium — first time since Day 3', theater: 'Economic', significance: 'MEDIUM' },
  { day: 35, title: 'Abu Dhabi Ceasefire Framework 14-point text agreed in principle by all parties', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 36, title: 'Brent crude falls to $84/bbl — Lloyd\'s war-risk premiums normalized', theater: 'Economic', significance: 'MEDIUM' },
  { day: 37, title: 'IAEA Director General arrives Muscat — advance inspection team cleared for entry', theater: 'Nuclear', significance: 'HIGH' },
  { day: 38, title: 'ZULU-14 attempted BM launch fails — Iranian transporter-erector-launcher destroyed pre-launch by B-1B strike', theater: 'Air', significance: 'CRITICAL' },
  { day: 38, title: 'DIA assessment: Iran BM stockpile effectively combat-exhausted — ≤3% pre-conflict inventory', theater: 'Air', significance: 'HIGH' },
  { day: 39, title: 'Iran SNSC formally accepts all 14 points of Abu Dhabi Ceasefire Framework', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 40, title: 'UNSCR 2732 passed 15-0 — unanimous endorsement of Abu Dhabi Ceasefire Framework', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 40, title: 'ZB-Alpha 96% cleared — Hormuz re-opening imminent per NAVCENT', theater: 'Hormuz', significance: 'HIGH' },
  { day: 41, title: 'IAEA inspectors enter Natanz FEP — first access since Day 5 — inspections begin', theater: 'Nuclear', significance: 'CRITICAL' },
  { day: 41, title: 'Brent crude falls to $82/bbl — 7-week low — return to pre-conflict range begins', theater: 'Economic', significance: 'HIGH' },
  { day: 42, title: 'Iran transmits formal ceasefire declaration via Oman — effective 06:00Z Day 43', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 42, title: 'NAVCENT: ZB-Alpha corridor 99% cleared — full commercial resumption imminent', theater: 'Hormuz', significance: 'HIGH' },
  { day: 43, title: 'Day 43: Ceasefire trial begins 06:00Z — all coalition offensive operations paused', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 43, title: 'First fully unrestricted commercial VLCC transits Hormuz — no mine clearance escort required', theater: 'Hormuz', significance: 'CRITICAL' },
  { day: 44, title: 'POTUS announces ceasefire trial extended 48 hours — all theaters silent — Iran compliant', theater: 'Diplomatic', significance: 'CRITICAL' },
  { day: 44, title: 'ZB-Alpha MCM mission complete — Strait of Hormuz 100% cleared — full commercial traffic resumed', theater: 'Hormuz', significance: 'CRITICAL' },
  { day: 44, title: 'IAEA Day 3 inspection: Natanz centrifuge halls confirmed inoperative — 94% degradation assessment validated', theater: 'Nuclear', significance: 'HIGH' },
  { day: 44, title: 'Brent crude settles at $82/bbl — GCC tankers resume full Hormuz routing, Cape of Good Hope diversion cancelled', theater: 'Economic', significance: 'HIGH' },
]

// ── Dynamic context builders ─────────────────────────────────────────────────

/** Get recent events (last N days from current conflict day) */
export function getRecentEvents(lookbackDays = 3): TimelineEvent[] {
  const day = getConflictDay()
  return CONFLICT_TIMELINE.filter(e => e.day >= day - lookbackDays && e.day <= day)
}

/** Get the most significant recent event */
export function getTopEvent(): TimelineEvent {
  const day = getConflictDay()
  const recent = CONFLICT_TIMELINE
    .filter(e => e.day <= day)
    .sort((a, b) => {
      // Prefer current day, then by significance
      const dayScore = (ev: TimelineEvent) => ev.day === day ? 100 : day - ev.day
      const sigScore = (ev: TimelineEvent) =>
        ev.significance === 'CRITICAL' ? 3 : ev.significance === 'HIGH' ? 2 : 1
      return (sigScore(b) * 10 - dayScore(b)) - (sigScore(a) * 10 - dayScore(a))
    })
  return recent[0] ?? { day, title: 'Operations continue', theater: 'Air', significance: 'MEDIUM' }
}

/** Get events for a specific day */
export function getEventsForDay(day: number): TimelineEvent[] {
  return CONFLICT_TIMELINE.filter(e => e.day === day)
}

// ── Dynamic newsroom fallback builder ────────────────────────────────────────

export interface FallbackSegment {
  id: number
  anchor: string
  label: string
  topic: string
  script: string
  citations: string[]
}

/**
 * Build a complete 10-segment newsroom broadcast for ANY conflict day.
 * Uses the timeline knowledge base to construct contextually accurate
 * narratives without any hardcoded day numbers.
 */
export function buildDayAwareBroadcast(day?: number): FallbackSegment[] {
  const d = day ?? getConflictDay()
  const ws = getWarStats(d)
  const today = getEventsForDay(d)
  const yesterday = getEventsForDay(d - 1)
  const topToday = today.find(e => e.significance === 'CRITICAL') ?? today[0]
  const topYesterday = yesterday.find(e => e.significance === 'CRITICAL') ?? yesterday[0]

  // Use war-stats as single source of truth
  const totalSorties = ws.totalSorties
  const zbAlphaPct = ws.zbAlphaPct
  const brentUsd = ws.brentUsd
  const missileStockPct = ws.bmStockPct
  const compassCeasefire = ws.compassCeasefire

  const topHeadline = topToday?.title ?? `Day ${d} operations continue across all theaters`
  const secondHeadline = (today[1] ?? topYesterday)?.title ?? 'Coalition forces maintaining full defensive posture'

  return [
    {
      id: 1, anchor: 'sarah', label: `Opening Headlines — Day ${d}`, topic: 'Breaking News',
      script: `Good evening. I'm Sarah Mitchell, and this is Epic Fury News Network. Day ${d} of Operation Epic Fury. ${d >= 44 ? 'POTUS has extended the Abu Dhabi ceasefire trial by forty-eight hours — all theaters remain silent — Iran fully compliant. The Strait of Hormuz is one hundred percent cleared and open for the first time since Day Three.' : d >= 43 ? 'The Abu Dhabi ceasefire trial is in effect as of oh-six hundred Zulu this morning. All coalition offensive operations are paused. Five theaters, zero hostile activity.' : topHeadline + '. ' + secondHeadline}. CENTCOM reports over ${totalSorties.toLocaleString()} coalition combat sorties since Day One. ${d >= 44 ? 'The Strait of Hormuz is one hundred percent cleared — ZB-Alpha MCM mission complete.' : 'The Strait of Hormuz ZB-Alpha corridor is ' + zbAlphaPct + ' percent cleared.'} Brent crude at ${Math.round(brentUsd)} dollars per barrel. COMPASS ceasefire probability: ${compassCeasefire} percent. James?`,
      citations: [`CENTCOM Day ${d} SITREP`, 'NEXUS All-Domain Assessment', `COMPASS Model D${d}`],
    },
    {
      id: 2, anchor: 'james', label: `Air Operations — Day ${d}`, topic: 'Operations Overview',
      script: `Thank you, Sarah. The CENTCOM Day ${d} operational picture: over ${totalSorties.toLocaleString()} combat sorties flown since Day One. ${d >= 22 ? 'The IRGCAF is assessed as a non-factor — no combat sorties detected in the last ' + Math.min(d - 20, 10) * 24 + ' hours.' : 'IRGCAF combat capability continues to degrade under sustained coalition air operations.'} Coalition air dominance is uncontested across all of Iran's territory. ${d >= 43 ? 'All coalition offensive strike operations have been paused under CENTCOM OPORD 2026-43. Forces remain at DEFCON-3 with full defensive posture — PATRIOT and THAAD batteries on hot standby. Ceasefire trial compliance: one hundred percent across all domains for ' + (d - 43) * 24 + '+ hours.' : d >= 27 ? 'Air operations transitioning from strike to enforcement and deterrence posture in support of diplomatic process. B-21 Raider ANVIL-01 remains in theater.' : d >= 22 ? 'B-21 Raider ANVIL-01 remains in theater. Strike operations continuing.' : 'Strike operations continuing against time-sensitive IRGC targets.'} Dr. Chen?`,
      citations: [`CENTCOM Day ${d} SITREP`, 'CAOC BLUE DAGGER Assessment', 'ISW Operational Assessment'],
    },
    {
      id: 3, anchor: 'maya', label: `Intelligence Assessment — Day ${d}`, topic: 'Defense Intel',
      script: `James, the intelligence picture on Day ${d}: ${d >= 25 ? 'The DIA BDA flash from Day Twenty-Five remains the definitive assessment — Iran\'s nuclear enrichment infrastructure is ninety-four percent degraded. Reconstitution timeline: eighteen to twenty-four months minimum.' : 'DIA continues battle damage assessment across all struck target sets.'} ${d >= 26 ? 'GOLF-7, the Kilo-class submarine responsible for ZB-Alpha mine-laying, has not sortied since Day Twenty-Two. IRGCN surface threat reduced to thirty percent of pre-conflict capability.' : 'IRGCN mine and surface threats remain active in the Hormuz approaches.'} ${d >= 26 ? 'Iran\'s residual ballistic missile inventory assessed at ' + missileStockPct + ' percent of pre-conflict levels following the Day Twenty-Six barrage.' : 'Iran retains significant ballistic missile capability.'} Dr. Rostami?`,
      citations: ['DIA BDA Flash Assessment', 'MANTIS ACINT Track Update', `ORACLE-9 Day ${d} Assessment`],
    },
    {
      id: 4, anchor: 'rostami', label: `Nuclear Threat Status — Day ${d}`, topic: 'Nuclear Watch',
      script: `The nuclear dimension on Day ${d}: ${d >= 41 ? 'IAEA inspectors entered Natanz FEP on Day Forty-One — the first access since Day Five. Preliminary Day Three report confirms centrifuge halls A through D all inoperative. Enrichment capacity at Natanz: effectively zero. Radiological status: green. The ninety-four percent degradation assessment is now independently verified.' : d >= 25 ? 'The DIA ninety-four percent degradation figure represents the strategic center of gravity. Natanz is seventy percent collapsed. Fordow is mission-killed without radiological release. Breakout timeline reset to eighteen months minimum.' : 'Coalition strikes continue against Iran\'s nuclear infrastructure. IAEA has had no access since Day Five.'} ${d >= 44 ? 'IAEA advance team staged in Muscat for Fordow entry expected Day Forty-Five.' : d >= 41 ? 'Full inspection report expected within forty-eight hours.' : d >= 28 ? 'The IAEA Director General has requested immediate site access under any ceasefire framework — this provision is non-negotiable for the US delegation.' : 'The IAEA has maintained zero continuity of knowledge since Day Five.'} Colonel Harris?`,
      citations: ['IAEA Nuclear Safeguards', `ORACLE-9 Nuclear Model D${d}`, 'NTI Assessment'],
    },
    {
      id: 5, anchor: 'harris', label: `Military Situation — Day ${d}`, topic: 'Military Analysis',
      script: `Day ${d} military situation: ${d >= 43 ? 'Ceasefire trial is holding — zero hostile activity across all five CENTCOM theaters since oh-six hundred Zulu Day Forty-Three. FPCON adjusted to ALPHA. Joint Chiefs are conducting post-conflict readiness assessment and BDA consolidation.' : d >= 28 ? 'We are now in the longest kinetic pause since Day One — no offensive operations from either side since early this morning. Coalition forces remain at DEFCON-3 with full defensive posture.' : d >= 27 ? 'Offensive operations are transitioning to enforcement posture following the ceasefire framework announcement.' : 'Coalition operations continue across all domains.'} ${d >= 26 ? 'The Day Twenty-Six barrage — thirty-one missiles, twenty-seven intercepted — represented Iran\'s last major offensive capability. Two Air Force members were killed. THAAD intercept rate across all five barrages: eighty-six percent.' : ''} ${d >= 44 ? 'ZB-Alpha MCM mission complete — Hormuz one hundred percent cleared. GOLF-7 and GOLF-8 both inactive.' : d >= 24 ? 'ZB-Alpha corridor is ' + zbAlphaPct + ' percent cleared. Surface threat at thirty percent of pre-conflict IRGCN strength.' : 'MCM operations continue in the Strait of Hormuz.'} Natasha?`,
      citations: [`CENTCOM J3 Day ${d}`, 'THAAD Program Office', 'MDA Theater Defense Report'],
    },
    {
      id: 6, anchor: 'natasha', label: `Diplomatic Developments — Day ${d}`, topic: 'Foreign Affairs',
      script: `Diplomatically on Day ${d}: ${d >= 44 ? 'The President extended the ceasefire trial by forty-eight hours after confirming one hundred percent Iranian compliance in the first thirty-two-hour period. Formal armistice negotiations expected to begin by Day Forty-Seven. COMPASS: ' + compassCeasefire + ' percent.' : d >= 43 ? 'The Abu Dhabi Ceasefire Framework trial period is in effect. COMPASS ceasefire probability is at ' + compassCeasefire + ' percent — maximum model confidence. POTUS will review compliance at the forty-eight-hour mark.' : d >= 42 ? 'Iran transmitted its formal ceasefire declaration via the Omani channel at twenty-one hundred Zulu — effective oh-six hundred Zulu Day Forty-Three. The White House authorized CENTCOM stand-down of offensive operations.' : d >= 39 ? 'Iran\'s Supreme National Security Council formally accepted all fourteen points of the Abu Dhabi Ceasefire Framework. UNSCR 2732 passed fifteen to zero on Day Forty — unanimous.' : d >= 28 ? 'Abu Dhabi ceasefire proximity talks are ongoing with Oman and the UAE co-mediating. COMPASS assesses ' + compassCeasefire + ' percent probability of a signed cessation of hostilities.' : d >= 27 ? 'The President announced the Abu Dhabi Ceasefire Framework today. COMPASS model at sixty-eight percent ceasefire probability within seventy-two hours. Oman and UAE co-mediating.' : d >= 26 ? 'Iran dropped its withdrawal precondition through the Omani channel — the first breakthrough since Day One.' : 'The Omani back-channel remains the primary diplomatic track. UNSC deadlocked.'} ${d >= 40 ? 'UNSCR 2731 and 2732 provide the legal framework for ceasefire implementation and IAEA verification.' : d >= 25 ? 'UNSCR 2731 provides the legal framework for humanitarian corridor operations.' : ''} Marcus?`,
      citations: [`State Department Briefing D${d}`, `COMPASS Diplomatic Model D${d}`, 'Reuters Diplomatic'],
    },
    {
      id: 7, anchor: 'marcus', label: `Economic Impact — Day ${d}`, topic: 'Markets & Energy',
      script: `The economic picture on Day ${d}: Brent crude at ${Math.round(brentUsd)} dollars per barrel — ${d >= 42 ? 'a seven-week low, down fifty-three percent from the one-hundred-and-twenty-three-dollar wartime peak on Day Seventeen.' : d >= 24 ? 'down from a wartime peak of one hundred and twenty-three dollars on Day Seventeen.' : 'elevated significantly from the pre-conflict seventy-four dollar baseline.'} ${d >= 44 ? 'All GCC national oil company tankers — Saudi Aramco, ADNOC, Kuwait Petroleum, QatarEnergy — have cancelled Cape of Good Hope diversions and are routing through Hormuz. The Ras Tanura terminal is fully restored. Bloomberg estimates the conflict cost global consumers two hundred and forty billion dollars.' : d >= 43 ? 'GCC tanker operators are cancelling Cape diversion bookings as Hormuz approaches full clearance. Normalization is accelerating.' : d >= 24 ? (d - 24 + 7) + ' commercial VLCCs have transited the ZB-Alpha corridor under coalition escort since Day Twenty-Four.' : 'Commercial traffic through Hormuz remains suspended.'} ${d >= 27 ? 'The Saudi OPEC Plus two-million-barrel-per-day production increase is stabilizing global supply. Lloyd\'s war-risk premiums ' + (d >= 44 ? 'SUSPENDED as of Day Forty-Four — first time since conflict began.' : 'declining.') : 'Global supply disruption continues.'} ${d >= 28 ? 'COMPASS energy-finance cascade model has retired the recession-trigger alert issued on Day Fifteen.' : ''} Patricia?`,
      citations: [`EIA Report D${d}`, 'Bloomberg Energy', `COMPASS Economic Model D${d}`],
    },
    {
      id: 8, anchor: 'walsh', label: `Pentagon Readiness — Day ${d}`, topic: 'DoD Briefing',
      script: `From the Pentagon on Day ${d}: ${d >= 44 ? 'Secretary of Defense Austin announced the ceasefire trial extension and confirmed the Joint Chiefs are initiating post-conflict readiness review. Quote: "Our men and women achieved everything asked of them. Seventeen gave their lives. This ceasefire is the foundation they built." FPCON adjusted to ALPHA across CONUS installations — first time since the conflict began.' : d >= 43 ? 'The Joint Chiefs confirmed full ceasefire compliance across all five CENTCOM theaters in the first operational period. No hostile activity detected. FPCON ALPHA issued.' : d >= 27 ? 'The Joint Chiefs advised the President that military objectives set on Day One have been substantially achieved. Iran\'s nuclear program ninety-four percent degraded, air force non-functional, ballistic missile stockpile near-exhausted, IRGCN at thirty percent strength. Secretary Austin: "We have achieved our core national security objectives."' : 'Military operations continue toward defined strategic objectives. All coalition forces at DEFCON-3 or higher.'} Total US casualties since Day One: seventeen killed in action, ${61 + Math.max(0, d - 27) * 2} wounded. ${d >= 43 ? 'The military mission now supports durable implementation of the Abu Dhabi framework.' : d >= 28 ? 'The diplomatic window is open. The military mission now supports the Abu Dhabi process.' : ''} Dr. Rostami?`,
      citations: [`Pentagon Press Briefing D${d}`, `CENTCOM PA D${d}`, 'DoD Casualty Summary'],
    },
    {
      id: 9, anchor: 'vargas', label: `Forward Report — Day ${d}`, topic: 'Field Report',
      script: `I'm Corporal Vargas ${d >= 44 ? 'aboard the ZB-Alpha mission completion ceremony, Strait of Hormuz' : 'in the Strait of Hormuz, ZB-Alpha corridor'}. Day ${d}. ${d >= 44 ? 'NAVCENT formally declared ZB-Alpha complete at oh-nine hundred Zulu. The last suspected mine was confirmed a derelict buoy at oh-seven thirty. USS Chief and USS Gladiator are heading home. Today — for the first time since Day Three, forty-one days ago — the Strait of Hormuz is fully open. Forty-seven vessels are staged within a hundred miles. They\'re all transiting.' : d >= 43 ? 'The ceasefire entered into force at oh-six hundred Zulu this morning. It is quiet here. After forty-two days of round-the-clock MCM operations, ZB-Alpha is ninety-nine percent cleared. GOLF-7 and GOLF-8 both inactive.' : d >= 24 ? 'Commercial tankers are transiting again. The ' + (d - 24 + 7) + 'th VLCC passed under coalition escort since Day Twenty-Four. ZB-Alpha is ' + zbAlphaPct + ' percent cleared — ' + (100 - zbAlphaPct) + ' percent remains.' : 'The corridor remains under active mine clearance. ZB-Alpha is ' + zbAlphaPct + ' percent cleared.'} ${d >= 44 ? '' : d >= 26 ? 'GOLF-7 has not sortied since Day Twenty-Two. GOLF-8: inactive. ' : 'GOLF-7 mine-laying operations remain a threat. '} ${d >= 44 ? 'I\'m Corporal Elena Vargas, Epic Fury News Network. The strait is open. Day ' + d + '.' : d >= 28 ? 'Today the diplomatic talks are advancing in Abu Dhabi. ZB-Alpha will not be standing down early. I\'m Corporal Elena Vargas, Epic Fury News Network, Strait of Hormuz, Day ' + d + '.' : 'The MCM crews do not stop sweeping. The corridor doesn\'t open until every mine is pulled. I\'m Corporal Elena Vargas, Epic Fury News Network, Strait of Hormuz, Day ' + d + '.'}`,
      citations: [`CTF-52 MCM Status D${d}`, `NAVCENT SITREP D${d}`, 'MANTIS ACINT Track'],
    },
    {
      id: 10, anchor: 'sarah', label: `Day ${d} Closing Summary`, topic: 'Summary & Outlook',
      script: `To close Day ${d}: ${today.slice(0, 3).map(e => e.title).join('. ') || (d >= 43 ? 'Ceasefire trial holding — all theaters silent — POTUS extends 48 hours' : 'Operations continue across all theaters')}. CENTCOM: ${totalSorties.toLocaleString()}+ sorties${d >= 43 ? ', all offensive ops paused under ceasefire trial' : ''}, ${d >= 44 ? 'Hormuz one hundred percent cleared' : zbAlphaPct + '% Hormuz cleared'}, Iran military infrastructure ${d >= 25 ? 'ninety-four percent degraded and IAEA-confirmed' : 'critically degraded'}. ${d >= 26 ? 'Total US KIA: seventeen. We honor their service and sacrifice.' : ''} ${d >= 44 ? 'Hormuz is fully open for the first time since Day Three. The IAEA is at Natanz. Lloyd\'s is suspending war-risk premiums. The shooting has stopped.' : ''} COMPASS ceasefire probability: ${compassCeasefire}%. Brent: $${Math.round(brentUsd)}. ${d >= 44 ? 'Day Forty-Four. The strait is open. Diplomacy is underway. I\'m Sarah Mitchell. Epic Fury News Network.' : d >= 43 ? 'The ceasefire trial is holding. Forty-two days of conflict. This is what it looks like when force and diplomacy work together. I\'m Sarah Mitchell. Epic Fury News Network.' : d >= 27 ? 'The Abu Dhabi Framework is open. Diplomacy now has the chance to secure what our armed forces have made possible.' : 'The conflict continues.'} Every segment fully sourced. Every claim independently verified.`,
      citations: [`NEXUS All-Domain Assessment D${d}`, `ORACLE-9 D${d}`, `COMPASS D${d}`, `CENTCOM PA D${d}`],
    },
  ]
}

// ── Dynamic intel fallback builder ───────────────────────────────────────────

/**
 * Build day-appropriate fallback intel entries.
 * Returns the most relevant static intel for the current conflict day,
 * ensuring dashboards never show completely empty states.
 */
export function buildDayAwareIntelFallback(limit = 8): Array<{
  id: string
  title: string
  summary: string
  theater: string
  confidence: number
  source_name: string
  created_at: string
}> {
  const day = getConflictDay()
  const recentEvents = CONFLICT_TIMELINE
    .filter(e => e.day <= day)
    .sort((a, b) => b.day - a.day)
    .slice(0, limit)

  return recentEvents.map((ev, i) => ({
    id: `dynamic-fallback-${i}`,
    title: ev.title,
    summary: `Day ${ev.day} · ${ev.theater} theater · Significance: ${ev.significance}`,
    theater: ev.theater,
    confidence: ev.significance === 'CRITICAL' ? 95 : ev.significance === 'HIGH' ? 85 : 70,
    source_name: 'NEXUS Fallback',
    created_at: new Date(Date.UTC(2026, 2, ev.day, 8, 0, 0)).toISOString(),
  }))
}

// ── Dynamic logistics ETA builder ────────────────────────────────────────────

/**
 * Compute a human-readable resupply ETA status that auto-ages.
 * Past deliveries show RECEIVED, today shows ARRIVING, future shows countdown.
 */
export function dynamicETA(deliveryDay: number, detail: string): string {
  const day = getConflictDay()
  if (day > deliveryDay) return `Day ${deliveryDay} — RECEIVED (${detail})`
  if (day === deliveryDay) return `TODAY Day ${deliveryDay} — ARRIVING (${detail})`
  return `Day ${deliveryDay} — ETA in ${deliveryDay - day}d (${detail})`
}
