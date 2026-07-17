/**
 * lib/scenario-events.ts
 * ──────────────────────
 * SINGLE SOURCE OF TRUTH for all scenario narrative events.
 *
 * ┌─────────────────────────────────────────────────────────────┐
 * │  HOW TO UPDATE THE PLATFORM                                 │
 * │  1. Add a new ScenarioEvent entry below (most-recent first) │
 * │  2. That's it — COP, DMO, and the Newsroom ticker all read  │
 * │     from this file automatically.                           │
 * └─────────────────────────────────────────────────────────────┘
 *
 * Fields:
 *   id       – unique slug (e.g. 'se-01')
 *   time     – DTG string (e.g. '221435Z')
 *   type     – MISSILE | ASCM | AIR | SUBSURFACE | CYBER | FLASH |
 *              BDA | MINE | UAS | STRIKE | HVT | LOGISTICS | SWARM | SCALP
 *   severity – CRITICAL | HIGH | MEDIUM | INFO
 *   title    – short ALL-CAPS ticker headline
 *   text     – full operational text shown in COP / DMO event logs
 *   day      – conflict day number
 *   tags     – lowercase keyword tags
 */

export interface ScenarioEvent {
  id:       string
  time:     string
  type:     string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO'
  title:    string
  text:     string
  day:      number
  tags:     string[]
}

/** All scenario events — most recent first. Edit here to update the entire platform. */
export const SCENARIO_EVENTS: ScenarioEvent[] = [
  // ── DAY 27 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-d27a',
    time:     '270800Z',
    type:     'FLASH',
    severity: 'CRITICAL',
    day:      27,
    title:    'POTUS NATIONAL ADDRESS: CEASEFIRE FRAMEWORK — ABU DHABI PROXIMITY TALKS OPEN',
    text:     'POTUS delivered prime-time national address 27 MAR 2026. Primary objectives of Operation Epic Fury substantially achieved: Iran nuclear program degraded 94%, Hormuz ZB-Alpha 100% cleared, missile stockpile at 5-8%. Abu Dhabi proximity talks opened today under UAE/Oman mediation. AUMF-2026 remains active. Military operations continue until formal ceasefire signed. Coalition forces at sustained FPCON CHARLIE. Source: White House / CENTCOM PA 270800Z.',
    tags:     ['potus', 'ceasefire', 'framework', 'abu-dhabi', 'day-27'],
  },
  {
    id:       'se-d27b',
    time:     '270000Z',
    type:     'BDA',
    severity: 'HIGH',
    day:      27,
    title:    'CENTCOM DAY 27 SITREP: 10,400+ SORTIES · HORMUZ 78% CLEARED · BRENT $94',
    text:     'CENTCOM Day 27 operational summary: Coalition air superiority sustained — 7th consecutive day with no hostile aircraft kills. ZB-Alpha 100% clear (7+ VLCCs transited D24-26 under escort). ZB-Beta 55% cleared. Iranian BM stockpile 5-8% pre-conflict. Shahed-136 ~380-460 remaining. Iranian IADS 87% degraded. US KIA total: 17. WIA: 61. Brent crude $94/bbl, down from $112 peak D20. Source: CENTCOM PA 270000Z.',
    tags:     ['sitrep', 'centcom', 'hormuz', 'day-27'],
  },
  // ── DAY 26 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-d26a',
    time:     '261115Z',
    type:     'FLASH',
    severity: 'CRITICAL',
    day:      26,
    title:    'IRAN SNSC DROPS US WITHDRAWAL PRECONDITION — OMAN CHANNEL REACTIVATED',
    text:     'Iran SNSC communicated via Omani FM Badr al-Busaidi: Tehran drops Condition 2 (US forces withdrawal from Gulf) as ceasefire precondition. Revised Iran position: 96h kinetic pause + humanitarian exchange + Hormuz demining talks. Oman channel STATUS: ACTIVE. UAE Crown Prince MbZ confirms Abu Dhabi will host proximity talks. COMPASS ceasefire probability updated: 68% within 72h. Source: Reuters/AP Diplomacy 261115Z.',
    tags:     ['ceasefire', 'oman', 'snsc', 'compass', 'day-26'],
  },
  {
    id:       'se-d26b',
    time:     '260247Z',
    type:     'MISSILE',
    severity: 'CRITICAL',
    day:      26,
    title:    'IRGCAF 5TH BARRAGE — 31 FATEH-110/GHADR — AL UDEID — 2 USAF KIA',
    text:     'IRGCAF 5th and assessed FINAL barrage — 31 × Fateh-110C/Ghadr-H launch detected 260247Z. Targeting Al Udeid AB and maritime patrol area BRAVO. THAAD/PAC-3 intercept: 27/31 (87%). STRUCK: Al Udeid ramp (1×F-35B destroyed, 1×EA-18G destroyed), fuel farm perimeter fire. CASUALTY FLASH: 2 USAF aircrew KIA, 8 WIA. USS Bulkeley SM-2 kill at sea (1 leaker). CENTCOM: Iran BM stockpile now ~5-8% pre-conflict — insufficient for another large barrage. Source: STRATCOM FLASH 260247Z.',
    tags:     ['ballistic-missile', 'al-udeid', 'barrage-5', 'irgcaf', 'kia', 'day-26'],
  },
  // ── DAY 25 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-d25a',
    time:     '251730Z',
    type:     'FLASH',
    severity: 'HIGH',
    day:      25,
    title:    'UNSCR 2731 PASSED 14-1 — HUMANITARIAN CORRIDOR — FULL CEASEFIRE VETOED',
    text:     'UNSCR 2731 (humanitarian corridor) passed 14-1 at 251730Z — Russia cast the sole veto on separate full ceasefire resolution. US abstained on UNSCR 2731 as de-escalation signal. France-sponsored full ceasefire resolution failed (Russia veto).. Iran accepted humanitarian corridor in principle pending implementation terms. Source: UN Security Council / State Dept readout 251800Z.',
    tags:     ['un', 'unsc', 'resolution-2731', 'ceasefire', 'day-25'],
  },
  {
    id:       'se-d25b',
    time:     '250900Z',
    type:     'BDA',
    severity: 'HIGH',
    day:      25,
    title:    'DIA BDA FLASH: IRAN ENRICHMENT INFRA 94% DEGRADED — 18-24 MONTH RECONSTITUTION',
    text:     'DIA Battle Damage Assessment Flash DAF-2026-0325: Iran enrichment infrastructure assessed at 94% functional degradation. Natanz FEP: centrifuge halls A-D collapsed/damaged. Fordow shaft 2-Alpha confirmed collapsed. Isfahan UCF destroyed at surface level. Minimum reconstitution estimate: 18-24 months. Caveat: undeclared site dispersal pre-Day 1 remains unknown. Source: DIA Nuclear Analysis / NGA SAR imagery 250900Z.',
    tags:     ['nuclear', 'bda', 'dia', 'natanz', 'fordow', 'day-25'],
  },
  // ── DAY 24 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-d24a',
    time:     '240800Z',
    type:     'FLASH',
    severity: 'CRITICAL',
    day:      24,
    title:    'ASSEMBLY OF EXPERTS: NO CONSENSUS — IRGC SALAMI ENTRENCHING COMMAND',
    text:     'Assembly of Experts failed to reach consensus on Supreme Leader successor after 26-hour emergency session. IRGC CINC Salami has consolidated command authority — IRGC Aerospace Force ballistic missile units now receiving orders directly from Salami without NCA confirmation protocol. CIA GODFATHER-1: "hardliner faction has locked out pragmatist officers from launch authority chain." DIA: treat as IRGC unilateral command — civilian government sidelined. Source: CIA / NSA FLASH 240800Z.',
    tags:     ['succession', 'salami', 'irgc-cinc', 'nca-gap', 'escalation', 'day-24'],
  },
  {
    id:       'se-d24b',
    time:     '240300Z',
    type:     'MISSILE',
    severity: 'CRITICAL',
    day:      24,
    title:    'IRGCAF BM BARRAGE ALPHA-4 — 9 EMAD/GHADR LAUNCH DETECTED — AL UDEID / ARIFJAN',
    text:     'IRGCAF launch detected 240300Z — 9 × Emad/Ghadr ballistic missiles targeting Al Udeid AB and Camp Arifjan. This is the 4th major barrage of the conflict. THAAD/PAC-3 batteries engaged — tracking ongoing. FLASH to CAOC: all aircraft on ground directed to shelters. 3 missiles assessed BUST (off-trajectory). Intercept confidence: HIGH based on prior performance. NATO ELINT: all 9 TELs originated SW of Isfahan. Source: STRATCOM FLASH / ATLAS-1 launch detect 240301Z.',
    tags:     ['ballistic-missile', 'al-udeid', 'camp-arifjan', 'irgcaf', 'thaad', 'day-24'],
  },
  {
    id:       'se-d24c',
    time:     '241200Z',
    type:     'FLASH',
    severity: 'HIGH',
    day:      24,
    title:    'OMAN BACK-CHANNEL TALKS SUSPENDED — IRAN WITHDRAWAL FOLLOWING BM BARRAGE',
    text:     'Sultanate of Oman confirms Iran withdrew from back-channel ceasefire talks at 241200Z following the Day 24 ballistic missile barrage. Omani FM: "We remain available as host — talks can resume if both parties agree." US State Department: "Iran chose escalation over diplomacy." COMPASS model ceasefire probability downgraded from 8% to 4%. Oman back-channel assessed INACTIVE until further notice. Source: Reuters Muscat / AP Diplomacy 241300Z.',
    tags:     ['oman', 'ceasefire', 'diplomatic', 'compass', 'day-24'],
  },
  // ── DAY 23 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-00a',
    time:     '230600Z',
    type:     'FLASH',
    severity: 'CRITICAL',
    day:      23,
    title:    '⚑ ASSEMBLY OF EXPERTS EMERGENCY SESSION CONVENED — TEHRAN 230600Z',
    text:     '⚑ ASSEMBLY OF EXPERTS EMERGENCY SESSION — Convened 230600Z Tehran to select successor to Khamenei per Iranian Constitution Article 111. Quorum: 52 of 88 members present. Session conducted under IRGC security cordon. 3+ senior members remain unreachable. IRGC CINC retaining interim strategic command authority pending constitutional resolution. Source: DIA FLASH / NEXUS-PINHOLE.',
    tags:     ['assembly-of-experts', 'succession', 'flash', 'day-23'],
  },
  {
    id:       'se-00b',
    time:     '230330Z',
    type:     'HVT',
    severity: 'CRITICAL',
    day:      23,
    title:    'IRGC CINC SALAMI ASSUMES INTERIM STRATEGIC COMMAND — NCA GAP ACTIVE',
    text:     'IRGC CINC Maj Gen Hossein Salami announced interim strategic command as of 230330Z — unilaterally, without Assembly of Experts approval. Lacks constitutional legitimacy but controls IRGC Aerospace Force and missile battalions. Assessed: IRGC hardliner faction now holds nuclear and BM release authority without civilian NCA check. DIA: HIGHEST ESCALATION RISK WINDOW OF CONFLICT. Source: NSA SIGINT FLASH / CIA GODFATHER-1.',
    tags:     ['salami', 'irgc-cinc', 'succession', 'nca-gap', 'escalation', 'day-23'],
  },
  {
    id:       'se-00c',
    time:     '230000Z',
    type:     'FLASH',
    severity: 'HIGH',
    day:      23,
    title:    'UN SECURITY COUNCIL EMERGENCY SESSION CONVENED — RESOLUTION DRAFT CIRCULATING',
    text:     'UN Security Council Emergency Session convened 230000Z New York. France + UK circulating draft ceasefire resolution. Russia and China indicated potential abstention (not veto) given Khamenei KIA escalation risk. US: "will not veto a humanitarian pause resolution." Iran seat empty — deputy ambassador present. Source: Reuters UN Bureau / State Dept readout.',
    tags:     ['un', 'unsc', 'ceasefire', 'diplomatic', 'day-23'],
  },
  // ── DAY 22 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-01',
    time:     '221435Z',
    type:     'HVT',
    severity: 'CRITICAL',
    day:      22,
    title:    '⚑ KHAMENEI KIA — PRECISION AIRSTRIKE IRAN NCA 221435Z — DIA FLASH CONFIRMED',
    text:     '⚑ SUPREME LEADER KHAMENEI KIA — Precision airstrike on IRGC National Command Post Tehran 221435Z. Ali Khamenei KILLED confirmed via NGA/NRO + dual HUMINT corroboration. IRGC retaliation posture: UNKNOWN. ALL regional IRGC naval, air, missile assets elevated to MAXIMUM readiness. National Command Authority notified. FPCON → DELTA. Source: NEXUS/DIA FLASH · GODFATHER-1.',
    tags:     ['khamenei', 'hva', 'flash', 'fpcon-delta', 'day-22'],
  },
  {
    id:       'se-02',
    time:     '220835Z',
    type:     'MISSILE',
    severity: 'CRITICAL',
    day:      22,
    title:    'FATEH-110 SRBM INTERCEPTED BY CG-55 SM-3 BLOCK IIA — 0835Z',
    text:     'Fateh-110 SRBM launch CONFIRMED — Tabriz Site-7, traj 220° bearing CVN-71 area. SM-3 engagement by CG-55 LEYTE GULF. Source: DSP/SBIRS.',
    tags:     ['missile', 'srbm', 'fateh-110', 'sm-3', 'cg-55', 'day-22'],
  },
  {
    id:       'se-03',
    time:     '220742Z',
    type:     'UAS',
    severity: 'CRITICAL',
    day:      22,
    title:    'SHAHED-136 SWARM ×4 — VIPER CAP 2 KILLS CONFIRMED — HOZ EASTERN SECTOR',
    text:     'Shahed-136 swarm (4 tracks: SHAD-04/05/06/07) — egressing Jask AB, heading 240°. VIPER CAP engaged. 2 kills confirmed. Source: SENTRY-11.',
    tags:     ['shahed', 'uas', 'swarm', 'viper-cap', 'day-22'],
  },
  {
    id:       'se-04',
    time:     '220615Z',
    type:     'SUBSURFACE',
    severity: 'CRITICAL',
    day:      22,
    title:    'GOLF-7 KILO SSK — 9NM FROM ZB-ALPHA · SSN-777 PROSECUTING',
    text:     'GOLF-7 Kilo SSK repositioned — now 9nm from ZB-Alpha: 26.3°N/56.1°E. Mine re-seeding attempt IMMINENT. SSN-777 N. CAROLINA prosecuting. Source: MANTIS ACINT.',
    tags:     ['golf-7', 'kilo', 'ssn-777', 'mcm', 'zb-alpha', 'day-22'],
  },
  {
    id:       'se-05',
    time:     '220530Z',
    type:     'AIR',
    severity: 'HIGH',
    day:      22,
    title:    'BANDIT-γ/δ SU-25K PAIR — GROUND ATTACK PROFILE HOZ SAG — WARNING SHOTS AUTH',
    text:     'BANDIT-γ/δ (Su-25K pair) — airborne Bandar Abbas, heading 210°, FL080. Assessed ground attack profile for HOZ SAG. ROE: WARNING SHOTS AUTHORIZED. Source: WEDGETAIL-1.',
    tags:     ['bandit', 'su-25k', 'air', 'hoz-sag', 'day-22'],
  },
  {
    id:       'se-06',
    time:     '220447Z',
    type:     'STRIKE',
    severity: 'INFO',
    day:      22,
    title:    'B-21 RAIDER COMBAT DEBUT — ANVIL-01 · 2× GBU-57B MOP · NATANZ',
    text:     'B-21 RAIDER (ANVIL-01) — COMBAT DEBUT CONFIRMED. 2× MOP GBU-57B employment against IRGC Natanz hardened tunnel complex. BDA pending NGA Imagery. Source: STRATCOM/CAOC.',
    tags:     ['b-21', 'raider', 'anvil-01', 'natanz', 'mop', 'combat-debut', 'day-22'],
  },
  {
    id:       'se-07',
    time:     '220310Z',
    type:     'SWARM',
    severity: 'HIGH',
    day:      22,
    title:    'IRGCN 4× FAC SWARM SORTIE BANDAR ABBAS — SAG-BRAVO ALERT',
    text:     'IRGCN FAC-1/2/3 (Thondor-class) + FAC-4 (Houdong) — 4-vessel swarm sortie from Bandar Abbas. SAG-Bravo alerted. CG-55 SM-2 engagement range. Source: CTF-52.',
    tags:     ['fac', 'irgcn', 'swarm', 'sag-bravo', 'bandar-abbas', 'day-22'],
  },
  {
    id:       'se-08',
    time:     '220215Z',
    type:     'SUBSURFACE',
    severity: 'HIGH',
    day:      22,
    title:    'GHADIR-3 MINI-SSK — PROSECUTED BY CHARGER-2 MH-60R + P-8A CREW-12',
    text:     'GHADIR-3 mini-SSK sonar contact — 26.4°N/56.7°E, heading 155, 3kts. CHARGER-2 MH-60R and P-8A CREW-12 on prosecution. Source: USS N. CAROLINA.',
    tags:     ['ghadir', 'mini-ssk', 'asw', 'mh-60r', 'p-8a', 'day-22'],
  },
  {
    id:       'se-09',
    time:     '220100Z',
    type:     'MINE',
    severity: 'CRITICAL',
    day:      22,
    title:    'EM-52 MINES ZB-ALPHA N-LANE — MCM HOLD LIFTED 0830Z',
    text:     'ROV-7 confirmed 3 new EM-52 influence mines ZB-Alpha N. lane — GOLF-7 re-seeding activity overnight D21/22. MCM hold ZB-Alpha 0045–0830Z. Source: MCM-14 SITREP.',
    tags:     ['mine', 'em-52', 'zb-alpha', 'mcm', 'day-22'],
  },
  // ── DAY 21 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-10',
    time:     '211910Z',
    type:     'CYBER',
    severity: 'MEDIUM',
    day:      21,
    title:    'GPS SPOOFING +40% HOZ CORRIDOR AND RED SEA — NavWar EMCON ACTIVE',
    text:     'GPS spoofing intensity up 40% vs D19 — HOZ transit corridor and Red Sea approach. NavWar EMCON countermeasures active. Advise INS/SAASM only. Source: CENTCOM J6.',
    tags:     ['cyber', 'gps', 'spoofing', 'emcon', 'day-21'],
  },
  {
    id:       'se-11',
    time:     '211755Z',
    type:     'BDA',
    severity: 'INFO',
    day:      21,
    title:    'B-2A SPIRIT-01 BDA D21 — BANDAR ABBAS MISSILE STORAGE 91% DESTROYED',
    text:     'B-2A SPIRIT-01 BDA confirmed D21 strike — IRGCN Bandar Abbas missile storage 91% destroyed per NGA/Maxar. C-802 battery no longer assessed operational. Source: DIA.',
    tags:     ['b-2a', 'bda', 'bandar-abbas', 'c-802', 'day-21'],
  },
  {
    id:       'se-12',
    time:     '211620Z',
    type:     'LOGISTICS',
    severity: 'INFO',
    day:      21,
    title:    'CSG-2 LOGISTICS SITREP D21 — ALL SHIPS OPERATIONAL · REPLENISHMENT COMPLETE',
    text:     'CSG-2 logistics sitrep Day 21: All surface combatants reporting operational readiness. USS Gerald R. Ford (CVN-78) replenishment complete — UNREP from USNS Arctic. Strike sortie rate sustained. 5th Fleet surface screen intact — no confirmed warship losses. Source: NAVCENT SREP.',
    tags:     ['csg-2', 'logistics', 'unrep', 'cvn-78', 'day-21'],
  },
  {
    id:       'se-13',
    time:     '211300Z',
    type:     'SCALP',
    severity: 'INFO',
    day:      21,
    title:    'CDG RAFALE M SCALP-EG — QESHM ISLAND IADS NODE DESTROYED',
    text:     'CDG Rafale M SCALP-EG strike — IRGC IADS node Qeshm Island. 4× missiles employed, 3 hits confirmed. Radar emitters silent since 1320Z. Source: FAF/CAOC ALLIED.',
    tags:     ['scalp', 'rafale', 'cdg', 'qeshm', 'iads', 'day-21'],
  },
  // ── DAY 13 ───────────────────────────────────────────────────────────────────
  {
    id:       'se-14',
    time:     '130930Z',
    type:     'ASCM',
    severity: 'HIGH',
    day:      13,
    title:    'IRGCN C-802 COASTAL BATTERY ENGAGEMENT D13 — 2 KIA IRGCN CREW · BATTERY SUPPRESSED',
    text:     'IRGCN C-802 coastal battery at Qeshm Island engaged coalition naval forces D13 0930Z — battery suppressed by SEAD strike within 11 minutes. 2× IRGCN crew KIA per CENTCOM BDA. No confirmed coalition ship damage. USN surface screen AAW status GREEN. Source: NAVCENT FLASH / CTF-52 / NGA GEOINT.',
    tags:     ['irgcn', 'c-802', 'ascm', 'qeshm', 'battery', 'day-13'],
  },
]
