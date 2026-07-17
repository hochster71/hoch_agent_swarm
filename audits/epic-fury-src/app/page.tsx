import Link from 'next/link'
import {
  Zap, Radio, ShieldAlert, Globe2, Activity, Clock,
  ChevronRight, AlertTriangle, Newspaper, BarChart3,
} from 'lucide-react'

// Force server-render so the conflict day is always current, never baked in
export const dynamic = 'force-dynamic'



// The public landing page renders NO modeled war figures. It previously headlined
// "Threat Level: NORMAL", "Ceasefire Prob: 95%", and "HORMUZ: FULLY OPEN / 100% CLEARED"
// -- all formula output, none observed -- on the day the real ceasefire collapsed and the
// US moved to reinstate a blockade of the strait. A disclaimer printed above a number does
// not un-say the number. So the numbers are gone from the public surface entirely.
// scripts/verify-no-fabricated-claims.mjs fails the build if lib/war-stats is imported here.
const QUICK_STATS: Array<{ label: string; value: string; sub: string; color: string }> = []

const OPERATOR_DOCTRINE = [
  { label: 'Sea Service Lens', value: '31 Years Naval Operations', tone: 'text-emerald-300' },
  { label: 'Missile Defense Lens', value: '7 Years Integrated BMD', tone: 'text-cyan-300' },
  { label: 'Information Warfare', value: 'Joint Information Control Officer', tone: 'text-amber-300' },
  { label: 'JADC2 Command Fabric', value: 'Sensor to Decision to Action', tone: 'text-rose-300' },
  { label: 'Watchfloor DNA', value: 'E-1 to E-9 Master Chief Operations Specialist', tone: 'text-sky-300' },
  { label: 'Commissioned Continuity', value: 'LDO Surface Line Operations 6120', tone: 'text-lime-300' },
]

const INTEL_PILLARS = [
  'Cross-verify every claim before it enters command traffic',
  'Fuse cyber, maritime, air, and space indicators into one track picture',
  'Publish confidence and dissent, not just conclusions',
  'Prioritize citizen understanding with operator-grade clarity',
]

const FEATURES = [
  {
    icon: Radio,
    color: 'text-emerald-400',
    border: 'border-emerald-900',
    title: 'Intel Feed',
    desc: 'Backed by a real ingested data source — one of the few views on this site that is, rather than a model projection.',
    href: '/dashboard/feed',
  },
  {
    icon: Newspaper,
    color: 'text-rose-400',
    border: 'border-rose-900',
    title: 'AI Newsroom',
    desc: 'AI-generated broadcast summaries produced from ingested sources.',
    href: '/dashboard/newsroom',
  },
  {
    icon: ShieldAlert,
    color: 'text-amber-400',
    border: 'border-amber-900',
    title: 'Homeland Threat',
    desc: 'Homeland threat scenario view. Modeled — not a current threat assessment. Named threat actors are real; their status here is not.',
    href: '/dashboard/homeland',
  },
  {
    icon: BarChart3,
    color: 'text-sky-400',
    border: 'border-sky-900',
    title: 'Ceasefire Tracker',
    desc: 'Negotiation-track scenario model. Projected from a model, not from reporting on any actual negotiation.',
    href: '/dashboard/ceasefire',
  },
  {
    icon: Globe2,
    color: 'text-violet-400',
    border: 'border-violet-900',
    title: 'Economic Impact',
    desc: 'Economic-impact scenario model. Prices are projections from a formula, not market data.',
    href: '/dashboard/econ',
  },
  {
    icon: Activity,
    color: 'text-lime-400',
    border: 'border-lime-900',
    title: 'SITREP',
    desc: 'Scenario situation report. Projected from the model. Not a current SITREP.',
    href: '/dashboard/sitrep',
  },
]

export default function SplashPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-zinc-950 font-mono text-zinc-100 flex flex-col command-ambience">
      <div className="pointer-events-none absolute inset-0 command-aurora" />
      <div className="pointer-events-none absolute inset-0 command-radar-sweep" />

      {/* ── Classification Banner ── */}
      <div className="relative z-10 bg-red-950/60 border-b border-red-900/50 text-center py-1.5">
        <p className="text-[10px] tracking-widest text-red-400 uppercase">
          UNCLASSIFIED // NOT REAL-TIME // MODELED PROJECTIONS — NOT CURRENT REPORTING
        </p>
      </div>

      {/* ── Hero Header ── */}
      <header className="relative z-10 border-b border-emerald-900/40 bg-zinc-950/80 py-10 px-6 text-center overflow-hidden">
        {/* Faint scanline grid */}
        <div className="pointer-events-none absolute inset-0 opacity-5"
          style={{ backgroundImage: 'repeating-linear-gradient(0deg, #22c55e 0px, transparent 1px, transparent 24px)' }}
        />

        <div className="relative z-10 max-w-4xl mx-auto space-y-4">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Zap size={14} className="text-emerald-400 animate-pulse" />
            <span className="text-[10px] tracking-[0.4em] text-zinc-500 uppercase">Open-Source Intelligence</span>
            <Zap size={14} className="text-emerald-400 animate-pulse" />
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-widest text-emerald-300 uppercase"
            style={{ textShadow: '0 0 30px rgba(74,222,128,0.4)' }}>
            Epic Fury
          </h1>
          <p className="text-sm sm:text-base tracking-[0.3em] text-zinc-400 uppercase">
            Operation Epic Fury — US–Iran Conflict {new Date().getFullYear()}
          </p>
          <p className="text-xs text-zinc-500 max-w-2xl mx-auto leading-relaxed normal-case tracking-wide">
            An analytical modeling tool for the 2026 US–Iran conflict.{' '}
            <strong className="text-amber-400">
              The figures shown below are PROJECTIONS from a model, not verified current reporting.
            </strong>{' '}
            They are not sourced from live feeds and may contradict what is actually happening right now.
            For current events, go to{' '}
            <a href="https://www.centcom.mil" className="underline text-sky-400">CENTCOM</a>,{' '}
            <a href="https://www.defense.gov" className="underline text-sky-400">DoD</a>, or a wire service.
            Do not use this page to make any decision that matters.
          </p>

          <div className="max-w-3xl mx-auto rounded border border-emerald-900/50 bg-zinc-900/45 px-4 py-3">
            <p className="text-[9px] tracking-[0.25em] text-emerald-500 uppercase mb-1">Nexus Command Doctrine</p>
            <p className="text-[11px] text-zinc-300 tracking-wide leading-relaxed">
              Open intelligence with a warfighter perspective: disciplined watchstanding, layered missile defense thinking,
              and joint all-domain command principles engineered for public transparency.
            </p>
          </div>

          {/* ── Quick Stats Row ── */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 max-w-2xl mx-auto">
            {QUICK_STATS.map(s => (
              <div key={s.label} className="rounded border border-zinc-800 bg-zinc-900/50 px-3 py-3 text-center">
                <p className={`text-lg font-bold tracking-widest ${s.color}`}>{s.value}</p>
                <p className="text-[9px] text-zinc-500 tracking-widest uppercase mt-0.5">{s.sub}</p>
                <p className="text-[9px] text-zinc-600 tracking-wider mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* ── CTA Buttons ── */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-6 py-3 rounded bg-emerald-700 hover:bg-emerald-600 text-emerald-100 font-bold text-sm tracking-widest uppercase transition-colors"
            >
              <Zap size={14} />
              Enter Command Center
              <ChevronRight size={14} />
            </Link>
            <Link
              href="/dashboard/newsroom"
              className="flex items-center gap-2 px-6 py-3 rounded border border-emerald-800 hover:border-emerald-600 text-emerald-400 font-bold text-sm tracking-widest uppercase transition-colors"
            >
              <Radio size={14} />
              Newsroom
            </Link>
          </div>
        </div>
      </header>

      {/* ── Breaking Alert Strip ── */}
      <div className="relative z-10 bg-red-950/40 border-b border-red-900/40 px-4 py-2 flex items-center gap-3">
        <AlertTriangle size={12} className="text-red-400 shrink-0 animate-pulse" />
        <p className="text-[10px] text-red-300 tracking-widest uppercase">
          <>
                <span className="font-bold">MODELED PROJECTION — NOT CURRENT REPORTING.</span>{' '}
                This page does not observe live events. Nothing here should be read as a
                statement about what is happening right now.
              </>
        </p>
      </div>

      {/* ── Feature Grid ── */}
      <main className="relative z-10 flex-1 max-w-5xl mx-auto w-full px-4 py-10 space-y-8">
        <section className="rounded border border-cyan-900/60 bg-zinc-900/40 p-5">
          <p className="text-[10px] tracking-[0.25em] text-cyan-400 uppercase mb-4">Operator Lens: Fleet to Joint Command</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {OPERATOR_DOCTRINE.map((item) => (
              <div key={item.label} className="rounded border border-zinc-800 bg-zinc-950/55 px-3 py-3">
                <p className="text-[9px] tracking-[0.2em] text-zinc-500 uppercase mb-1">{item.label}</p>
                <p className={`text-xs tracking-wide font-semibold ${item.tone}`}>{item.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {INTEL_PILLARS.map((pillar) => (
              <div key={pillar} className="rounded border border-zinc-800/80 bg-zinc-950/35 px-3 py-2 text-[11px] text-zinc-300 tracking-wide">
                {pillar}
              </div>
            ))}
          </div>
        </section>

        <div>
          <p className="text-[10px] tracking-[0.3em] text-zinc-600 uppercase mb-4 text-center">What&apos;s Inside The Dashboard</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(f => (
              <Link
                key={f.href}
                href={f.href}
                className={`group rounded border ${f.border} bg-zinc-900/40 hover:bg-zinc-800/50 p-4 transition-colors flex flex-col gap-2`}
              >
                <div className="flex items-center gap-2">
                  <f.icon size={14} className={f.color} />
                  <span className={`text-xs font-bold tracking-widest uppercase ${f.color}`}>{f.title}</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed normal-case tracking-wide">{f.desc}</p>
                <span className={`mt-auto text-[10px] ${f.color} group-hover:underline tracking-widest uppercase`}>
                  Open → 
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* ── About / Disclaimer ── */}
        <section className="rounded border border-zinc-800 bg-zinc-900/30 p-6 space-y-3">
          <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
            <Clock size={12} className="text-zinc-500" />
            <p className="text-[10px] tracking-widest text-zinc-500 uppercase">About This Dashboard</p>
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed normal-case tracking-wide">
            <strong className="text-zinc-300">Epic Fury</strong> is a conflict <em>modeling</em> and analysis tool.
            Most figures on this site are <strong className="text-amber-400">projections produced by a model</strong> —
            they are not sourced from live feeds, they are not verified current reporting, and they can contradict
            what is actually happening. A small number of views are backed by live ingested sources and are labelled
            as such on the page. This is <em>not</em> a government platform, it is <em>not</em> a news source, and it
            must not be used for any decision that matters.
          </p>
          <p className="text-xs text-zinc-500 leading-relaxed normal-case tracking-wide">
            <Link href="/terms" className="text-emerald-400 hover:underline">Terms</Link>
            {' · '}
            <Link href="/privacy" className="text-emerald-400 hover:underline">Privacy</Link>
            {' · '}
            <Link href="/refund" className="text-emerald-400 hover:underline">Refunds &amp; Cancellation</Link>
            {' · '}
            <Link href="/support" className="text-emerald-400 hover:underline">Support</Link>
          </p>
          <p className="text-xs text-zinc-500 leading-relaxed normal-case tracking-wide">
            AI analysis is provided for context only. Always verify critical information through official US government
            sources: <a href="https://www.centcom.mil" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">CENTCOM</a>,&nbsp;
            <a href="https://www.defense.gov" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">DoD</a>,&nbsp;
            <a href="https://www.cisa.gov" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:underline">CISA</a>.
          </p>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-zinc-900 px-6 py-4 text-center">
        <p className="text-[9px] tracking-widest text-zinc-700 uppercase">
          UNCLASSIFIED // MODELED PROJECTIONS — DO NOT RELY ON THIS FOR CURRENT EVENTS
          &nbsp;·&nbsp;Epic Fury Intelligence Network&nbsp;·&nbsp;Made in the USA 🇺🇸
        </p>
      </footer>
    </div>
  )
}

