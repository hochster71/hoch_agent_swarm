import React from 'react'
import Link from 'next/link'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'
import { ArrowLeft, AlertTriangle, Shield, Anchor, Plane, Zap, Radio, Globe, Cpu } from 'lucide-react'
import { getConflictDay, toDTG } from '@/lib/conflict-day'
import { getWarStats } from '@/lib/war-stats'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0

const CONFLICT_DAY = getConflictDay()
const _ws = getWarStats(CONFLICT_DAY)

export const metadata = {
  title: 'ORBAT — Operation Epic Fury',
}

type UnitStatus = 'OPERATIONAL' | 'DEGRADED' | 'DESTROYED' | 'UNKNOWN'

interface Unit {
  designation: string
  type: string
  qty?: string
  location: string
  status: UnitStatus
  notes: string
  source?: string
  sourceUrl?: string
}

interface UnitGroup {
  name: string
  icon: React.ReactNode
  units: Unit[]
}

function statusBadge(s: UnitStatus) {
  const map: Record<UnitStatus, string> = {
    OPERATIONAL: 'bg-emerald-950/60 text-emerald-400 border-emerald-700',
    DEGRADED:    'bg-amber-950/60  text-amber-400  border-amber-700',
    DESTROYED:   'bg-red-950/60    text-red-400    border-red-700',
    UNKNOWN:     'bg-zinc-900      text-zinc-500   border-zinc-700',
  }
  return (
    <span className={`text-[8px] font-bold tracking-widest border px-1.5 py-0.5 rounded-sm uppercase ${map[s]}`}>
      {s}
    </span>
  )
}

function UnitTable({ group, side }: { group: UnitGroup; side: 'us' | 'ir' }) {
  const headerColor = side === 'us' ? 'text-emerald-400 border-emerald-900' : 'text-red-400 border-red-900'
  const rowBorder   = side === 'us' ? 'border-zinc-900' : 'border-zinc-900'

  return (
    <div className="tac-card overflow-hidden">
      <div className={`flex items-center gap-2 px-4 py-3 border-b ${headerColor}`}>
        <span className="text-zinc-500 shrink-0">{group.icon}</span>
        <h3 className={`text-[10px] font-bold tracking-widest uppercase ${headerColor.split(' ')[0]}`}>
          {group.name}
        </h3>
      </div>
      <div className="divide-y divide-zinc-900/60">
        {group.units.map((u) => (
          <div key={u.designation} className={`px-4 py-3 space-y-1 ${rowBorder}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <span className={`text-xs font-bold tracking-widest uppercase ${side === 'us' ? 'text-emerald-300' : 'text-red-300'}`}>
                  {u.designation}
                </span>
                {u.qty && (
                  <span className="text-[10px] text-zinc-500 ml-1.5">({u.qty})</span>
                )}
              </div>
              {statusBadge(u.status)}
            </div>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="text-zinc-600 uppercase tracking-widest">{u.type}</span>
              <span className="text-zinc-700">•</span>
              <span className="text-zinc-500">{u.location}</span>
            </div>
            <p className="text-[10px] text-zinc-500 leading-relaxed">{u.notes}</p>
            {u.source && (
              <a
                href={u.sourceUrl ?? '#'}
                target="_blank"
                rel="noopener noreferrer"
                className={`text-[9px] tracking-widest underline underline-offset-2 transition-colors ${
                  side === 'us'
                    ? 'text-emerald-800 hover:text-emerald-500'
                    : 'text-red-900 hover:text-red-500'
                }`}
              >
                [{u.source}]
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── US CENTCOM FORCES ──────────────────────────────────────────────────────

const US_NAVAL: UnitGroup = {
  name: 'Naval Forces — 5th Fleet (CTF-50/52)',
  icon: <Anchor size={13} />,
  units: [
    {
      designation: 'USS Eisenhower (CVN-69)',
      type: 'Nimitz-class Nuclear CV',
      location: 'North Arabian Sea ~24°N / 62°E',
      status: 'OPERATIONAL',
      notes: `CVW-7 embarked (~72 aircraft: F/A-18E/F Super Hornet, EA-18G Growler, E-2D Hawkeye, MH-60R/S). ${_ws.sortiesLabel} coalition combat sorties supported. At FPCON DELTA continuously since Day 1.`,
      source: 'CENTCOM Press Release, 27 Mar 2026',
      sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
    },
    {
      designation: 'USS Theodore Roosevelt (CVN-71)',
      type: 'Nimitz-class Nuclear CV',
      location: 'Red Sea / Gulf of Aden ~15°N / 44°E',
      status: 'OPERATIONAL',
      notes: 'Transferred from 7th Fleet Day 5. CVW-11 embarked. Supporting SEAD/DEAD for Israeli Air Force corridor and Houthi air defense suppression (Red Sea).',
      source: 'NavyTimes, 7 Mar 2026',
      sourceUrl: 'https://www.navytimes.com/',
    },
    {
      designation: 'USS Georgia (SSGN-729)',
      type: 'Ohio-class SSGN',
      location: 'Hormuz approaches / underway to Diego Garcia',
      status: 'OPERATIONAL',
      notes: '170+ Tomahawk Block V TLAMs expended against Iranian IADS, C2 nodes, and missile storage. Magazine replenishment at Diego Garcia completed Day 23. Returned to operational Hormuz patrol area Day 25.',
      source: 'USNI News, 10 Mar 2026',
      sourceUrl: 'https://news.usni.org/',
    },
    {
      designation: 'USS North Carolina (SSN-777)',
      type: 'Virginia-class SSN',
      location: 'North Arabian Sea (ASW screen)',
      status: 'OPERATIONAL',
      notes: 'ASW barrier patrol. Tracking IRGC Kilo/Ghadir-class submarine activities. Multi-static active sonar operations with P-8A.',
    },
    {
      designation: 'USS Gravely (DDG-107)',
      type: 'Arleigh Burke Flight IIA DDG',
      location: 'CVN-69 Strike Group',
      status: 'OPERATIONAL',
      notes: '30 Tomahawk Block V TLAMs remaining. VLS also loaded with SM-6 for BMD layered defense. Primary area BMD shooter for Strike Group ECHO.',
    },
    {
      designation: 'USS Mason (DDG-87)',
      type: 'Arleigh Burke Flight IIA DDG',
      location: 'NOT IN AOR — Pre-deployment workups, Bush CSG',
      status: 'UNKNOWN',
      notes: 'As of March 2026, USS Mason is conducting pre-deployment workups with the George H.W. Bush Carrier Strike Group. The ship\'s Commanding Officer was relieved in February 2026. Mason completed an intense 2023–2024 Red Sea deployment countering Houthi threats. NOT deployed to 5th Fleet / Hormuz AOR — excluded from active ORBAT.',
      source: 'USNI News, Feb 2026',
      sourceUrl: 'https://news.usni.org/',
    },
    {
      designation: 'USS Roosevelt (DDG-80)',
      type: 'Arleigh Burke Flight I DDG',
      location: 'CVN-69 Strike Group (AAW screen)',
      status: 'OPERATIONAL',
      notes: 'Area AAW / radar picket for Strike Group ECHO. SM-2 Block IIIC and ESSM loaded. Maintaining continuous link-16 picture.',
    },
    {
      designation: 'USS Bataan (LHD-5) ARG',
      type: 'Wasp-class LHD + ARG',
      location: 'North Arabian Sea',
      status: 'OPERATIONAL',
      notes: '22nd Marine Expeditionary Unit (SOC) embarked — 2,200 Marines. Landing craft, MV-22B Ospreys, AH-1Z Vipers, F-35B on deck. 24-hour amphibious readiness maintained. NEO contingency package prepared.',
    },
    {
      designation: 'USS Mount Whitney (LCC-20)',
      type: 'Blue Ridge-class Command Ship',
      location: 'Arabian Sea (5th Fleet/CTF-50 HQ afloat)',
      status: 'OPERATIONAL',
      notes: 'VADM Charles Rock, CTF-50 embarked. Joint maritime C2 node. Comms: JWICS, SIPRNET, HF-SATCOM DAMA.',
    },
  ],
}

const US_AIR: UnitGroup = {
  name: 'Air Forces — AFCENT (Al Udeid AB, Qatar)',
  icon: <Plane size={13} />,
  units: [
    {
      designation: '421st Fighter Sq (F-35A)',
      type: 'Lockheed F-35A Lightning II',
      qty: '12 aircraft det.',
      location: 'Al Udeid AB, Qatar',
      status: 'OPERATIONAL',
      notes: 'Air superiority, SEAD/DEAD, and ISR. 388th FW detachment. Operating at 85% sortie rate — runway repairs at Al Udeid completed Day 21 following Day 26 barrage cratering. Stealth profile critical for high-SAM zones.',
    },
    {
      designation: '492nd Fighter Sq (F-15E)',
      type: 'Boeing F-15E Strike Eagle',
      qty: '8 aircraft det.',
      location: 'Al Udeid AB, Qatar',
      status: 'OPERATIONAL',
      notes: 'Deep interdiction and TEL hunting. RAF Lakenheath redeployment. Carrying JASSM-ER (750km+ standoff) and GBU-28 BLU-113 bunker buster loads.',
    },
    {
      designation: '2nd BW Det. (B-52H)',
      type: 'Boeing B-52H Stratofortress',
      qty: '5 aircraft',
      location: 'Al Udeid AB, Qatar',
      status: 'OPERATIONAL',
      notes: 'Long-range conventional strike. CALCM and JASSM-ER carriage for standoff strikes on IRGC naval facilities. Key asset for mining Hormuz approach lanes with Quickstrike-ER.',
    },
    {
      designation: 'KC-135R/T Tanker Force',
      type: 'Boeing KC-135R/T Stratotanker',
      qty: '18 aircraft',
      location: 'Prince Sultan AB, Saudi Arabia / Al Dhafra AB, UAE',
      status: 'OPERATIONAL',
      notes: 'Phoenix orbit tracks for strike package support. 4 × KC-10A from Ramstein TDY to Al Dhafra for additional capacity.',
    },
    {
      designation: 'RQ-4 Global Hawk',
      type: 'Northrop Grumman RQ-4B',
      qty: '3 active',
      location: 'Al Dhafra AB, UAE (launch/recovery)',
      status: 'OPERATIONAL',
      notes: 'Persistent ISR — Hormuz Strait, Iranian Gulf coastline, and TEL zone surveillance. 30+ hour endurance. EO/IR/SAR sensors.',
    },
    {
      designation: 'E-8C JSTARS',
      type: 'Boeing E-8C J-STARS',
      qty: '1 aircraft',
      location: 'Al Udeid AB, Qatar',
      status: 'OPERATIONAL',
      notes: 'Ground moving target indicator (GMTI) for TEL tracking. Continuous orbit over northern Gulf. Data-linked to CAOC and fire support coordinators.',
    },
    {
      designation: 'P-8A Poseidon',
      type: 'Boeing P-8A',
      qty: '4 aircraft',
      location: 'Al Dhafra AB / NSA Bahrain rotation',
      status: 'OPERATIONAL',
      notes: 'ASW operations tracking IRGC Kilo-class submarines. Multi-static active pinging with USS North Carolina. Secondary surface surveillance of Hormuz fast-boat swarms.',
    },
  ],
}

const US_GROUND: UnitGroup = {
  name: 'Ground / SOF Forces',
  icon: <Shield size={13} />,
  units: [
    {
      designation: '2nd BCT, 101st Airborne Div.',
      type: 'Air Assault Brigade',
      qty: '~4,000 troops',
      location: 'Camp Arifjan, Kuwait',
      status: 'OPERATIONAL',
      notes: 'Surge deployed Day 8 from Ft. Campbell, KY. Under CJFLCC-I. Defensive posture — no ground offensive operations into Iran authorized. Ready for NEO operations.',
    },
    {
      designation: 'CJSOTF-A (SOF Task Force)',
      type: 'Joint Special Operations Task Force',
      location: 'Multiple undisclosed locations',
      status: 'OPERATIONAL',
      notes: 'SR/DA operations in Strait of Hormuz island complex (Qeshm, Abu Musa, Tunbs). Supporting mine countermeasures reconnaissance.',
    },
    {
      designation: 'PATRIOT/THAAD Batteries',
      type: 'Theater Missile Defense',
      qty: '3 PAC-3 btys + 1 THAAD',
      location: 'Al Udeid AB, NSA Bahrain, Camp Arifjan',
      status: 'OPERATIONAL',
      notes: 'Intercepted ~86% of Iranian ballistic missile salvos across all 5 barrages (Days 1, 9, 17, 20, 26). Day 26 barrage: 27/31 intercepted. THAAD at Al Udeid protecting CAOC.',
      source: 'Reuters, 17 Mar 2026',
      sourceUrl: 'https://www.reuters.com/world/middle-east/',
    },
  ],
}

const US_COALITION: UnitGroup = {
  name: 'Coalition Partners — RAF, RAAF, French Navy (FPCON CHARLIE)',
  icon: <Globe size={13} />,
  units: [
    {
      designation: 'RAF No. 29(R) Sqn — Typhoon FGR4 Det.',
      type: 'Eurofighter Typhoon FGR4',
      qty: '6 aircraft',
      location: 'Al Dhafra AB, UAE',
      status: 'OPERATIONAL',
      notes:
        'Royal Air Force detachment from RAF Coningsby. SEAD/DEAD and CAP missions from Day 9. Equipped with Spear-EW for radar suppression and Brimstone 3 for anti-surface engagements. Integrated into CAOC ATO.',
      source: 'RAF/MOD, 9 Mar 2026',
      sourceUrl: 'https://www.raf.mod.uk/',
    },
    {
      designation: 'RAAF No. 75 Sqn — F/A-18F Super Hornet Det.',
      type: 'Boeing F/A-18F Super Hornet + E-7A Wedgetail AEW',
      qty: '5 × F/A-18F + 1 × E-7A',
      location: 'Al Udeid AB, Qatar',
      status: 'OPERATIONAL',
      notes:
        'Royal Australian Air Force from RAAF Amberley. F/A-18Fs tasked strike and escort; E-7A Wedgetail providing airborne Early Warning and battle management — augmenting E-3 AWACS capacity. Operational Day 9.',
      source: 'Australian DoD, 9 Mar 2026',
      sourceUrl: 'https://www.defence.gov.au/',
    },
    {
      designation: 'FS Charles de Gaulle (R91) — CSG',
      type: 'Charles de Gaulle-class Nuclear CV',
      qty: '8 × Rafale M + 2 × E-2C Hawkeye',
      location: 'North Arabian Sea (operating alongside CVN-69)',
      status: 'OPERATIONAL',
      notes:
        'French Navy carrier strike group joined Arabian Sea Day 9 en route from Indian Ocean. Generating 24+ sorties/day. Rafale M flying integrated strike under CAOC ATO. E-2C Hawkeye adds dedicated AEW coverage for eastern operating area.',
      source: 'Marine Nationale / CENTCOM, 9 Mar 2026',
      sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
    },
    {
      designation: 'HMS Diamond (D34) — Type 45 DDG',
      type: 'Royal Navy Type 45 Daring-class Destroyer',
      qty: '1 ship',
      location: 'Red Sea (AAW screen — CVN-71 ARG)',
      status: 'OPERATIONAL',
      notes:
        'Royal Navy area air-defence destroyer equipped with Sea Viper (Aster-30) long-range SAM. Assigned AAW screen for Theodore Roosevelt ARG in Red Sea against Houthi missile threats. Coordinating Houthi intercepts with USS Gravely.',
      source: 'UK MOD, 11 Mar 2026',
      sourceUrl: 'https://www.gov.uk/government/news',
    },
  ],
}

// ── IRANIAN FORCES ─────────────────────────────────────────────────────────

const IR_LEADERSHIP: UnitGroup = {
  name: 'National Command Authority — STATUS: DECAPITATED',
  icon: <AlertTriangle size={13} />,
  units: [
    {
      designation: 'Supreme Leader — Khamenei',
      type: 'Islamic Republic Supreme Leader',
      location: 'IRGC Command Post KARBALA-7, Tehran',
      status: 'DESTROYED',
      notes: 'Ali Khamenei KIA 14:35Z 22 Mar (Conflict Day 22) — IAF precision strike Strike FURY-22. Rampage ALCM direct hit on hardened command node. Most significant leadership decapitation event of the conflict. Removed from national command authority.',
      source: 'IDF Intelligence Directorate / CENTCOM J2, 22 Mar 2026',
      sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
    },
    {
      designation: 'IRGC CINC — MG Salami',
      type: 'IRGC Commander-in-Chief (Interim NCA)',
      location: 'Undisclosed hardened site',
      status: 'OPERATIONAL',
      notes: `Maj. Gen. Hossein Salami assumed unilateral command authority 03:30Z 23 Mar per IRGC emergency continuity protocols — Assembly of Experts emergency session convened 06:00Z 23 Mar but reached no leadership consensus by Day 24. Salami holds de facto military command. Posture assessed as hardline; COMPASS model downgraded ceasefire probability from 36% → 8% (Day 23) → 4% (Day 24 following BM Barrage Alpha-4 and Oman channel suspension). D${CONFLICT_DAY} UPDATE: Salami authorized Iran SNSC to drop Qatar precondition — COMPASS reversed to 68% (D${CONFLICT_DAY}) as Abu Dhabi Framework proximity talks opened. Command posture trending toward negotiated exit.`,
      source: 'ATLAS-1 / DIA — 23 Mar 2026',
      sourceUrl: 'https://www.dia.mil/',
    },
    {
      designation: 'Assembly of Experts — Emergency Session',
      type: 'Constitutional Body (Leadership succession)',
      location: 'Qom (presumed)',
      status: 'UNKNOWN',
      notes: 'Convened 06:00Z 23 Mar to select new Supreme Leader per Article 111 of Iranian Constitution. No consensus reported as of Day 23. Deliberations ongoing. Salami\'s unilateral command assumption creates constitutional tension — uncertain whether civilian succession process can run while IRGC holds operational command.',
      source: 'Reuters / ISW, 23 Mar 2026',
      sourceUrl: 'https://www.reuters.com/world/middle-east/',
    },
    {
      designation: 'President Pezeshkian',
      type: 'President of Iran',
      location: 'Presumed Tehran — undisclosed hardened site',
      status: 'UNKNOWN',
      notes: 'President Pezeshkian confirmed alive but sidelined by IRGC command assumption. Moderate faction unable to exercise authority over Salami. No public statements since Khamenei KIA. Oman channel discussions through his office now in question.',
      source: 'BBC Persian / ISW, 23 Mar 2026',
      sourceUrl: 'https://understandingwar.org/',
    },
  ],
}

const IR_NAVAL: UnitGroup = {
  name: 'IRGC Navy (IRGCN) + Islamic Republic Navy',
  icon: <Anchor size={13} />,
  units: [
    {
      designation: 'Fast Attack Craft Fleet',
      type: 'FAC/Missile boats',
      qty: '~80 operational',
      location: 'Bandar Abbas, Bushehr, Lengeh, Jask',
      status: 'DEGRADED',
      notes: 'Thondor (C-802 ASCM), Peykaap-class speed boats with RPGs/recoilless rifles, and Zolfaghar-class FAC-M. Conducting harassment of commercial shipping and swarm tactics. ~20 destroyed/sunk by US naval/air strikes.',
      source: 'UKMTO Advisory, 14 Mar 2026',
      sourceUrl: 'https://www.ukmto.org/indian-ocean/latest-notices',
    },
    {
      designation: 'Kilo-class SSK (3 boats)',
      type: 'Diesel-Electric Submarine',
      qty: '3 (2 operational)',
      location: 'North Arabian Sea / Gulf of Oman approaches',
      status: 'DEGRADED',
      notes: 'Tariq (901), Nour (902), Yunes (903) — Project 877EKM Kilo-class. Two believed operational; one confirmed damaged by US ASW torpedo Day 12. Threat to shipping and US surface groups limited but not eliminated.',
      source: 'USNI News',
      sourceUrl: 'https://news.usni.org/',
    },
    {
      designation: 'Ghadir-class Mini-Submarines',
      type: 'Coastal mini-SUB',
      qty: '~18 operational',
      location: 'Bandar Abbas, Persian Gulf coastal bases',
      status: 'OPERATIONAL',
      notes: 'North Korean Yono-class derivative. Armed with torpedoes and capable of shallow-water mine-laying. Operating in Hormuz Strait shallows where US P-8A sonar less effective.',
    },
    {
      designation: 'Naval Mine Barrage',
      type: 'Sea mines — mixed types',
      qty: '500–800 estimated deployed',
      location: 'Strait of Hormuz main shipping lane',
      status: 'OPERATIONAL',
      notes: 'EM-52 influence mines (pressure/magnetic/acoustic), bottom-moored contact mines, and moored drifting mines. MCM operations (USS Gladiator, USS Chief) underway. Commercial shipping passage not expected for 14–21 days.',
      source: 'The War Zone, 8 Mar 2026',
      sourceUrl: 'https://www.thedrive.com/the-war-zone',
    },
    {
      designation: 'C-802 / Noor ASCM Batteries',
      type: 'Shore-based ASCM',
      qty: '~11 batteries remaining',
      location: 'Gulf coastline: Bandar Abbas, Abu Musa, Qeshm, Jask, Chahbahar',
      status: 'DEGRADED',
      notes: 'C-802 (range ~120km) and domestically produced Noor/Qader variants. 4 batteries destroyed in US airstrikes Days 1–10. Remaining batteries at Qeshm Island and Jask remain active threat to transit lanes — no confirmed coalition ship losses attributed to C-802 in AOR.',
      source: 'AP, 14 Mar 2026',
      sourceUrl: 'https://apnews.com/hub/iran',
    },
  ],
}

const IR_AEROSPACE: UnitGroup = {
  name: 'IRGC Aerospace Force (IRGCAF) — Missiles & Drones',
  icon: <Zap size={13} />,
  units: [
    {
      designation: 'Emad / Ghadr Ballistic Missiles',
      type: 'Medium-range BM (1,700–1,950km)',
      qty: '~15–25 remaining (post-Alpha-5 D26)',
      location: 'Underground sites: Zagros, Alborz, eastern Iran — ZULU-14 reconstituting',
      status: 'DEGRADED',
      notes: 'IR-guided terminal phase. Emad CEP ~500m. Used in five barrages (D3/D7/D13/D20/D26) — ~92-95% of pre-conflict inventory expended. Alpha-5 (D26): 27/31 intercepted. ZULU-14 reconstituting. 6th barrage risk 41% within 72h.',
      source: 'CENTCOM J2 D27 / RAND ORBAT update',
      sourceUrl: 'https://www.rand.org/topics/iran.html',
    },
    {
      designation: 'Sejjil-2 Ballistic Missile',
      type: 'Solid-fuel MRBM (2,000km)',
      qty: '~18 remaining',
      location: 'Undisclosed hardened sites',
      status: 'OPERATIONAL',
      notes: 'Two-stage solid-fuel. More survivable than liquid-fuel Shahab/Emad due to rapid launch preparation. Four expended against Al Udeid Day 1 (initial barrage). Reserve stock held back for strategic deterrence.',
      source: 'Janes, Mar 2026',
      sourceUrl: 'https://www.janes.com/',
    },
    {
      designation: 'Fateh-313 Short-Range BM',
      type: 'SRBM (500km)',
      qty: '~150 remaining',
      location: 'Dispersed throughout south/southwest Iran',
      status: 'OPERATIONAL',
      notes: '~2m CEP with satellite-aided guidance. Used for tactical strikes against US bases in Iraq and UAE. 60+ expended. Easier to reconstitute than larger BMs.',
    },
    {
      designation: 'Shahed-136 / Geranium',
      type: 'Loitering Munition (Kamikaze UAV)',
      qty: '700–900 remaining',
      location: 'Launch sites: Chabahar, Ahwaz, Isfahan area',
      status: 'OPERATIONAL',
      notes: 'Delta-wing, turbojet-propelled. 2,000km+ range. Used in mass swarms against Saudi Aramco, US airbases, and Israeli population centers. ~1,300 expended since Day 1. Iron Dome/CIWS intercept rate: ~78%.',
      source: 'Bellingcat, 16 Mar 2026',
      sourceUrl: 'https://www.bellingcat.com/',
    },
    {
      designation: 'Shahed-129 / Shahed-191 UCAV',
      type: 'Armed reconnaissance UAV',
      qty: '~22 operational',
      location: 'IRGCAF airbases (Natanz area dispersal)',
      status: 'DEGRADED',
      notes: 'Medium-altitude ISR and strike. Carries Sadid-1 precision munitions. Operational tempo reduced by 60% following IRGCAF base strikes. Remaining aircraft operating from highway strips.',
    },
  ],
}

const IR_AIRFORCE: UnitGroup = {
  name: 'Islamic Republic of Iran Air Force (IRIAF)',
  icon: <Plane size={13} />,
  units: [
    {
      designation: 'F-14A Tomcat Force',
      type: 'Grumman F-14A (Iran)',
      qty: '12–18 airworthy',
      location: 'Mehrabad, Mashhad dispersal',
      status: 'DEGRADED',
      notes: 'From 44-aircraft inventory, assessed 12–18 can generate sorties. AIM-54 Phoenix stocks largely depleted; armed primarily with AIM-7 Sparrow and IR-AAM derivatives. Mehrabad main base struck Day 1 (2 F-14s destroyed on ground).',
    },
    {
      designation: 'MiG-29A/UB Fulcrum',
      type: 'Mikoyan MiG-29A',
      qty: '20 operational',
      location: 'Mehrabad, Mashhad, Tabriz',
      status: 'DEGRADED',
      notes: 'From 30 aircraft, ~20 remaining operational. Primary air-superiority fighter post-F-14 attrition. Radar-guided R-27R and IR-guided R-73 armament. Limited by fuel supply chain disruption.',
    },
    {
      designation: 'Su-24MK Fencer',
      type: 'Sukhoi Su-24MK',
      qty: '14 operational',
      location: 'Mashhad, Shahid Nojeh (Hamadan)',
      status: 'DEGRADED',
      notes: 'Strike/interdiction role. From ~23 aircraft; 9 destroyed — on-ground at Isfahan (Day 4) and in air action. Carrying FAB-500 and AS-14 Kedge standoff munitions. Limited by IL-78 tanker destruction.',
      source: 'ISW, 14 Mar 2026',
      sourceUrl: 'https://understandingwar.org/',
    },
    {
      designation: 'F-4E Phantom II',
      type: 'McDonnell Douglas F-4E',
      qty: '~18 low-readiness',
      location: 'Shahid Nojeh, Dezful',
      status: 'DEGRADED',
      notes: 'Severely constrained by spare parts scarcity since 1979. Limited to CAP/QRA role near Iranian territory. Not expected to operate beyond Iranian airspace cover. Largely ceremonial deterrent value.',
    },
  ],
}

const IR_AIRDEFENSE: UnitGroup = {
  name: 'Iranian Integrated Air Defense System (IADS)',
  icon: <Radio size={13} />,
  units: [
    {
      designation: 'Bavar-373',
      type: 'Domestic S-300 equivalent (SAM)',
      qty: '2 batteries fully operational',
      location: 'Tehran perimeter, Alborz approaches',
      status: 'DEGRADED',
      notes: '6 of 8 batteries destroyed or severely degraded by US/Israeli SEAD operations Days 1–3 (AGM-88 HARM, JASSM-ER). 2 batteries retain limited coverage. Radar emissions sporadic to avoid targeting.',
      source: 'ISW, 18 Mar 2026',
      sourceUrl: 'https://understandingwar.org/',
    },
    {
      designation: 'Khordad-15 (3rd Khordad)',
      type: 'Medium-range SAM',
      qty: '5 batteries operational',
      location: 'Dispersed: Gulf coast, Bushehr, Isfahan, Tehran S.',
      status: 'DEGRADED',
      notes: 'Range 75km, altitude 30km. 3 batteries destroyed. Demonstrated capability (downed US RQ-4 June 2019). Operating under strict EMCON to reduce targetability.',
    },
    {
      designation: 'Tor-M1 / Pantsir-S1',
      type: 'Short-range SAM / SHORAD',
      qty: '~10 systems remaining',
      location: 'Point defense of key nodes',
      status: 'OPERATIONAL',
      notes: 'SHORAD for nuclear sites, regime HQ, IRGCAF bases. Russian Tor-M1 (range 12km) and domestically modified Pantsir copies. Limited effectiveness against F-35 low-observable profiles.',
    },
  ],
}

const IR_PROXY: UnitGroup = {
  name: 'Proxy / Partner Forces (Axis of Resistance)',
  icon: <Globe size={13} />,
  units: [
    {
      designation: 'Houthi Forces (Yemen)',
      type: 'IRGC Proxy — Ansarallah',
      location: 'Western Yemen (Red Sea coast)',
      status: 'OPERATIONAL',
      notes: 'Quds-1 cruise missiles (6 fired Day 16 at 5th Fleet); 5 intercepted. Remaining ASCM stock estimated 40–60. Houthi UAVs (Samad-3) continuing Red Sea attacks. CVN-71 detering further launches.',
      source: 'Reuters, 17 Mar 2026',
      sourceUrl: 'https://reuters.com/world/middle-east/',
    },
    {
      designation: 'Kata\'ib Hezbollah (Iraq)',
      type: 'IRGC Proxy — Iraq',
      location: 'Western Iraq (Anbar, Baghdad)',
      status: 'OPERATIONAL',
      notes: 'Small-UAS (Qasef-1/Shahada) swarm against Al Asad AB Day 14 — 2 helicopters damaged. Occasional rocket/mortar attacks on US forces in Baghdad. Escalation held below US retaliatory threshold.',
    },
    {
      designation: 'Hezbollah (Lebanon)',
      type: 'IRGC Strategic Proxy',
      location: 'Southern Lebanon',
      status: 'OPERATIONAL',
      notes: 'Conducting cross-border fires into northern Israel (Kornet ATGMs, 122mm rockets) but holding back major escalation (Precision Guided Munitions reserve, Radwan SOF). 100,000+ rocket/missile inventory intact. Strategic deterrent vs. ground invasion.',
      source: 'Haaretz, 19 Mar 2026',
      sourceUrl: 'https://www.haaretz.com/',
    },
  ],
}

export default async function OrbatPage() {
  // Fetch live ORBAT updates from Supabase
  interface LiveOrbatUpdate {
    id: number; unit_id: string; unit_name: string; faction: string
    status: string; location: string; notes: string; confidence: number; created_at: string
  }
  let liveOrbatUpdates: LiveOrbatUpdate[] = []
  try {
    const sb = await createServerClient()
    if (sb) {
      const since = new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString()
      const { data } = await sb
        .from('orbat_updates')
        .select('*')
        .gte('created_at', since)
        .order('created_at', { ascending: false })
        .limit(15)
      liveOrbatUpdates = (data ?? []) as LiveOrbatUpdate[]
    }
  } catch { /* non-fatal */ }
  return (
    <div className="max-w-screen-xl space-y-5">

      {/* Live intelligence feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TheaterIntelFeed theater="Air" limit={12} />
        <LiveNewsBoard limit={15} warFilter={true} compact={false} />
      </div>

      {/* Back nav */}
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-[10px] text-zinc-500 hover:text-emerald-400 tracking-widest uppercase transition-colors"
      >
        <ArrowLeft size={11} /> Command Overview
      </Link>

      {/* ── Cinematic ORBAT Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(239,68,68,0.012) 2px, rgba(239,68,68,0.012) 4px)'}} />
          <div className="relative z-[3]">
            <div className="flex items-start gap-3">
              <div className="relative">
                <AlertTriangle size={22} className="text-red-400 animate-pulse drop-shadow-[0_0_8px_rgba(239,68,68,0.5)] shrink-0 mt-0.5" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-400 rounded-full animate-pulse" />
              </div>
              <div>
                <p className="text-[9px] tracking-[0.2em] text-red-400 uppercase mb-1">
                  UNCLASSIFIED // AI-SYNTHESIZED ORDER OF BATTLE // OPEN-SOURCE ANALYSIS
                </p>
                <h1 className="text-lg font-bold tracking-widest text-zinc-200 glow-red uppercase">
                  Order of Battle — Operation Epic Fury
                </h1>
                <p className="text-xs text-zinc-500 tracking-widest mt-1">
                  AS OF: {toDTG(CONFLICT_DAY)} (Day {CONFLICT_DAY}) &nbsp;|&nbsp; Source: J2 Intel Cell, CENTCOM FWD
                </p>
              </div>
              <div className="ml-auto on-air-badge inline-block bg-red-900/60 text-red-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-red-800/60 shrink-0">
                ● ORBAT LIVE
              </div>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-zinc-900">
              <p className="text-[9px] text-zinc-600 tracking-widest uppercase">Status Legend:</p>
              {(['OPERATIONAL', 'DEGRADED', 'DESTROYED', 'UNKNOWN'] as UnitStatus[]).map((s) =>
                <React.Fragment key={s}>{statusBadge(s)}</React.Fragment>
              )}
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" style={{background: 'linear-gradient(90deg, #dc2626 0%, #991b1b 50%, #450a0a 100%)'}} />
      </div>

      {/* Two-column layout: US (green) vs Iran (red) */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ── US CENTCOM ── */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <div className="h-px flex-1 bg-emerald-900" />
            <h2 className="text-[10px] font-bold tracking-[0.3em] text-emerald-400 uppercase px-2">
              US CENTCOM / Coalition Forces
            </h2>
            <div className="h-px flex-1 bg-emerald-900" />
          </div>
          <UnitTable group={US_NAVAL}     side="us" />
          <UnitTable group={US_AIR}       side="us" />
          <UnitTable group={US_GROUND}    side="us" />
          <UnitTable group={US_COALITION} side="us" />
        </div>

        {/* ── IRAN / IRGC ── */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <div className="h-px flex-1 bg-red-900" />
            <h2 className="text-[10px] font-bold tracking-[0.3em] text-red-400 uppercase px-2">
              Islamic Republic of Iran / IRGC Forces
            </h2>
            <div className="h-px flex-1 bg-red-900" />
          </div>
          <UnitTable group={IR_LEADERSHIP} side="ir" />
          <UnitTable group={IR_NAVAL}      side="ir" />
          <UnitTable group={IR_AEROSPACE}  side="ir" />
          <UnitTable group={IR_AIRFORCE}   side="ir" />
          <UnitTable group={IR_AIRDEFENSE} side="ir" />
          <UnitTable group={IR_PROXY}      side="ir" />
        </div>
      </div>

      {/* Assessment footer — cinematic */}
      <div className="video-feed-frame tac-card p-5 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
          <span className="text-[7px] text-amber-500/60 font-bold tracking-[0.2em]">ASSESSMENT</span>
        </div>
        <h2 className="text-[10px] font-bold tracking-widest text-zinc-400 uppercase border-b border-zinc-800 pb-2 relative z-[1] glow-amber">
          Overall Assessment — Day {CONFLICT_DAY}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[10px] text-zinc-500 leading-relaxed">
          <div>
            <p className="font-bold text-emerald-400 uppercase tracking-widest mb-1">US Advantage</p>
            <p>Air superiority achieved in target areas. Naval strike power substantially intact — surface screen operational. Special operations ongoing in Hormuz. Missile defense has intercepted ~85% of Iranian BM barrages.</p>
          </div>
          <div>
            <p className="font-bold text-amber-400 uppercase tracking-widest mb-1">Contested Domains</p>
            <p>Hormuz Strait remains mined/blocked — MCM operations ongoing. IRGC drone/ASCM threat to surface assets persists. Iranian cyber operations targeting Gulf infrastructure active. Residual IADS in Zagros/Tehran.</p>
          </div>
          <div>
            <p className="font-bold text-red-400 uppercase tracking-widest mb-1">Iranian Capability</p>
            <p>Ballistic missile stocks ~92-95% depleted (post-Alpha-5 D26 — five barrages complete). IADS critically degraded. IRIAF barely operational. CRITICAL: Supreme Leader Khamenei KIA Day 22 — national command authority decapitated; IRGC CINC Salami assumed unilateral command D23. Hormuz: PARTIAL TRANSIT underway, MCM ZB-Alpha 78% cleared, GOLF-7 INACTIVE D26. CEASEFIRE: COMPASS 68% within 72h — Abu Dhabi proximity talks active. Proxy network (Hezbollah, Houthis, KH) intact. 6th barrage risk 41%. Unpredictable escalation risk ELEVATED.</p>
          </div>
        </div>
        <div className="pt-3 border-t border-zinc-900 text-[9px] text-zinc-700 tracking-wide">
          Sources: ISW Iran Campaign Assessment | USNI News | Janes Defence | RAND Corporation Iran Military Review |
          Bellingcat open-source verification | CENTCOM press releases |{' '}
          <a href="https://understandingwar.org/" target="_blank" rel="noopener noreferrer" className="hover:text-zinc-500 underline">ISW</a>{' '}
          <a href="https://news.usni.org/" target="_blank" rel="noopener noreferrer" className="hover:text-zinc-500 underline">USNI</a>{' '}
          <a href="https://www.janes.com/" target="_blank" rel="noopener noreferrer" className="hover:text-zinc-500 underline">Janes</a>{' '}
          <a href="https://www.bellingcat.com/" target="_blank" rel="noopener noreferrer" className="hover:text-zinc-500 underline">Bellingcat</a>
        </div>
      </div>

      {/* Live AI ORBAT updates from Supabase */}
      {liveOrbatUpdates.length > 0 && (
        <div className="video-feed-frame tac-card border-emerald-900/60 bg-emerald-950/5 p-5 space-y-3 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-emerald-500/60 font-bold tracking-[0.2em]">NEXUS AI</span>
          </div>
          <div className="tac-section-header mb-3 relative z-[1]">
            <Cpu size={12} className="text-emerald-500 animate-pulse drop-shadow-[0_0_4px_rgba(16,185,129,0.4)]" />
            <span className="glow-green">Live Unit Status Updates — NEXUS-AI</span>
            <span className="ml-auto text-[9px] text-emerald-600 normal-case font-normal tracking-widest">{liveOrbatUpdates.length} UPDATE{liveOrbatUpdates.length !== 1 ? 'S' : ''}</span>
          </div>
          <div className="space-y-2">
            {liveOrbatUpdates.map((u) => (
              <div key={u.id} className="flex items-start gap-3 p-2.5 bg-zinc-900/50 rounded-sm border border-zinc-800">
                <div className="flex flex-col gap-0.5 shrink-0">
                  <span className={`text-[8px] font-bold tracking-widest px-1.5 py-0.5 rounded-sm border ${
                    u.status === 'OPERATIONAL' ? 'text-emerald-400 border-emerald-800 bg-emerald-950/40' :
                    u.status === 'DEGRADED'    ? 'text-amber-400 border-amber-800 bg-amber-950/40' :
                    u.status === 'DESTROYED'   ? 'text-red-400 border-red-800 bg-red-950/40' :
                    'text-zinc-500 border-zinc-700 bg-zinc-900/40'
                  }`}>{u.status}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-0.5">
                    <span className="text-[9px] font-bold text-zinc-300 tracking-wider">{u.unit_name}</span>
                    <span className="text-[7px] text-zinc-600">{u.faction}</span>
                    {u.location && <span className="text-[7px] text-zinc-600">▶ {u.location}</span>}
                    {u.confidence > 0 && <span className="text-[7px] text-zinc-700 ml-auto">{u.confidence}% conf.</span>}
                    <Cpu size={7} className="text-emerald-700" />
                  </div>
                  {u.notes && <p className="text-[9px] text-zinc-500 leading-relaxed">{u.notes}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
