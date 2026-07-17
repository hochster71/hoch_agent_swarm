import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Support | Epic Fury War Dashboard',
  description: 'Support and contact information for the Epic Fury 2026 intelligence dashboard and iOS application.',
  robots: { index: true, follow: true },
}

export default function SupportPage() {
  const year = new Date().getFullYear()

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-mono">
      <div className="max-w-2xl mx-auto px-6 py-12 space-y-8">
        <div className="space-y-2">
          <p className="text-[9px] tracking-[0.3em] text-zinc-600 uppercase">Epic Fury Intelligence Network</p>
          <h1 className="text-lg font-bold tracking-widest text-zinc-100 uppercase">Support</h1>
          <p className="text-[11px] text-zinc-600">Epic Fury 2026 — US–Iran Conflict Intelligence Dashboard</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">Contact</h2>
          <p className="text-xs leading-relaxed text-zinc-500">
            For support, bug reports, or feedback, please email{' '}
            <a
              href="mailto:michael.b.hoch@gmail.com"
              className="text-emerald-500 hover:text-emerald-400 underline underline-offset-2"
            >
              michael.b.hoch@gmail.com
            </a>
            . Response time is typically within 24–48 hours.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">Frequently Asked Questions</h2>

          <div className="space-y-4">
            <div className="border border-zinc-800 rounded p-4 space-y-1">
              <p className="text-xs font-semibold text-zinc-200">What is Epic Fury 2026?</p>
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                Epic Fury 2026 is a real-time open-source intelligence (OSINT) dashboard tracking the 2026 US–Iran
                conflict. It uses AI to curate, score, and synthesize publicly available information — providing
                civilian situational awareness without classified data.
              </p>
            </div>

            <div className="border border-zinc-800 rounded p-4 space-y-1">
              <p className="text-xs font-semibold text-zinc-200">Is the information classified or government-affiliated?</p>
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                No. All information presented is derived from open-source, publicly available sources including wire
                services, official government press releases (CENTCOM, DHS, CISA), and verified media outlets.
                Epic Fury 2026 has no government affiliation. All analysis represents the independent professional
                judgment of the developer.
              </p>
            </div>

            <div className="border border-zinc-800 rounded p-4 space-y-1">
              <p className="text-xs font-semibold text-zinc-200">How do I cancel my subscription?</p>
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                iOS subscriptions can be cancelled at any time through your Apple ID settings:
                Settings → [Your Name] → Subscriptions → Epic Fury 2026 → Cancel Subscription.
                You will retain access through the end of your current billing period.
              </p>
            </div>

            <div className="border border-zinc-800 rounded p-4 space-y-1">
              <p className="text-xs font-semibold text-zinc-200">The intel feed isn&apos;t updating — what do I do?</p>
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                Pull to refresh on the feed page. If updates remain stalled for more than 30 minutes, check
                your internet connection. AI ingest runs every 5 minutes on our servers — the feed should
                auto-populate without any action required.
              </p>
            </div>

            <div className="border border-zinc-800 rounded p-4 space-y-1">
              <p className="text-xs font-semibold text-zinc-200">I found an error in the intelligence data — how do I report it?</p>
              <p className="text-[11px] text-zinc-500 leading-relaxed">
                All AI-synthesized intelligence carries a confidence score. If you identify a factual error,
                please email{' '}
                <a
                  href="mailto:michael.b.hoch@gmail.com"
                  className="text-emerald-500 hover:text-emerald-400 underline underline-offset-2"
                >
                  michael.b.hoch@gmail.com
                </a>{' '}
                with the specific report title and the correction. We review all submissions.
              </p>
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">About the Developer</h2>
          <p className="text-xs leading-relaxed text-zinc-500">
            Epic Fury 2026 was built by a retired U.S. Navy Lieutenant Commander with 31 years of Surface Warfare
            experience — including multiple deployments to the Persian Gulf, Red Sea, and Arabian Sea. The platform
            applies operational naval intelligence analysis methodology to open-source data, combined with modern
            AI to provide real-time situational awareness.
          </p>
        </section>

        <div className="border-t border-zinc-800 pt-6 flex items-center justify-between">
          <p className="text-[10px] text-zinc-700">© {year} Epic Fury Intelligence Network</p>
          <div className="flex space-x-3">
            <Link href="/privacy" className="text-[10px] text-zinc-600 hover:text-zinc-400 tracking-widest uppercase">
              Privacy
            </Link>
            <span className="text-[10px] text-zinc-800">|</span>
            <Link href="/terms" className="text-[10px] text-zinc-600 hover:text-zinc-400 tracking-widest uppercase">
              Terms
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
