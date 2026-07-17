import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Privacy Policy | Epic Fury War Dashboard',
  description: 'Privacy policy for the Epic Fury 2026 intelligence dashboard and iOS application.',
  robots: { index: true, follow: true },
}

export default function PrivacyPage() {
  const updated = 'April 9, 2026'

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-mono">
      <div className="max-w-2xl mx-auto px-6 py-12 space-y-8">
        <div className="space-y-2">
          <p className="text-[9px] tracking-[0.3em] text-zinc-600 uppercase">Epic Fury Intelligence Network</p>
          <h1 className="text-lg font-bold tracking-widest text-zinc-100 uppercase">Privacy Policy</h1>
          <p className="text-[11px] text-zinc-600">Last updated: {updated}</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">1. Overview</h2>
          <p className="text-xs leading-relaxed text-zinc-500">
            Epic Fury 2026 (&ldquo;the App&rdquo;) is an open-source intelligence (OSINT) news and analysis
            dashboard covering the 2026 US–Iran conflict. This policy explains what information
            we collect, how we use it, and your rights.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">2. Information We Collect</h2>
          <div className="space-y-2 text-xs text-zinc-500 leading-relaxed">
            <p><strong className="text-zinc-400">Account data:</strong> If you create an account, we store your email address and a hashed password using Supabase Auth. No other personal information is required.</p>
            <p><strong className="text-zinc-400">Session data:</strong> A session token is stored in a secure HTTP-only cookie to keep you signed in. This is cleared on sign-out.</p>
            <p><strong className="text-zinc-400">Usage data:</strong> We do not run analytics, tracking pixels, or behavioural profiling. Standard server access logs (IP address, request path, timestamp) may be retained by our hosting provider (Vercel) for up to 30 days.</p>
            <p><strong className="text-zinc-400">No advertising:</strong> We do not sell, trade, or share your personal data with advertisers or third parties for marketing purposes.</p>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">3. How We Use Your Information</h2>
          <ul className="text-xs text-zinc-500 leading-relaxed space-y-1 list-disc list-inside">
            <li>To authenticate your account and enforce subscription access tiers</li>
            <li>To deliver personalised dashboard content based on your subscription level</li>
            <li>To maintain platform security and prevent abuse</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">4. Third-Party Services</h2>
          <div className="text-xs text-zinc-500 leading-relaxed space-y-2">
            <p><strong className="text-zinc-400">Supabase</strong> — authentication and database hosting (EU/US data regions). <a href="https://supabase.com/privacy" className="text-sky-600 hover:text-sky-400 underline" target="_blank" rel="noopener noreferrer">Privacy policy →</a></p>
            <p><strong className="text-zinc-400">Vercel</strong> — web hosting and edge delivery. <a href="https://vercel.com/legal/privacy-policy" className="text-sky-600 hover:text-sky-400 underline" target="_blank" rel="noopener noreferrer">Privacy policy →</a></p>
            <p><strong className="text-zinc-400">OpenAI / ElevenLabs</strong> — used server-side for AI-generated intelligence analysis. No user data is sent; only editorial content is processed.</p>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">5. Data Retention & Deletion</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Your account data is retained for as long as your account is active. You may request
            deletion at any time by emailing{' '}
            <a href="mailto:privacy@epicfury.app" className="text-sky-600 hover:text-sky-400 underline">privacy@epicfury.app</a>.
            We will delete your account and associated data within 30 days.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">6. Children&rsquo;s Privacy</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            This App covers active military conflict and is intended for users aged 17 and older.
            We do not knowingly collect personal information from anyone under 13.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">7. California &amp; GDPR Rights</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            If you are a California resident or located in the European Economic Area, you have the
            right to access, correct, or delete your personal data. Contact us at{' '}
            <a href="mailto:privacy@epicfury.app" className="text-sky-600 hover:text-sky-400 underline">privacy@epicfury.app</a>.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold tracking-widest text-zinc-400 uppercase">8. Contact</h2>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Epic Fury Intelligence Network<br />
            <a href="mailto:privacy@epicfury.app" className="text-sky-600 hover:text-sky-400 underline">privacy@epicfury.app</a>
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
