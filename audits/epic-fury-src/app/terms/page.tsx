import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Terms of Service | Epic Fury War Dashboard',
  description: 'Terms of Service and EULA agreement for the Epic Fury 2026 application.',
  robots: { index: true, follow: true },
}

export default function TermsPage() {
  const updated = 'June 30, 2026'

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-mono">
      <div className="max-w-2xl mx-auto px-6 py-12 space-y-8">
        <div className="space-y-2">
          <p className="text-[9px] tracking-[0.3em] text-zinc-600 uppercase">Epic Fury Intelligence Network</p>
          <h1 className="text-lg font-bold tracking-widest text-zinc-100 uppercase">Terms of Service</h1>
          <p className="text-[11px] text-zinc-600">Last updated: {updated}</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">1. Agreement to Terms</h2>
          <p className="text-xs leading-relaxed text-zinc-500">
            By accessing or using Epic Fury 2026 (&ldquo;the App&rdquo;), you agree to be bound by these
            Terms of Service and End User License Agreement (EULA). If you do not agree to these terms,
            do not download, install, or use the App.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">2. End User License Agreement (EULA)</h2>
          <div className="space-y-2 text-xs text-zinc-500 leading-relaxed">
            <p><strong className="text-zinc-400">License Grant:</strong> We grant you a limited, non-exclusive, non-transferable, revocable license to use the App for personal, non-commercial purposes on iOS devices that you own or control, as permitted by the App Store Terms of Service.</p>
            <p><strong className="text-zinc-400">Apple Acknowledgment:</strong> You acknowledge that this agreement is between you and the App publisher only, and not with Apple. Apple is not responsible for the App, its content, maintenance, support, or any claims related to it.</p>
            <p><strong className="text-zinc-400">Subscription Terms:</strong> Access to advanced intelligence feeds require a paid subscription (Monthly/Annual). Subscriptions automatically renew unless auto-renew is turned off at least 24 hours before the end of the current period. Subscriptions can be managed in your App Store Account Settings.</p>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">3. Content & Disclaimers</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            <strong className="text-amber-400">EPIC FURY CONTAINS SIMULATED CONTENT.</strong>{' '}
            &ldquo;Operation Epic Fury&rdquo; is a <strong className="text-zinc-300">fictional conflict scenario</strong>.
            Events, casualties, force postures, negotiations, and threat statuses presented within
            the scenario <strong className="text-zinc-300">did not occur and are not real-world reporting</strong>,
            even where they reference real organizations, nations, or threat actors.
          </p>
          <p className="text-xs text-zinc-500 leading-relaxed mt-3">
            The App <em>also</em> provides live, open-source intelligence drawn from real feeds.
            <strong className="text-zinc-300"> Every dashboard is labelled at the top of the page</strong> as
            {' '}<strong className="text-emerald-400">LIVE DATA</strong>,{' '}
            <strong className="text-amber-400">SIMULATION</strong>,{' '}
            <strong className="text-sky-400">MIXED</strong>, or{' '}
            <strong className="text-zinc-400">UNVERIFIED</strong>. Read that label before you rely on anything.
            Content is for educational, analysis, and information purposes only. We do not warrant the
            accuracy, completeness, or operational safety of any data displayed, and nothing in this App
            may be relied upon for operational, safety-of-life, or investment decisions.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">4. User Conduct</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            You agree not to attempt to reverse engineer, modify, decompile, or extract the source code
            of the native shell. You agree not to use the App for any illegal activities or to disrupt
            the network endpoints.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">5. Limitation of Liability</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            To the maximum extent permitted by law, the publisher and Apple shall not be liable for
            any direct, indirect, incidental, or consequential damages resulting from your use or
            inability to use the App.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">6. Contact & Support</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            If you have questions or need assistance regarding these terms or App support, contact us at:<br />
            <a href="mailto:michael.b.hoch@gmail.com" className="text-sky-600 hover:text-sky-400 underline">michael.b.hoch@gmail.com</a>
          </p>
        </section>

        <div className="border-t border-zinc-900 pt-6">
          <Link href="/dashboard" className="text-[10px] text-zinc-600 hover:text-zinc-400 tracking-widest uppercase transition-colors">
            ← Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}
