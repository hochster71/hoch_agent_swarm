import {
  Shield,
  AlertTriangle,
  DollarSign,
  Users,
  Globe,
  Zap,
  BookOpen,
  Radio,
  TrendingUp,
  ExternalLink,
  ChevronRight,
  Flag,
  Heart,
  Landmark,
  Anchor,
} from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { getConflictDay, toDateStr } from '@/lib/conflict-day'
import { ShareButton } from '@/components/ShareButton'

export const metadata = { title: 'Start Here — What You Need to Know | Epic Fury' }

const CONFLICT_DAY  = getConflictDay()
const CONFLICT_DATE = toDateStr(CONFLICT_DAY)

// ── Data ─────────────────────────────────────────────────────────────────────

const DASHBOARD_SECTIONS = [
  { href: '/dashboard',            icon: Shield,        label: 'Main Dashboard',        desc: 'At-a-glance overview — threat level, top news, Oracle threat model, all in one place' },
  { href: '/dashboard/sitrep',     icon: Radio,         label: 'Daily SITREP',          desc: 'AI-generated situation report — what happened today, what it means for you' },
  { href: '/dashboard/intel',      icon: AlertTriangle, label: 'Intelligence Feed',     desc: 'Verified news and intelligence items scored by severity and source reliability' },
  { href: '/dashboard/econ',       icon: DollarSign,    label: 'Economy & Energy',      desc: 'Gas prices, oil markets, sanctions, supply chain — the economic war explained' },
  { href: '/dashboard/ceasefire',  icon: Globe,         label: 'Ceasefire & Diplomacy', desc: "Diplomatic channels, peace probability, Iran's demands vs US positions" },
  { href: '/dashboard/homeland',   icon: Anchor,        label: 'Homeland Threats',      desc: 'CONUS threat level, cybersecurity warnings, what\'s being watched inside the US' },
  { href: '/dashboard/agents',     icon: Zap,           label: 'AI Pipeline',           desc: 'Full AI pipeline view — source scoring, threat modeling, accuracy metrics' },
]

const HOW_IT_AFFECTS_YOU = [
  { icon: DollarSign, color: 'text-amber-400 border-amber-800 bg-amber-950/20',   label: 'Gas & Energy Prices',      detail: 'Oil markets remain elevated from the Hormuz disruption — Brent at $94/bbl and declining as PARTIAL TRANSIT resumed D24. Pump prices are high but stabilizing. Heating oil, jet fuel, and electricity costs remain above pre-conflict levels. See the Economy page for live market prices.' },
  { icon: TrendingUp, color: 'text-red-400 border-red-800 bg-red-950/20',         label: 'Stock Market & Savings',   detail: 'The S&P 500 is down ~11%. Retirement accounts and investments have taken a hit. Defense stocks are way up. If you have a 401(k), the mix of sectors matters now more than usual.' },
  { icon: Globe,      color: 'text-sky-400 border-sky-800 bg-sky-950/20',         label: 'Travel & Supply Chain',    detail: 'Flights to/from the Middle East are suspended. Global shipping is disrupted — slower delivery times and higher prices for imported goods are expected over the next 60–90 days.' },
  { icon: Landmark,   color: 'text-violet-400 border-violet-800 bg-violet-950/20',label: 'Your Tax Dollars',         detail: 'Emergency military supplemental spending is ongoing. Estimated $2–4B per week in active operations. Congress will vote on an emergency spending package. This adds to national debt.' },
  { icon: Heart,      color: 'text-emerald-400 border-emerald-800 bg-emerald-950/20', label: 'Military Families',    detail: '~45,000 US service members are currently deployed to the theater. Casualty information is officially restricted. The Red Cross and CACO channels remain the authoritative source for family notifications.' },
]

const THREATCON_LEVELS = [
  { level: 'NORMAL',   color: 'text-emerald-400 border-emerald-800 bg-emerald-950/20', meaning: 'No known immediate threat. Routine military readiness.' },
  { level: 'ELEVATED', color: 'text-yellow-400 border-yellow-800 bg-yellow-950/20',   meaning: 'Increased threat indications. Additional security measures in place.' },
  { level: 'HIGH',     color: 'text-amber-400 border-amber-800 bg-amber-950/20',      meaning: 'Credible threat detected. Targeted protective actions underway.' },
  { level: 'SEVERE',   color: 'text-orange-400 border-orange-800 bg-orange-950/20',   meaning: 'Threat is imminent or in progress. All response resources engaged.' },
  { level: 'CRITICAL', color: 'text-red-400 border-red-800 bg-red-950/20',            meaning: 'Attack occurring or confirmed. Maximum protective actions in effect.' },
]

// ── Page ─────────────────────────────────────────────────────────────────────

export default function BriefPage() {
  return (
    <div className="space-y-6 max-w-screen-xl pb-10">

      {/* Alert banner */}
      <div className="tac-card border-red-900/60 bg-red-950/10 p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle size={15} className="text-red-400 shrink-0 mt-0.5 animate-pulse" />
            <div>
              <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-0.5">
                Day {CONFLICT_DAY} of Active Hostilities — {CONFLICT_DATE}
              </p>
              <h1 className="text-sm font-bold tracking-widest text-red-400 uppercase">
                START HERE — What Every American Should Know
              </h1>
              <p className="text-[10px] text-zinc-400 mt-1 leading-relaxed max-w-3xl">
                The US military is engaged in active combat operations against Iran. This dashboard gives you
                real-time, source-verified information — no spin, no paywall, no partisan framing.
                Here&apos;s how to use it and what it means for you.
              </p>
            </div>
          </div>
          <ShareButton
            title="Epic Fury War Dashboard — Start Here"
            text={`Day ${CONFLICT_DAY} of the US-Iran conflict. Real-time OSINT dashboard for American citizens.`}
            className="shrink-0"
          />
        </div>
      </div>

      {/* What happened */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header">
          <BookOpen size={11} className="text-violet-400" />
          <span className="text-violet-300 tracking-widest">WHAT HAPPENED — Plain English</span>
        </div>
        <div className="space-y-2 text-[11px] text-zinc-400 leading-relaxed max-w-4xl">
          <p>
            On <strong className="text-zinc-200">March 1, 2026</strong>, the United States and Israel launched
            coordinated strikes against Iranian nuclear facilities, IRGC command infrastructure, and air
            defense networks. This was designated <strong className="text-zinc-200">Operation Epic Fury</strong>.
            Iran retaliated within hours with ballistic missile and drone strikes against US bases in the region.
          </p>
          <p>
            As of Day {CONFLICT_DAY}, active hostilities are ongoing with intense diplomatic activity. The{' '}
            <strong className="text-zinc-200">Strait of Hormuz is under PARTIAL TRANSIT</strong> — ZB-α mine
            clearance zone 78% cleared, 7 VLCCs transited D24–D27. Ceasefire negotiations through the Abu Dhabi
            Framework show <strong className="text-zinc-200">68% probability</strong> — Iran dropped its
            precondition D26 under UNSCR 2731.
          </p>
          <p>
            <strong className="text-zinc-200">No nuclear weapons have been used.</strong> Iran&apos;s nuclear
            program has been significantly degraded but not eliminated. Diplomatic channels through Oman
            remain open. The situation is serious and evolving — but not a civilization-ending event.
            Stay informed, not panicked.
          </p>
        </div>
      </div>

      {/* How this affects you */}
      <div className="space-y-3">
        <div className="tac-section-header">
          <Users size={11} className="text-amber-400" />
          <span className="text-amber-300 tracking-widest">HOW THIS AFFECTS YOU — Day {CONFLICT_DAY}</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {HOW_IT_AFFECTS_YOU.map((item) => (
            <div key={item.label} className={cn('tac-card p-4 space-y-2 border', item.color)}>
              <div className="flex items-center gap-2">
                <item.icon size={13} className={item.color.split(' ')[0]} />
                <p className="text-[10px] font-bold tracking-widest uppercase text-zinc-200">{item.label}</p>
              </div>
              <p className="text-[10px] text-zinc-400 leading-relaxed">{item.detail}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Dashboard navigation guide */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header">
          <Flag size={11} className="text-emerald-400" />
          <span className="text-emerald-300 tracking-widest">YOUR GUIDE TO THIS DASHBOARD</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {DASHBOARD_SECTIONS.map((s) => (
            <Link
              key={s.href}
              href={s.href}
              className="flex items-start gap-3 border border-zinc-800 rounded p-3 hover:border-emerald-800 hover:bg-emerald-950/10 transition-colors group"
            >
              <s.icon size={14} className="text-emerald-400 shrink-0 mt-0.5 group-hover:text-emerald-300 transition-colors" />
              <div>
                <div className="flex items-center gap-1">
                  <p className="text-[11px] font-bold text-zinc-200 group-hover:text-emerald-300 transition-colors">{s.label}</p>
                  <ChevronRight size={10} className="text-zinc-600 group-hover:text-emerald-400 transition-colors" />
                </div>
                <p className="text-[10px] text-zinc-500 leading-relaxed">{s.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* How to read threat levels */}
      <div className="tac-card p-4 space-y-3">
        <div className="tac-section-header">
          <Shield size={11} className="text-red-400" />
          <span className="text-red-300 tracking-widest">HOW TO READ THREAT LEVELS</span>
        </div>
        <div className="space-y-2">
          {THREATCON_LEVELS.map((t) => (
            <div key={t.level} className={cn('flex items-center gap-3 border rounded p-2.5', t.color)}>
              <span className={cn('text-[9px] font-bold tracking-widest border rounded px-2 py-0.5 shrink-0', t.color)}>
                {t.level}
              </span>
              <p className="text-[10px] text-zinc-400">{t.meaning}</p>
            </div>
          ))}
        </div>
        <p className="text-[9px] text-zinc-600 border-t border-zinc-800 pt-2">
          Current THREATCON is <strong className="text-red-400">SEVERE</strong> for CONUS infrastructure,
          cyberattacks, and personnel in the Middle East theater.
        </p>
      </div>

      {/* Stay informed */}
      <div className="tac-card border-emerald-900/60 bg-emerald-950/10 p-4 space-y-3">
        <div className="tac-section-header">
          <Radio size={11} className="text-emerald-400 animate-pulse" />
          <span className="text-emerald-300 tracking-widest">STAY INFORMED — Share &amp; Save</span>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <div className="text-[10px] text-zinc-400 leading-relaxed max-w-lg">
            This dashboard updates every few minutes with verified intelligence. Share it with family and
            friends who want facts over rumor. Save it to your home screen for quick access.
          </div>
          <ShareButton
            title="Epic Fury War Dashboard — Live US-Iran Conflict Tracker"
            text="Real-time OSINT dashboard for the 2026 US-Iran conflict. No paywall, no spin — just verified intelligence for American citizens."
            className="shrink-0"
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 border-t border-zinc-800/60">
          {[
            { label: '📲 iPhone', step: 'Safari → Share → Add to Home Screen' },
            { label: '🤖 Android', step: 'Chrome Menu → Add to Home Screen' },
            { label: '💻 Desktop', step: 'Bookmark this page (Cmd/Ctrl+D)' },
          ].map((d) => (
            <div key={d.label} className="border border-zinc-800 rounded p-2.5 space-y-0.5">
              <p className="text-[10px] font-bold text-zinc-300">{d.label}</p>
              <p className="text-[9px] text-zinc-500">{d.step}</p>
            </div>
          ))}
        </div>
      </div>

      {/* About this dashboard */}
      <div className="tac-card p-4 border-zinc-800/60">
        <div className="tac-section-header mb-2">
          <Zap size={11} className="text-zinc-500" />
          <span className="text-zinc-500 tracking-widest">ABOUT THIS DASHBOARD</span>
        </div>
        <p className="text-[10px] text-zinc-500 leading-relaxed max-w-3xl">
          Epic Fury is an open-source intelligence (OSINT) dashboard built for American citizens during the
          2026 US-Iran conflict. It aggregates public news sources, runs AI analysis to score and verify
          information, and presents military/economic data in plain English. All sources are cited, all AI
          outputs are labeled. This is not a US government product — it is independent civil-society journalism
          infrastructure.{' '}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-700 hover:text-emerald-400 transition-colors inline-flex items-center gap-1"
          >
            <ExternalLink size={8} /> Source code on GitHub
          </a>
        </p>
      </div>

    </div>
  )
}
