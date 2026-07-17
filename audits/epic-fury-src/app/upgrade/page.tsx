'use client'

/**
 * app/upgrade/page.tsx
 *
 * Public-facing pricing + upgrade page.
 * - Shown when free users visit /upgrade directly, or after cancelling Stripe checkout
 * - Shows plan selector → triggers PaywallModal (web Stripe) or native IAP
 * - SEO-friendly: no auth required to view
 */

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams }               from 'next/navigation'
import { PaywallModal }                  from '@/components/PaywallModal'
import { createBrowserClient }           from '@/lib/supabase'
import { PRICE_MONTHLY_USD, PRICE_ANNUAL_USD } from '@/lib/purchases'

/** Stripe billing portal button — web only */
function ManageSubButton() {
  const [loading, setLoading] = useState(false)
  async function openPortal() {
    setLoading(true)
    try {
      const res  = await fetch('/api/stripe/portal', { method: 'POST' })
      const data = await res.json() as { url?: string; error?: string }
      if (data.url) window.location.href = data.url
      else alert(data.error ?? 'Unable to open billing portal')
    } finally {
      setLoading(false)
    }
  }
  return (
    <button onClick={openPortal} disabled={loading} className="underline hover:text-green-300 disabled:opacity-50 transition-colors">
      {loading ? 'Loading…' : 'Manage subscription'}
    </button>
  )
}

const FEATURES = [
  { icon: '🎯', label: 'ORACLE-9 AI Threat Assessments',   desc: 'Real-time probabilistic threat models across all 9 war domains' },
  { icon: '🧭', label: 'COMPASS Economic Cascade Model',    desc: 'Brent crude, shipping, sanctions, and macro impact scoring' },
  { icon: '📡', label: 'NEXUS 24h / 72h / 30d Forecasts',  desc: 'AI-fused intelligence forecasts updated every 15 minutes' },
  { icon: '💣', label: 'BDA · HVA · ORBAT Reports',        desc: 'Battle damage assessment, high-value targets, order of battle' },
  { icon: '📰', label: '9-Anchor Live Broadcast Newsroom', desc: 'ElevenLabs AI voices reading real-time SITREP scripts' },
  { icon: '🔐', label: 'Full SITREP Archive + Export',      desc: 'Every assessment, every day — downloadable PDF export' },
  { icon: '🚫', label: 'No Ads. Ever.',                     desc: 'Clean intelligence interface — zero advertising' },
]

function UpgradeContent() {
  const searchParams  = useSearchParams()
  const cancelled     = searchParams.get('cancelled') === '1' || searchParams.get('canceled') === '1'
  const success       = searchParams.get('success') === '1'

  const [showPaywall, setShowPaywall] = useState(false)
  const [plan,        setPlan]        = useState<'annual' | 'monthly' >('annual')
  const [isVerifiedPro, setIsVerifiedPro] = useState(false)

  useEffect(() => {
    if (cancelled) {
      const t = setTimeout(() => {}, 500)
      return () => clearTimeout(t)
    }
  }, [cancelled])

  useEffect(() => {
    let mounted = true

    async function checkProStatus() {
      const supabase = createBrowserClient()
      const { data } = await supabase.auth.getSession()
      const user = data.session?.user
      const role = user?.app_metadata?.role as string | undefined
      const isAdmin = !!(user?.email && process.env.NEXT_PUBLIC_ADMIN_EMAIL && user.email === process.env.NEXT_PUBLIC_ADMIN_EMAIL)

      if (mounted) {
        setIsVerifiedPro(role === 'subscriber' || role === 'admin' || isAdmin)
      }
    }

    void checkProStatus()
    return () => {
      mounted = false
    }
  }, [])

  return (
    <div className="min-h-screen bg-zinc-950 text-white">

      {/* Nav */}
      <div className="border-b border-zinc-800/60 px-6 py-4 flex items-center justify-between">
        <a href="/dashboard" className="flex items-center gap-2 text-zinc-300 hover:text-white text-sm transition-colors">
          ← Dashboard
        </a>
        <span className="text-xs text-zinc-600 font-mono">EPIC FURY NEXUS</span>
      </div>

      {/* Banner messages */}
      {cancelled && (
        <div className="bg-zinc-900 border-b border-yellow-800/40 text-yellow-400 text-sm text-center px-4 py-2.5">
          Checkout cancelled — your card was not charged. Subscribe below to unlock Pro access.
        </div>
      )}
      {success && isVerifiedPro && (
        <div className="bg-zinc-900 border-b border-green-800/40 text-green-400 text-sm text-center px-4 py-2.5 flex flex-wrap items-center justify-center gap-4">
          <span>✅ Subscription active! Your Pro access is now unlocked.</span>
          <span className="flex items-center gap-3">
            <a href="/dashboard" className="underline hover:text-green-300">Go to dashboard →</a>
            <span className="text-green-800">|</span>
            <ManageSubButton />
          </span>
        </div>
      )}
      {success && !isVerifiedPro && (
        <div className="bg-zinc-900 border-b border-yellow-800/40 text-yellow-400 text-sm text-center px-4 py-2.5">
          Payment return received, but Pro access is not verified on this account yet. Sign in with the purchasing account or wait a moment for billing sync.
        </div>
      )}

      {/* Hero */}
      <div className="max-w-3xl mx-auto px-6 pt-16 pb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-red-950/40 border border-red-800/50 rounded-full px-4 py-1.5 text-red-400 text-xs font-semibold tracking-widest mb-6">
          ⚡ EPIC FURY PRO
        </div>
        <h1 className="text-4xl sm:text-5xl font-black tracking-tight leading-tight mb-4">
          Full-Spectrum War Intelligence
        </h1>
        <p className="text-zinc-400 text-lg max-w-xl mx-auto leading-relaxed">
          NEXUS-grade AI analysis. ORACLE-9 threat models. Live ElevenLabs broadcast.
          Everything you need to understand Operation Epic Fury — updated every 15 minutes.
        </p>
      </div>

      {/* Feature grid */}
      <div className="max-w-3xl mx-auto px-6 pb-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {FEATURES.map(f => (
            <div key={f.label} className="flex gap-3 bg-zinc-900/50 border border-zinc-800 rounded-xl p-4">
              <span className="text-2xl mt-0.5 shrink-0">{f.icon}</span>
              <div>
                <p className="text-white text-sm font-semibold">{f.label}</p>
                <p className="text-zinc-500 text-xs mt-0.5 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pricing cards */}
      <div className="max-w-md mx-auto px-6 pb-6">
        <h2 className="text-center text-zinc-400 text-sm font-semibold tracking-widest uppercase mb-4">Choose Your Plan</h2>
        <div className="space-y-3">
          {(['annual', 'monthly'] as const).map(p => (
            <button
              key={p}
              onClick={() => setPlan(p)}
              className={`w-full flex justify-between items-center px-5 py-4 rounded-2xl border text-sm transition-all ${
                plan === p
                  ? 'border-red-500 bg-red-950/30 text-white shadow-lg shadow-red-950/20'
                  : 'border-zinc-700 bg-zinc-900/40 text-zinc-400 hover:border-zinc-500'
              }`}
            >
              <div className="text-left">
                <p className="font-bold text-base">
                  {p === 'annual' ? 'Annual' : 'Monthly'}
                  {p === 'annual' && (
                    <span className="ml-2 text-xs bg-red-600 text-white px-2 py-0.5 rounded-full">BEST VALUE</span>
                  )}
                </p>
                <p className="text-zinc-500 text-xs mt-0.5">
                  {p === 'annual'
                    ? '2 months free vs monthly — ~$15.83/mo'
                    : 'Billed monthly, cancel anytime'}
                </p>
              </div>
              <div className="text-right">
                {/* Prices come from the ONE authoritative constant. They were hardcoded
                    here as $39.99/$4.99/$149 — which is the price a customer would
                    actually have been shown, regardless of what the constants said. */}
                <p className="font-mono font-bold text-lg">
                  {p === 'annual' ? PRICE_ANNUAL_USD : PRICE_MONTHLY_USD}
                </p>
                <p className="text-zinc-600 text-xs">/{p === 'annual' ? 'year' : 'month'}</p>
              </div>
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowPaywall(true)}
          className="mt-6 w-full bg-red-600 hover:bg-red-500 text-white font-black text-base py-4 rounded-2xl transition-colors tracking-wide shadow-lg shadow-red-950/30"
        >
          Unlock EPIC FURY PRO →
        </button>

        <p className="text-center text-zinc-600 text-xs mt-3 leading-relaxed">
          Secure payment via Stripe. Cancel anytime — no questions asked.<br />
          iOS &amp; Android: subscribe inside the app via App Store / Google Play.
        </p>
      </div>

      {/* Trust signals */}
      <div className="max-w-2xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-3 gap-4 text-center">
          {[
            { stat: '$0', label: 'Ads shown ever' },
            { stat: '15m', label: 'Update interval' },
            { stat: '9', label: 'AI anchor voices' },
          ].map(t => (
            <div key={t.stat} className="bg-zinc-900/30 border border-zinc-800/60 rounded-xl py-4 px-2">
              <p className="text-white font-black text-2xl">{t.stat}</p>
              <p className="text-zinc-500 text-xs mt-1">{t.label}</p>
            </div>
          ))}
        </div>
      </div>

      {showPaywall && (
        <PaywallModal
          onClose={() => setShowPaywall(false)}
          onSuccess={() => { setShowPaywall(false) }}
          initialPlan={plan}
        />
      )}
    </div>
  )
}

export default function UpgradePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-600 text-sm animate-pulse">Loading…</div>
      </div>
    }>
      <UpgradeContent />
    </Suspense>
  )
}
