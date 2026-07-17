import { ExternalLink, Rss, ShieldCheck, Radio } from 'lucide-react'
import type { NewsSource } from '@/lib/types'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'

/**
 * /dashboard/news  –  Verified Source Directory
 * Curated index of news organisations, official channels, and analysis outlets
 * covering the US–Iran conflict. Every link resolves to a real, publicly accessible URL.
 */

const SOURCES: NewsSource[] = [
  // ── Wire Services ──────────────────────────────────────────────────────────
  {
    id: 'reuters',
    name: 'Reuters',
    shortName: 'Reuters',
    category: 'Wire',
    description: 'Global wire service with dedicated Middle East bureau. Primary source for breaking diplomatic and military developments.',
    url: 'https://www.reuters.com/world/middle-east/',
    rssUrl: 'https://feeds.reuters.com/Reuters/worldNews',
    reliability: 'High',
  },
  {
    id: 'ap',
    name: 'Associated Press',
    shortName: 'AP',
    category: 'Wire',
    description: 'Non-profit international wire service. Rigorous two-source standard for breaking military claims.',
    url: 'https://apnews.com/hub/iran',
    rssUrl: 'https://rsshub.app/apnews/topics/iran',
    reliability: 'High',
  },
  {
    id: 'afp',
    name: 'Agence France-Presse',
    shortName: 'AFP',
    category: 'Wire',
    description: 'French international wire; strong Gulf and Tehran bureau coverage.',
    url: 'https://www.afp.com/en/news-hub',
    reliability: 'High',
  },
  // ── Broadcast & Digital ────────────────────────────────────────────────────
  {
    id: 'bbc',
    name: 'BBC World Service',
    shortName: 'BBC',
    category: 'Broadcast',
    description: 'Independent British broadcaster. Persian Service provides unique Iran-side reporting.',
    url: 'https://www.bbc.com/news/world/middle_east',
    rssUrl: 'https://feeds.bbci.co.uk/news/world/middle_east/rss.xml',
    region: 'Middle East',
    reliability: 'High',
  },
  {
    id: 'aljazeera',
    name: 'Al Jazeera English',
    shortName: 'AJE',
    category: 'Broadcast',
    description: 'Qatar-based outlet; critical for Gulf-perspective reporting and Arabic-language sourcing.',
    url: 'https://www.aljazeera.com/tag/iran/',
    rssUrl: 'https://www.aljazeera.com/xml/rss/all.xml',
    region: 'Gulf / MENA',
    reliability: 'Medium',
  },
  {
    id: 'guardian',
    name: 'The Guardian',
    shortName: 'Guardian',
    category: 'Broadcast',
    description: 'UK outlet with strong international affairs desk and Tehran correspondents.',
    url: 'https://www.theguardian.com/world/iran',
    rssUrl: 'https://www.theguardian.com/world/iran/rss',
    reliability: 'High',
  },
  {
    id: 'nyt',
    name: 'New York Times',
    shortName: 'NYT',
    category: 'Broadcast',
    description: 'In-depth investigative reporting on CENTCOM operations and US policy.',
    url: 'https://www.nytimes.com/topic/destination/iran',
    reliability: 'High',
  },
  {
    id: 'haaretz',
    name: 'Haaretz',
    shortName: 'Haaretz',
    category: 'Broadcast',
    description: 'Israeli daily of record. Critical for Israeli military perspective, IAF strike reporting, and Hezbollah/Lebanon-front analysis. Hebrew and English editions; primary source for Israeli cabinet decision-making.',
    url: 'https://www.haaretz.com/middle-east-news/iran',
    region: 'Israel / Middle East',
    reliability: 'High',
  },
  // ── Official Sources ────────────────────────────────────────────────────────
  {
    id: 'centcom',
    name: 'US Central Command',
    shortName: 'CENTCOM',
    category: 'Official',
    description: 'Official US military press releases, statements, and operational updates for the Middle East AOR.',
    url: 'https://www.centcom.mil/MEDIA/PRESS-RELEASES/',
    reliability: 'High',
  },
  {
    id: 'dod',
    name: 'US Dept. of Defense',
    shortName: 'DoD',
    category: 'Official',
    description: 'Pentagon press briefings, policy statements, and force posture announcements.',
    url: 'https://www.defense.gov/News/',
    rssUrl: 'https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=12&ContentType=1&Site=945',
    reliability: 'High',
  },
  {
    id: 'state',
    name: 'US Dept. of State',
    shortName: 'State Dept.',
    category: 'Official',
    description: 'Diplomatic cables, sanctions announcements, and official US foreign policy positions.',
    url: 'https://www.state.gov/countries-areas/iran/',
    reliability: 'High',
  },
  {
    id: 'iaea',
    name: 'International Atomic Energy Agency',
    shortName: 'IAEA',
    category: 'Official',
    description: 'Nuclear safeguards reports, inspection updates, and enrichment monitoring — primary source on Iran nuclear program.',
    url: 'https://www.iaea.org/newscenter/focus/iran',
    reliability: 'High',
  },
  {
    id: 'un',
    name: 'United Nations News',
    shortName: 'UN',
    category: 'Official',
    description: 'Security Council resolutions, Secretary-General statements, and UNSC debates.',
    url: 'https://news.un.org/en/topic/iran',
    rssUrl: 'https://news.un.org/feed/subscribe/en/news/topic/iran/feed/rss.xml',
    reliability: 'High',
  },
  // ── Analysis & Think Tanks ─────────────────────────────────────────────────
  {
    id: 'isw',
    name: 'Institute for the Study of War',
    shortName: 'ISW',
    category: 'Analysis',
    description: 'Daily campaign maps, order of battle assessments, and open-source military analysis. Widely cited by DoD.',
    url: 'https://www.understandingwar.org/',
    reliability: 'High',
  },
  {
    id: 'rand',
    name: 'RAND Corporation',
    shortName: 'RAND',
    category: 'Analysis',
    description: 'Long-form research on Iran strategy, nuclear security, and deterrence policy.',
    url: 'https://www.rand.org/topics/iran.html',
    reliability: 'High',
  },
  {
    id: 'rusi',
    name: 'RUSI',
    shortName: 'RUSI',
    category: 'Analysis',
    description: 'Royal United Services Institute. UK-based defense think tank with strong Iran/Gulf expertise.',
    url: 'https://rusi.org/',
    region: 'UK / Global',
    reliability: 'High',
  },
  {
    id: 'carnegie',
    name: 'Carnegie Endowment for International Peace',
    shortName: 'Carnegie',
    category: 'Analysis',
    description: 'Non-partisan policy analysis on Iran nuclear negotiations, sanctions, and regional deterrence.',
    url: 'https://carnegieendowment.org/',
    reliability: 'High',
  },
  {
    id: 'warontherocks',
    name: 'War on the Rocks',
    shortName: 'WOTR',
    category: 'Analysis',
    description: 'Expert commentary from former officials, strategists, and academics on US defense policy.',
    url: 'https://warontherocks.com/',
    reliability: 'High',
  },
  {
    id: 'almonitor',
    name: 'Al-Monitor',
    shortName: 'Al-Monitor',
    category: 'Analysis',
    description: 'Middle East-focused news and analysis platform. Primary source for Persian-language sourcing, Iranian domestic politics, IRGC factional analysis, and Gulf diplomatic back-channel reporting.',
    url: 'https://www.al-monitor.com/iran',
    region: 'Iran / MENA',
    reliability: 'Medium',
  },
  // ── Specialized Military ────────────────────────────────────────────────────
  {
    id: 'usni',
    name: 'USNI News',
    shortName: 'USNI',
    category: 'Specialized',
    description: 'US Naval Institute — authoritative naval and maritime operations reporting. Ship movements, fleet posture.',
    url: 'https://news.usni.org/',
    rssUrl: 'https://news.usni.org/feed',
    reliability: 'High',
  },
  {
    id: 'twz',
    name: 'The War Zone',
    shortName: 'TWZ',
    category: 'Specialized',
    description: 'Defense and aerospace reporting. Drone, missile, air strike, and electronic warfare analysis.',
    url: 'https://www.twz.com/',
    reliability: 'High',
  },
  {
    id: 'janes',
    name: "Jane's",
    shortName: 'Janes',
    category: 'Specialized',
    description: 'Authoritative defense intelligence on order of battle, weapons systems, and ORBAT assessments.',
    url: 'https://www.janes.com/',
    reliability: 'High',
  },
  {
    id: 'breakingdefense',
    name: 'Breaking Defense',
    shortName: 'Break.Def',
    category: 'Specialized',
    description: 'Defense acquisition, Pentagon policy, and US weapons programmes. Strong CENTCOM procurement coverage, F-35/B-21 operational reporting, and commentary from senior acquisition officials.',
    url: 'https://breakingdefense.com/',
    reliability: 'High',
  },
  {
    id: 'defenseone',
    name: 'Defense One',
    shortName: 'Def.One',
    category: 'Specialized',
    description: 'Atlantic Media defense publication. Interviews with SecDef, CJCS, CENTCOM/INDOPACOM leadership, and senior civilian officials. Strong on US military strategy and emerging technology.',
    url: 'https://www.defenseone.com/',
    reliability: 'High',
  },
  // ── OSINT & Open Source ────────────────────────────────────────────────────
  {
    id: 'bellingcat',
    name: 'Bellingcat',
    shortName: 'Bellingcat',
    category: 'OSINT',
    description: 'Open-source investigation collective. Geolocates imagery, tracks missile impacts and troop movements.',
    url: 'https://www.bellingcat.com/',
    reliability: 'High',
  },
  {
    id: 'acled',
    name: 'ACLED',
    shortName: 'ACLED',
    category: 'OSINT',
    description: 'Armed Conflict Location & Event Data Project. Structured dataset of all reported armed incidents.',
    url: 'https://acleddata.com/',
    reliability: 'High',
  },
  // ── Homeland Security & Intelligence ──────────────────────────────────────
  {
    id: 'cisa',
    name: 'CISA — Cybersecurity & Infrastructure Security Agency',
    shortName: 'CISA',
    category: 'Homeland',
    description: 'Primary US federal authority for critical infrastructure protection. Issues cybersecurity advisories, Emergency Directives, and the Known Exploited Vulnerabilities (KEV) catalog. Lead agency for IRGC cyber threat response.',
    url: 'https://www.cisa.gov/news-events/alerts',
    rssUrl: 'https://www.cisa.gov/cybersecurity-advisories/all.xml',
    reliability: 'High',
  },
  {
    id: 'dhs-ntas',
    name: 'DHS — National Terrorism Advisory System',
    shortName: 'DHS NTAS',
    category: 'Homeland',
    description: 'Official DHS homeland threat bulletins. Provides ELEVATED and IMMINENT public advisory levels when specific or credible threat intelligence warrants nationwide public notification.',
    url: 'https://www.dhs.gov/ntas',
    reliability: 'High',
  },
  {
    id: 'fbi-cyber',
    name: 'FBI Cyber Division & Counterterrorism',
    shortName: 'FBI',
    category: 'Homeland',
    description: 'FBI domestic cyber and counterterrorism investigations. Issues Private Industry Notifications (PINs), Flash reports, and public alerts on threat actor TTPs targeting US networks and infrastructure.',
    url: 'https://www.fbi.gov/investigate/cyber',
    reliability: 'High',
  },
  {
    id: 'nsa-cybersec',
    name: 'NSA Cybersecurity Directorate',
    shortName: 'NSA Cyber',
    category: 'Homeland',
    description: 'National Security Agency Cybersecurity Advisories (CSAs) on nation-state TTPs. Co-publishes joint advisories with CISA and FBI on IRGC, PRC, and Russian targeting of US systems.',
    url: 'https://www.nsa.gov/cybersecurity-advisories/',
    reliability: 'High',
  },
  {
    id: 'nctc',
    name: 'National Counterterrorism Center',
    shortName: 'NCTC',
    category: 'Homeland',
    description: 'ODNI-managed center fusing threat intelligence from all 18 IC agencies. Publishes unclassified threat assessments, actor profiles, and situational awareness products for homeland security partners.',
    url: 'https://www.nctc.gov/',
    reliability: 'High',
  },
  {
    id: 'odni',
    name: 'Office of the Director of National Intelligence',
    shortName: 'ODNI',
    category: 'Homeland',
    description: 'Annual Threat Assessments, Worldwide Threat Assessments, and public IC reporting on state-sponsored threats. Coordinates assessments from all 18 US intelligence community agencies.',
    url: 'https://www.dni.gov/index.php/newsroom',
    rssUrl: 'https://www.dni.gov/index.php/newsroom/rss',
    reliability: 'High',
  },
  {
    id: 'nerc',
    name: 'NERC — North American Electric Reliability Corp',
    shortName: 'NERC',
    category: 'Homeland',
    description: 'Regulatory authority for North American power grid reliability and Critical Infrastructure Protection (CIP) standards. Issues threat bulletins, grid security alerts, and mandatory security directives for all bulk electric system operators.',
    url: 'https://www.nerc.com/pa/ci/Pages/Default.aspx',
    reliability: 'High',
  },
  {
    id: 'nrc',
    name: 'NRC — Nuclear Regulatory Commission',
    shortName: 'NRC',
    category: 'Homeland',
    description: 'Regulates all 93 US commercial nuclear power facilities. Issues security orders, cyber security directives, and coordinates with DHS/FBI on physical and cyber threats to nuclear sites.',
    url: 'https://www.nrc.gov/security.html',
    reliability: 'High',
  },
  {
    id: 'fincen',
    name: 'FinCEN — Financial Crimes Enforcement Network',
    shortName: 'FinCEN',
    category: 'Homeland',
    description: 'Treasury bureau responsible for combating financial crimes. Issues advisories on IRGC sanctions evasion, cryptocurrency abuse, and terrorism financing patterns. Key source for tracking IRGC economic warfare.',
    url: 'https://www.fincen.gov/resources/advisories',
    reliability: 'High',
  },
  {
    id: 'ic3',
    name: 'IC3 — Internet Crime Complaint Center',
    shortName: 'IC3',
    category: 'Homeland',
    description: 'FBI-hosted internet crime reporting hub. Publishes annual reports, flash alerts on cyber-enabled fraud, nation-state cyber attacks, and ransomware campaigns. Primary intake mechanism for cyber crime reporting.',
    url: 'https://www.ic3.gov/',
    reliability: 'High',
  },
]

const CATEGORY_STYLES: Record<string, { label: string; border: string; badge: string; title: string }> = {
  Wire:       { label: 'Wire Services',                    border: 'border-l-amber-600',   badge: 'bg-amber-950/50 text-amber-300 border-amber-700',    title: 'text-amber-300' },
  Broadcast:  { label: 'Broadcast & Digital',              border: 'border-l-cyan-700',    badge: 'bg-cyan-950/50 text-cyan-300 border-cyan-700',       title: 'text-cyan-300' },
  Official:   { label: 'Official Sources',                  border: 'border-l-blue-600',    badge: 'bg-blue-950/50 text-blue-300 border-blue-700',       title: 'text-blue-300' },
  Analysis:   { label: 'Analysis & Think Tanks',            border: 'border-l-violet-600',  badge: 'bg-violet-950/50 text-violet-300 border-violet-700', title: 'text-violet-300' },
  Specialized:{ label: 'Specialized Military',              border: 'border-l-orange-600',  badge: 'bg-orange-950/50 text-orange-300 border-orange-700', title: 'text-orange-300' },
  OSINT:      { label: 'OSINT & Open Source',               border: 'border-l-lime-600',    badge: 'bg-lime-950/50 text-lime-300 border-lime-700',       title: 'text-lime-300' },
  Homeland:   { label: 'Homeland Security & Intelligence',  border: 'border-l-red-600',     badge: 'bg-red-950/50 text-red-300 border-red-700',          title: 'text-red-300' },
}

const CATEGORIES = ['Wire', 'Broadcast', 'Official', 'Analysis', 'Specialized', 'OSINT', 'Homeland'] as const

function SourceCard({ source }: { source: NewsSource }) {
  const style = CATEGORY_STYLES[source.category]
  return (
    <div className={`tac-card rounded-sm p-4 border-l-2 ${style.border} space-y-2`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <div className="flex items-center gap-1.5">
            {source.reliability === 'High' && (
              <ShieldCheck size={10} className="text-emerald-500 shrink-0" />
            )}
            <h3 className="text-xs font-bold text-emerald-200 tracking-wider truncate">
              {source.name}
            </h3>
          </div>
          {source.region && (
            <p className="text-[9px] text-zinc-600 tracking-widest uppercase">{source.region}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-[9px] px-1.5 py-0.5 rounded-sm border tracking-widest uppercase ${style.badge}`}>
            {source.category}
          </span>
          <span
            className={`text-[9px] px-1.5 py-0.5 rounded-sm border tracking-widest ${
              source.reliability === 'High'
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800'
                : source.reliability === 'Medium'
                ? 'bg-amber-950/40 text-amber-400 border-amber-800'
                : 'bg-zinc-900 text-zinc-500 border-zinc-700'
            }`}
          >
            {source.reliability}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="text-[10px] text-zinc-500 leading-relaxed">{source.description}</p>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-1">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-emerald-400 transition-colors tracking-widest uppercase"
        >
          OPEN SOURCE <ExternalLink size={9} />
        </a>
        {source.rssUrl && (
          <a
            href={source.rssUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="RSS Feed"
            className="flex items-center gap-1 text-[10px] text-zinc-600 hover:text-amber-400 transition-colors"
          >
            <Rss size={9} />
            RSS
          </a>
        )}
      </div>
    </div>
  )
}

export default function NewsPage() {
  const sourcesByCategory = CATEGORIES.reduce((acc, cat) => {
    acc[cat] = SOURCES.filter((s) => s.category === cat)
    return acc
  }, {} as Record<string, NewsSource[]>)

  return (
    <section className="space-y-8">
      {/* Page header */}
      <div className="space-y-1 border-b border-emerald-900 pb-4">
        <div className="flex items-center gap-2">
          <ExternalLink size={14} className="text-emerald-400" />
          <h2 className="text-sm font-bold tracking-widest text-emerald-400 glow-green uppercase">
            Verified Source Directory
          </h2>
        </div>
        <p className="text-[10px] text-zinc-500 tracking-wider max-w-2xl">
          Curated index of {SOURCES.length} verified news organisations, official government channels,
          and defence-analysis bodies covering the US–Iran conflict. All links resolve to primary source URLs.
          Reliability ratings reflect editorial standards and track record for military/diplomatic reporting.
        </p>
        <div className="flex items-center gap-4 pt-2">
          {CATEGORIES.map((cat) => {
            const style = CATEGORY_STYLES[cat]
            const count = sourcesByCategory[cat]?.length ?? 0
            return (
              <a key={cat} href={`#${cat}`} className="flex items-center gap-1">
                <span className={`text-[9px] tracking-widest uppercase ${style.title}`}>{cat}</span>
                <span className="text-[9px] text-zinc-700">{count}</span>
              </a>
            )
          })}
        </div>
      </div>

      {/* Category sections */}
      {CATEGORIES.map((cat) => {
        const sources = sourcesByCategory[cat] ?? []
        if (sources.length === 0) return null
        const style = CATEGORY_STYLES[cat]
        return (
          <div key={cat} id={cat} className="space-y-3">
            <h3 className={`text-[11px] font-bold tracking-widest uppercase ${style.title} border-b border-zinc-900 pb-2`}>
              {style.label}
              <span className="text-zinc-700 ml-2 font-normal">({sources.length})</span>
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {sources.map((s) => (
                <SourceCard key={s.id} source={s} />
              ))}
            </div>
          </div>
        )
      })}

      {/* Disclaimer */}
      <div className="border border-zinc-900 rounded-sm p-4 text-[10px] text-zinc-600 tracking-wider space-y-1">
        <p className="text-zinc-500 font-bold uppercase tracking-widest">Editorial Note</p>
        <p>
          All sources listed are publicly accessible and linked for informational purposes. Reliability ratings
          reflect general editorial standards and are not endorsements. Official government sources represent
          their respective institutional positions. Cross-reference multiple sources; apply source-critical
          analysis to all reporting in an active conflict environment.
        </p>
      </div>

      {/* Live feed from all sources */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Radio size={12} className="text-emerald-400 animate-pulse" />
          <h2 className="text-[9px] font-bold tracking-[0.3em] text-emerald-400 uppercase">
            LIVE HEADLINES — NOW BEING ANALYZED BY AI IN REAL TIME
          </h2>
        </div>
        <p className="text-[8px] font-mono text-zinc-600">
          The sources above feed directly into the NEXUS analysis pipeline. Click any headline below to run
          HERALD-3 IO scoring, claim extraction, and cross-reference against the Intel database.
        </p>
        <LiveNewsBoard limit={50} warFilter={false} compact={false} />
      </div>
    </section>
  )
}
