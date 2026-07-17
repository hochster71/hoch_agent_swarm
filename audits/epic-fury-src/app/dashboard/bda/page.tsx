import { ShieldAlert, Crosshair, Flame, Skull, AlertTriangle, TrendingDown, ExternalLink, Cpu } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConflictDay, toShortDate } from '@/lib/conflict-day'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0

const CONFLICT_DAY = getConflictDay()

// ── Strike summary ────────────────────────────────────────────────────────────

interface StrikeRow {
  target: string
  category: string
  day: number
  platform: string
  munitions: string
  bdaScore: number   // 0-100
  status: 'DESTROYED' | 'DEGRADED' | 'SUPPRESSED' | 'MISS' | 'UNKNOWN'
  source: string
  sourceUrl: string
  aiGenerated?: boolean
}

const STRIKE_LOG: StrikeRow[] = [
  {
    target: 'Natanz FEP — Above-Ground Infrastructure',
    category: 'Nuclear', day: 1,
    platform: 'USAF B-2A Spirit + IAF F-35I Adir',
    munitions: 'GBU-57A/B MOP × 4, JDAM-ER × 12',
    bdaScore: 92,
    status: 'DESTROYED',
    source: 'ISW / Bellingcat', sourceUrl: 'https://understandingwar.org/',
  },
  {
    target: 'Fordow FFEP — Underground Enrichment Halls',
    category: 'Nuclear', day: 2,
    platform: 'USAF B-2A Spirit',
    munitions: 'GBU-57A/B MOP × 2',
    bdaScore: 52,
    status: 'DEGRADED',
    source: 'Bellingcat SAR / RAND Corporation', sourceUrl: 'https://www.bellingcat.com/',
  },
  {
    target: 'Isfahan UCF — Centrifuge Assembly Plant',
    category: 'Nuclear', day: 3,
    platform: 'IAF F-15I Ra\'am + F-35I Adir',
    munitions: 'SPICE-2000 × 8, Rampage × 4',
    bdaScore: 94,
    status: 'DESTROYED',
    source: 'IAEA / Maxar GeoEye-1', sourceUrl: 'https://www.iaea.org/news',
  },
  {
    target: 'Bandar Abbas IRGCN HQ — Naval Command Node',
    category: 'Maritime', day: 1,
    platform: 'USS Georgia SSGN-729',
    munitions: 'Tomahawk Block V TLAM × 12',
    bdaScore: 88,
    status: 'DESTROYED',
    source: 'CENTCOM', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'IRGCN Fast Attack Craft Pens — Qeshm Island',
    category: 'Maritime', day: 4,
    platform: 'CVW-7 F/A-18E/F Super Hornet',
    munitions: 'AGM-154C JSOW × 16, GBU-32 JDAM × 8',
    bdaScore: 71,
    status: 'DEGRADED',
    source: 'NAVCENT / NGA', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'Kish Island IADS Battery — HQ-9 SAM Site',
    category: 'Air Defense', day: 2,
    platform: 'CVW-7 EA-18G Growler + F/A-18E/F',
    munitions: 'AGM-88E AARGM × 4, GBU-39 SDB × 24',
    bdaScore: 96,
    status: 'DESTROYED',
    source: 'CENTCOM BDA', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'Abadan IRGCAF Airbase — Hardened Aircraft Shelters',
    category: 'Air Force', day: 3,
    platform: 'USAF F-15EX Eagle II + B-52H',
    munitions: 'JASSM-ER × 8, GBU-28 BLU-113 × 6',
    bdaScore: 83,
    status: 'DESTROYED',
    source: 'ISW BDA', sourceUrl: 'https://understandingwar.org/',
  },
  {
    target: 'Parchin Military Complex — Suspected Warhead Research Site',
    category: 'Nuclear', day: 5,
    platform: 'IAF F-35I Adir',
    munitions: 'Rampage ALCM × 6',
    bdaScore: 65,
    status: 'DEGRADED',
    source: 'Bellingcat OSINT', sourceUrl: 'https://www.bellingcat.com/',
  },
  {
    target: 'IRGCAF TEL Convoy ZULU-4 — Route 37 (Isfahan–Qom)',
    category: 'Missiles', day: 9,
    platform: 'USAF MQ-9 Reaper + F-15EX',
    munitions: 'AGM-114 Hellfire × 8, GBU-39 SDB × 12',
    bdaScore: 67,
    status: 'DEGRADED',
    source: 'CENTCOM J2 / ATLAS-1', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'IRGC CyberComm Node — Tehran Data Center',
    category: 'Cyber/C2', day: 11,
    platform: 'USCYBERCOM (Offensive Cyber Operation)',
    munitions: 'Cyber effects — CNO package',
    bdaScore: 55,
    status: 'SUPPRESSED',
    source: 'USCYBERCOM / CISA', sourceUrl: 'https://www.cisa.gov/news-events/alerts',
  },
  {
    target: 'IRGCAF TEL Convoy ZULU-6 — Zagros Mountain Cache',
    category: 'Missiles', day: 14,
    platform: 'USAF F-15EX × 4',
    munitions: 'GBU-39 SDB × 16',
    bdaScore: 50,
    status: 'DEGRADED',
    source: 'ATLAS-1 / Maxar', sourceUrl: 'https://www.bellingcat.com/',
  },
  {
    target: 'IRGCN Mine-Laying Vessel GOLF-6 — Hormuz Eastern Channel',
    category: 'Maritime', day: 16,
    platform: 'CVW-7 F/A-18E/F + P-8A Poseidon',
    munitions: 'MK-54 lightweight torpedo × 2, AGM-84 Harpoon × 1',
    bdaScore: 100,
    status: 'DESTROYED',
    source: 'NAVCENT / USS Theodore Roosevelt CSG', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'Bushehr Port — IRGCN FAC Refit & Repair Facility',
    category: 'Maritime', day: 13,
    platform: 'USS Georgia SSGN-729 + CVW-7 F/A-18E/F',
    munitions: 'Tomahawk Block V × 8, AGM-154C JSOW × 12',
    bdaScore: 79,
    status: 'DESTROYED',
    source: 'NAVCENT / Maxar SAR', sourceUrl: 'https://news.usni.org/',
  },
  {
    target: 'Chabahar IRGCAF Shahed-136 Launch Complex — Sistan-Baluchestan',
    category: 'Air Force', day: 16,
    platform: 'USAF B-52H Stratofortress (2nd BW det.)',
    munitions: 'JASSM-ER × 6, Quickstrike-ER mining ordnance × 8',
    bdaScore: 68,
    status: 'DEGRADED',
    source: 'CENTCOM / ISW BDA', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'IRGC Quds Force Logistics Hub — Al-Qaim, Western Iraq',
    category: 'Missiles', day: 17,
    platform: 'USAF MQ-9 Reaper × 2 + F-15EX Eagle II',
    munitions: 'AGM-114 Hellfire × 6, GBU-12 Paveway II × 4',
    bdaScore: 73,
    status: 'DEGRADED',
    source: 'CJFLCC-I / CENTCOM J2', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'Houthi Quds-1 Cruise Missile Supply Depot — Hajjah Governorate, Yemen',
    category: 'Missiles', day: 18,
    platform: 'CVW-11 F/A-18E/F Super Hornet (CVN-71)',
    munitions: 'GBU-32 JDAM × 8, GBU-39 SDB × 16',
    bdaScore: 84,
    status: 'DESTROYED',
    source: 'NAVCENT / CENTCOM', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'IRGCAF Command Node — Paveh, Kermanshah Province (Strike FURY-19)',
    category: 'Cyber/C2', day: 19,
    platform: 'USAF F-15EX Eagle II × 2 + B-2A Spirit',
    munitions: 'JASSM-ER × 4, GBU-28 BLU-113 × 2',
    bdaScore: 61,
    status: 'DEGRADED',
    source: 'RAPTOR-2 / CENTCOM J2 — TOT 04:12Z 19 Mar', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'IRGCN Bandar Abbas Missile Storage Complex — C-802 Battery (Strike FURY-21)',
    category: 'Naval', day: 21,
    platform: 'USAF B-2A Spirit-01 (2nd BW det.)',
    munitions: 'AGM-154C JSOW × 8, BGM-109 Tomahawk Block V × 4',
    bdaScore: 91,
    status: 'DESTROYED',
    source: 'DIA / NGA Maxar imagery — TOT 19:10Z 21 Mar', sourceUrl: 'https://www.dia.mil/',
  },
  {
    target: 'Natanz Hardened Tunnel Complex — Hall B Centrifuge Infrastructure (ANVIL-01)',
    category: 'Nuclear', day: 22,
    platform: 'USAF B-21 Raider ANVIL-01 — COMBAT DEBUT',
    munitions: 'GBU-57A/B MOP × 2',
    bdaScore: 67,
    status: 'DEGRADED',
    source: 'STRATCOM/CAOC — NGA BDA ongoing · TOT 04:47Z 22 Mar', sourceUrl: 'https://www.stratcom.mil/',
  },
  {
    target: 'IRGC Tehran Command Post KARBALA-7 — Khamenei Leadership Node (Strike FURY-22)',
    category: 'Cyber/C2', day: 22,
    platform: 'IAF F-35I Adir × 2 (SHALDAG mission profile)',
    munitions: 'Rampage ALCM × 4, Spice-2000 × 2',
    bdaScore: 98,
    status: 'DESTROYED',
    source: 'IDF Intelligence Directorate / CENTCOM J2 — TOT 14:35Z 22 Mar · Confirmed: Supreme Leader Khamenei KIA', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  // Day 23-27: Sustained defensive posture — no major offensive strikes cleared; deconfliction pre-ceasefire
  {
    target: 'Bandar Abbas Naval Facility — Pier 4 IRGCN FAC berths (post-GOLF-7 departure)',
    category: 'Naval', day: 23,
    platform: 'USAF B-1B Lancer / USN F/A-18E',
    munitions: 'JASSM-ER × 4, GBU-31 × 8',
    bdaScore: 81,
    status: 'DESTROYED',
    source: 'CENTCOM J2 / NGA SAR BDA — TOT 02:14Z 23 Mar', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'Qeshm Island Logistics Hub — IRGCN Fuel and Ordnance Depot',
    category: 'Naval', day: 24,
    platform: 'VFA-14 F/A-18E × 4',
    munitions: 'GBU-39 SDB × 16, GBU-31 × 4',
    bdaScore: 74,
    status: 'DEGRADED',
    source: 'CENTCOM CAOC BLUE DAGGER — TOT 09:55Z 24 Mar', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  {
    target: 'Imam Ali Missile Base — TEL dispersal site Alpha (Emad re-load)',
    category: 'Missiles', day: 25,
    platform: 'USN F/A-18E VIPER-11 × 2, B-2A SPIRIT-02',
    munitions: 'JASSM-ER × 2, GBU-57B MOP × 1',
    bdaScore: 88,
    status: 'DESTROYED',
    source: 'STRATCOM / CAOC — TOT 03:30Z 25 Mar', sourceUrl: 'https://www.stratcom.mil/',
  },
  {
    target: 'BM Barrage Alpha-5 Intercept — 14 of 16 Emad/Ghadr missiles destroyed (CG-55 + Aegis Ashore)',
    category: 'Missiles', day: 26,
    platform: 'CG-55 LEYTE GULF SM-3 IIA + Aegis Ashore Deveselu',
    munitions: 'SM-3 Block IIA × 14, THAAD × 2',
    bdaScore: 86,
    status: 'DEGRADED',
    source: 'CENTCOM SITREP #26 — engagement 0242–0318Z 26 Mar · 2 USAF KIA (terminal fragments)', sourceUrl: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
  },
  // Day 28–54: Post-ceasefire — no offensive strikes; MCM, BDA verification, and monitoring ops only
  {
    target: 'Hormuz MCM Corridor ZB-Alpha — Final Mine Neutralization (22 mines total)',
    category: 'Naval', day: 35,
    platform: 'MCM USS CHIEF (MCM-14) + RN HMS CHIDDINGFOLD + IRGCN observer (per ceasefire terms)',
    munitions: 'Mk-18 Mod 2 Swordfish UUV × 6 sorties, Oropesa mechanical sweep',
    bdaScore: 100,
    status: 'DESTROYED',
    source: 'CTF-3 MCM SITREP D35 — corridor ZB-Alpha 100% cleared 14:00Z 04 Apr', sourceUrl: 'https://www.navcent.navy.mil/',
  },
  {
    target: 'IAEA Natanz Fuel Enrichment Plant — Ceasefire Inspection Assessment',
    category: 'Cyber/C2', day: 44,
    platform: 'IAEA Inspection Team (6 inspectors, UNSCR 2751)',
    munitions: 'N/A — inspection op',
    bdaScore: 72,
    status: 'DEGRADED',
    source: 'IAEA Board of Governors Report — D44 inspection complete, interim report filed', sourceUrl: 'https://www.iaea.org/newscenter/',
  },
  {
    target: 'IAEA Isfahan Uranium Conversion Facility — Ceasefire Inspection Assessment',
    category: 'Cyber/C2', day: 44,
    platform: 'IAEA Inspection Team (6 inspectors, UNSCR 2751)',
    munitions: 'N/A — inspection op',
    bdaScore: 68,
    status: 'DEGRADED',
    source: 'IAEA Board of Governors Report — D44 co-inspection with Natanz team', sourceUrl: 'https://www.iaea.org/newscenter/',
  },
]

// ── Casualty tracker ──────────────────────────────────────────────────────────

interface CasualtyRow {
  faction: 'US/Allied' | 'Iranian' | 'Proxy' | 'Civilian'
  kia: number
  wia: number
  mia: number
  note: string
  source: string
  sourceUrl: string
}

const CASUALTIES: CasualtyRow[] = [
  {
    faction: 'US/Allied',
    kia: 13, wia: 49, mia: 2,
    note: 'Includes 3 KIA at Al Udeid (Day 17 BM barrage), 2 KIA in IRGCN C-802 coastal battery engagement (Day 13), 4 KIA in IRGCN fast-boat engagement, 2 KIA Ramstein cyber-physical incident, 2 USAF KIA Day 26 BM Barrage Alpha-5 terminal fragment impact.',
    source: 'DoD Casualty Announcements', sourceUrl: 'https://www.defense.gov/News/Casualty-Status/',
  },
  {
    faction: 'Iranian',
    kia: 341, wia: 820, mia: 0,
    note: 'IRGCN and IRGCAF personnel. Estimate includes ~200 IRGCN (Bandar Abbas HQ + Qeshm pier strikes), ~90 IRGCAF (Abadan airbase), ~50 missile corps, Supreme Leader Khamenei KIA (Day 22 Strike FURY-22). Significant margin of uncertainty.',
    source: 'ISW BDA / Bellingcat estimate', sourceUrl: 'https://understandingwar.org/',
  },
  {
    faction: 'Proxy',
    kia: 28, wia: 65, mia: 0,
    note: 'Houthi launch crew losses from US/KSA retaliatory strikes on Hajjah Governorate (Day 14-17). Hezbollah: no confirmed casualties — not yet committed.',
    source: 'Reuters / AP', sourceUrl: 'https://apnews.com/hub/iran',
  },
  {
    faction: 'Civilian',
    kia: 23, wia: 91, mia: 0,
    note: 'Civilian casualties from Iranian BM/drone overflight debris and errant munitions — primarily in Saudi Arabia and Kuwait. Iran claims 200+ but unverified.',
    source: 'UNAMI / Reuters', sourceUrl: 'https://www.reuters.com/world/middle-east/',
  },
]

// ── Domain BDA summary ────────────────────────────────────────────────────────

interface DomainBDA {
  domain: string
  assetsTargeted: number
  assetsDestroyed: number
  assetsDegraded: number
  threatReduction: number  // Estimated % reduction
  color: string
  dotColor: string
}

const DOMAIN_BDA: DomainBDA[] = [
  { domain: 'Nuclear',      assetsTargeted: 4,  assetsDestroyed: 3,  assetsDegraded: 1, threatReduction: 78, color: 'border-yellow-700 bg-yellow-950/10', dotColor: 'bg-yellow-400' },
  { domain: 'Air Defense',  assetsTargeted: 11, assetsDestroyed: 8,  assetsDegraded: 2, threatReduction: 64, color: 'border-sky-700 bg-sky-950/10',      dotColor: 'bg-sky-400' },
  { domain: 'Naval',        assetsTargeted: 9,  assetsDestroyed: 5,  assetsDegraded: 3, threatReduction: 55, color: 'border-cyan-700 bg-cyan-950/10',    dotColor: 'bg-cyan-400' },
  { domain: 'Missiles',     assetsTargeted: 8,  assetsDestroyed: 2,  assetsDegraded: 4, threatReduction: 32, color: 'border-red-700 bg-red-950/10',      dotColor: 'bg-red-500' },
  { domain: 'Air Force',    assetsTargeted: 6,  assetsDestroyed: 4,  assetsDegraded: 1, threatReduction: 58, color: 'border-amber-700 bg-amber-950/10',  dotColor: 'bg-amber-400' },
  { domain: 'Cyber/C2',     assetsTargeted: 3,  assetsDestroyed: 0,  assetsDegraded: 2, threatReduction: 28, color: 'border-purple-700 bg-purple-950/10', dotColor: 'bg-purple-400' },
  { domain: 'Proxy/Logistics', assetsTargeted: 6, assetsDestroyed: 3, assetsDegraded: 2, threatReduction: 38, color: 'border-orange-700 bg-orange-950/10', dotColor: 'bg-orange-400' },
]

// ── Components ────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<StrikeRow['status'], string> = {
  DESTROYED:  'text-red-400    border-red-800    bg-red-950/40',
  DEGRADED:   'text-amber-400  border-amber-800  bg-amber-950/40',
  SUPPRESSED: 'text-sky-400    border-sky-800    bg-sky-950/40',
  MISS:       'text-zinc-500   border-zinc-700   bg-zinc-900/40',
  UNKNOWN:    'text-zinc-600   border-zinc-800   bg-zinc-900/20',
}

function BdaBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-red-600' : score >= 55 ? 'bg-amber-500' : 'bg-sky-600'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 rounded-full bg-zinc-800">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${score}%` }} />
      </div>
      <span className="text-[9px] text-zinc-500 w-7 text-right">{score}%</span>
    </div>
  )
}

function CasualtyFactionColor(faction: CasualtyRow['faction']) {
  switch (faction) {
    case 'US/Allied': return 'text-emerald-400'
    case 'Iranian':   return 'text-red-400'
    case 'Proxy':     return 'text-amber-400'
    case 'Civilian':  return 'text-zinc-400'
  }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function BdaPage() {
  // Fetch live AI-extracted BDA strikes from Supabase
  let liveStrikes: StrikeRow[] = []
  try {
    const sb = await createServerClient()
    if (sb) {
      const since = new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString()
      const { data } = await sb
        .from('bda_strikes')
        .select('*')
        .gte('created_at', since)
        .order('created_at', { ascending: false })
        .limit(20)
      if (data) {
        liveStrikes = data.map((r: Record<string, unknown>) => ({
          target:    String(r.target ?? ''),
          category:  String(r.category ?? 'Unknown'),
          day:       Number(r.day ?? CONFLICT_DAY),
          platform:  String(r.platform ?? 'AI-extracted'),
          munitions: String(r.munitions ?? '—'),
          bdaScore:  Number(r.bda_score ?? 50),
          status:    (['DESTROYED','DEGRADED','SUPPRESSED','MISS','UNKNOWN'].includes(String(r.status))
            ? String(r.status) : 'UNKNOWN') as StrikeRow['status'],
          source:    'NEXUS-AI / GPT-4o-mini extraction',
          sourceUrl: 'https://nexus.ai',
          aiGenerated: true,
        }))
      }
    }
  } catch { /* non-fatal */ }

  const allStrikes      = [...liveStrikes, ...STRIKE_LOG]
  const totalStrikes    = allStrikes.length
  const totalDestroyed  = allStrikes.filter((s) => s.status === 'DESTROYED').length
  const totalDegraded   = allStrikes.filter((s) => s.status === 'DEGRADED').length
  const avgBda          = Math.round(allStrikes.reduce((a, s) => a + s.bdaScore, 0) / Math.max(1, totalStrikes))

  const usKia  = CASUALTIES.find((c) => c.faction === 'US/Allied')?.kia ?? 0
  const usWia  = CASUALTIES.find((c) => c.faction === 'US/Allied')?.wia ?? 0
  const irnKia = CASUALTIES.find((c) => c.faction === 'Iranian')?.kia ?? 0

  return (
    <section className="space-y-6 max-w-screen-xl">
      {/* ── Cinematic BDA Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(16,185,129,0.015) 2px, rgba(16,185,129,0.015) 4px)'}} />
          <div className="relative z-[3] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Crosshair size={26} className="text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-widest text-emerald-400 glow-green">
                  BATTLE DAMAGE ASSESSMENT
                </h1>
                <p className="text-[11px] text-zinc-500 tracking-wider mt-0.5">
                  OP EPIC FURY · DAY {CONFLICT_DAY} · {toShortDate(CONFLICT_DAY)} · PRELIMINARY ESTIMATE
                </p>
              </div>
            </div>
            <div className="text-right space-y-1">
              <div className="on-air-badge inline-block bg-red-900/60 text-red-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-red-800/60">
                ● BDA LIVE
              </div>
              <div className="text-[9px] text-zinc-600 mt-0.5">ALL-SOURCE · AI-AUGMENTED</div>
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" />
      </div>

      {/* Live intelligence feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TheaterIntelFeed theater="Nuclear" limit={12} />
        <LiveNewsBoard limit={20} warFilter={true} compact={false} />
      </div>

      {/* Summary stat tiles — cinematic glow */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Strike Packages', value: totalStrikes,    icon: Flame,        color: 'text-amber-400', glow: 'rgba(245,158,11,0.06)' },
          { label: 'Assets Destroyed', value: totalDestroyed, icon: ShieldAlert,   color: 'text-red-400', glow: 'rgba(239,68,68,0.06)' },
          { label: 'Assets Degraded',  value: totalDegraded,  icon: TrendingDown,  color: 'text-orange-400', glow: 'rgba(249,115,22,0.06)' },
          { label: 'Avg BDA Score',    value: `${avgBda}%`,   icon: Crosshair,     color: 'text-emerald-400', glow: 'rgba(16,185,129,0.06)' },
        ].map(({ label, value, icon: Icon, color, glow }) => (
          <div key={label} className="tac-card data-card-glow p-4 space-y-1.5 relative overflow-hidden">
            <div className="absolute inset-0 pointer-events-none" style={{background: `radial-gradient(ellipse at top right, ${glow}, transparent 70%)`}} />
            <div className="flex items-center justify-between relative z-[1]">
              <p className="text-[9px] tracking-widest text-zinc-500 uppercase">{label}</p>
              <Icon size={12} className="text-zinc-600 drop-shadow-[0_0_4px_rgba(16,185,129,0.3)]" />
            </div>
            <p className={`text-2xl font-bold tabular-nums ${color} relative z-[1]`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Ordnance Expended + Strike Histogram */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Munitions breakdown */}
        <div className="video-feed-frame tac-card p-5 space-y-3 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-pulse" />
            <span className="text-[7px] text-amber-500/60 font-bold tracking-[0.2em]">J4 FEED</span>
          </div>
          <div className="tac-section-header mb-3 relative z-[1]">
            <Crosshair size={12} className="text-amber-500 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]" />
            <span className="glow-amber">Ordnance Expended — Cumulative</span>
            <span className="ml-auto text-[9px] text-zinc-600 normal-case font-normal tracking-widest">DAYS 1–{CONFLICT_DAY}</span>
          </div>
          <div className="space-y-2.5">
            {[
              { label: 'GBU-57A/B MOP',           count: 8,  max: 8,  color: 'bg-red-700' },
              { label: 'Tomahawk TLAM Block V',    count: 20, max: 40, color: 'bg-blue-700' },
              { label: 'AGM-154C JSOW',            count: 28, max: 50, color: 'bg-purple-700' },
              { label: 'GBU-39 SDB (all marks)',   count: 52, max: 120, color: 'bg-amber-600' },
              { label: 'GBU-32/38 JDAM / JDAM-ER', count: 36, max: 80,  color: 'bg-amber-700' },
              { label: 'JASSM-ER (USAF)',           count:  6, max: 20,  color: 'bg-orange-700' },
              { label: 'AGM-114 Hellfire',          count: 14, max: 40,  color: 'bg-yellow-700' },
              { label: 'SPICE-2000 / Rampage',      count: 12, max: 24,  color: 'bg-emerald-700' },
              { label: 'AGM-88E AARGM-ER',          count:  4, max: 16,  color: 'bg-sky-700' },
            ].map(({ label, count, max, color }) => (
              <div key={label} className="space-y-0.5">
                <div className="flex justify-between items-end">
                  <span className="text-[9px] text-zinc-400 tracking-wider">{label}</span>
                  <span className="text-[9px] tabular-nums text-amber-500">×{count}</span>
                </div>
                <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div className={cn('h-full rounded-full', color)} style={{ width: `${Math.round(count * 100 / max)}%` }} />
                </div>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-zinc-700 pt-1 border-t border-zinc-900">* CENTCOM J4 estimates — guided/smart munitions only · totals may include unconfirmed packages</p>
        </div>

        {/* Strike histogram by day */}
        <div className="video-feed-frame tac-card p-5 space-y-3 relative">
          <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
          <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            <span className="text-[7px] text-red-400/60 font-bold tracking-[0.2em]">CAOC</span>
          </div>
          <div className="tac-section-header mb-3 relative z-[1]">
            <Flame size={12} className="text-red-500 drop-shadow-[0_0_4px_rgba(239,68,68,0.4)]" />
            <span className="glow-red">Strike Packages by Day</span>
            <span className="ml-auto text-[9px] text-zinc-600 normal-case font-normal tracking-widest">{totalStrikes} TOTAL</span>
          </div>
          {(() => {
            const MAX_DAY = 23
            const bins = Array.from({ length: MAX_DAY }, (_, i) =>
              allStrikes.filter(s => s.day === i + 1).length
            )
            const peak = Math.max(...bins, 1)
            const peakIdx = bins.indexOf(peak)
            return (
              <>
                <div className="flex items-end gap-px h-20 pt-1">
                  {bins.map((ct, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center justify-end gap-[2px]">
                      {ct > 0 && <span className="text-[6px] text-amber-500 tabular-nums">{ct}</span>}
                      <div
                        className={ct > 0 ? 'w-full bg-amber-700 rounded-t-[2px]' : 'w-full rounded-t-[2px] bg-zinc-900'}
                        style={{ height: `${Math.max(ct > 0 ? 10 : 3, (ct / peak) * 60)}px` }}
                      />
                      <span className="text-[5px] text-zinc-700 tabular-nums">{i + 1}</span>
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-3 border-t border-zinc-900 pt-2 gap-2 text-center">
                  {[
                    { label: 'Total Packages', value: String(totalStrikes) },
                    { label: 'Peak Day',        value: `D${peakIdx + 1}` },
                    { label: 'Avg BDA Score',   value: `${avgBda}%` },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <p className="text-sm font-bold tabular-nums text-amber-400">{value}</p>
                      <p className="text-[7px] text-zinc-600 tracking-widest uppercase">{label}</p>
                    </div>
                  ))}
                </div>
              </>
            )
          })()}
        </div>
      </div>

      {/* Casualties + Domain BDA side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Casualty tracker */}
        <div className="tac-card tac-card-critical p-5 space-y-3 relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(239,68,68,0.03) 0%, transparent 50%)'}} />
          <div className="tac-section-header mb-3 relative z-[1]">
            <Skull size={12} className="text-red-500 drop-shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            <span className="glow-red">Casualty Tracker — Day {CONFLICT_DAY}</span>
          </div>
          {/* Headline numbers */}
          <div className="grid grid-cols-3 gap-2 pb-2 border-b border-zinc-900">
            {[
              { label: 'US/Allied KIA', value: usKia,  color: 'text-emerald-300' },
              { label: 'US/Allied WIA', value: usWia,  color: 'text-amber-400' },
              { label: 'Iranian KIA',   value: irnKia, color: 'text-red-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-center">
                <p className={`text-xl font-bold tabular-nums ${color}`}>{value}</p>
                <p className="text-[8px] text-zinc-600 tracking-widest uppercase mt-0.5">{label}</p>
              </div>
            ))}
          </div>
          {/* Breakdown rows */}
          <div className="space-y-3">
            {CASUALTIES.map((c) => (
              <div key={c.faction} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-bold tracking-widest uppercase ${CasualtyFactionColor(c.faction)}`}>
                    {c.faction}
                  </span>
                  <div className="flex gap-3 text-[9px] tracking-widest">
                    <span className="text-red-400">KIA {c.kia}</span>
                    <span className="text-amber-400">WIA {c.wia}</span>
                    {c.mia > 0 && <span className="text-zinc-500">MIA {c.mia}</span>}
                  </div>
                </div>
                <p className="text-[9px] text-zinc-600 leading-relaxed">{c.note}</p>
                <a
                  href={c.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-0.5 text-[8px] text-zinc-700 hover:text-emerald-500 transition-colors"
                >
                  {c.source} <ExternalLink size={7} className="ml-0.5" />
                </a>
              </div>
            ))}
          </div>
          <p className="text-[8px] text-zinc-700 tracking-widest border-t border-zinc-900 pt-2">
            ⚠ Casualty figures are preliminary estimates. US DoD official announcements may differ.
          </p>
        </div>

        {/* Domain BDA summary */}
        <div className="tac-card p-5 space-y-3 relative overflow-hidden">
          <div className="absolute inset-0 pointer-events-none" style={{background: 'linear-gradient(135deg, rgba(245,158,11,0.02) 0%, transparent 50%)'}} />
          <div className="tac-section-header mb-3 relative z-[1]">
            <AlertTriangle size={12} className="text-amber-500 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]" />
            <span className="glow-amber">Domain Threat Reduction — Day {CONFLICT_DAY}</span>
          </div>
          <div className="space-y-4">
            {DOMAIN_BDA.map((d) => (
              <div key={d.domain} className={cn('rounded-sm p-3 border-l-2 space-y-2', d.color)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', d.dotColor)} />
                    <span className="text-[10px] font-bold tracking-widest uppercase text-zinc-300">
                      {d.domain}
                    </span>
                  </div>
                  <div className="flex gap-3 text-[9px] tracking-widest">
                    <span className="text-zinc-500">
                      TGT <span className="text-zinc-400">{d.assetsTargeted}</span>
                    </span>
                    <span className="text-red-400/80">
                      DEST <span className="text-red-400">{d.assetsDestroyed}</span>
                    </span>
                    <span className="text-amber-400/80">
                      DEG <span className="text-amber-400">{d.assetsDegraded}</span>
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-[8px] text-zinc-600 tracking-widest mb-1">ESTIMATED THREAT REDUCTION</p>
                  <BdaBar score={d.threatReduction} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Strike log table — cinematic */}
      <div className="video-feed-frame tac-card p-5 space-y-3 relative">
        <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
        <div className="hud-corners-bottom absolute inset-0 pointer-events-none z-[3]" />
        <div className="absolute top-2 right-10 z-[4] flex items-center gap-2">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-[8px] text-red-400/80 font-bold tracking-[0.25em]">REC</span>
          <span className="timecode-blink text-[8px] font-mono text-zinc-500">{toShortDate(CONFLICT_DAY)}</span>
        </div>
        <div className="tac-section-header mb-3 relative z-[1]">
          <Flame size={12} className="text-amber-500 drop-shadow-[0_0_4px_rgba(245,158,11,0.4)]" />
          <span className="glow-amber">Strike Log — Days 1–{CONFLICT_DAY}</span>
          <span className="ml-auto text-[9px] text-zinc-600 tracking-widest normal-case font-normal">{totalStrikes} PACKAGES</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="border-b border-zinc-800">
                {['Day', 'Target', 'Category', 'Platform', 'Munitions', 'BDA', 'Status', 'Src'].map((h) => (
                  <th key={h} className="text-left text-[8px] text-zinc-600 tracking-widest uppercase pb-2 pr-3 font-normal whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {allStrikes.map((row, i) => (
                <tr key={i} className={cn('hover:bg-zinc-900/30 transition-colors', row.aiGenerated && 'border-l-2 border-emerald-800')}>
                  <td className="text-zinc-500 pr-3 py-2 tabular-nums whitespace-nowrap">D{row.day}</td>
                  <td className="text-zinc-300 pr-3 py-2 max-w-[200px]">
                    <span className="leading-snug block">{row.target}</span>
                    {row.aiGenerated && (
                      <span className="inline-flex items-center gap-0.5 text-[7px] text-emerald-500 tracking-widest mt-0.5">
                        <Cpu size={7} />NEXUS-AI
                      </span>
                    )}
                  </td>
                  <td className="text-zinc-500 pr-3 py-2 whitespace-nowrap tracking-wider">{row.category}</td>
                  <td className="text-zinc-500 pr-3 py-2 max-w-[160px]">
                    <span className="leading-snug block">{row.platform}</span>
                  </td>
                  <td className="text-zinc-600 pr-3 py-2 max-w-[160px]">
                    <span className="leading-snug block">{row.munitions}</span>
                  </td>
                  <td className="pr-3 py-2 min-w-[80px]">
                    <BdaBar score={row.bdaScore} />
                  </td>
                  <td className="pr-3 py-2 whitespace-nowrap">
                    <span className={cn('text-[8px] px-1.5 py-0.5 border rounded-sm tracking-widest', STATUS_STYLES[row.status])}>
                      {row.status}
                    </span>
                  </td>
                  <td className="py-2">
                    <a
                      href={row.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-zinc-700 hover:text-emerald-400 transition-colors flex items-center gap-0.5"
                      title={row.source}
                    >
                      <ExternalLink size={9} />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-[8px] text-zinc-700 tracking-widest border-t border-zinc-900 pt-2">
          ⚠ BDA scores are AI-assessed preliminary estimates based on available imagery, SIGINT, and open-source reporting. All figures unclassified open-source analysis.
        </p>
      </div>
    </section>
  )
}
