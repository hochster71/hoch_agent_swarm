'use client'

/**
 * components/PaywallModal.tsx
 *
 * Full-screen paywall shown to free users who tap a subscriber-only feature.
 * Uses RevenueCat on native iOS; hides gracefully on web.
 *
 * Props:
 *   onClose  — called when user dismisses without subscribing
 *   onSuccess — called after successful purchase or restore
 */

import { useState, useEffect } from 'react'
import { createBrowserClient } from '@/lib/supabase'
import {
  PRICE_MONTHLY_USD,
  PRICE_ANNUAL_USD,
  PRODUCT_MONTHLY,
  PRODUCT_ANNUAL,
  isNative,
  getOfferings,
  purchasePackage,
  restorePurchases,
  type PurchasePackage,
} from '@/lib/purchases'

interface PaywallModalProps {
  onClose:   () => void
  onSuccess: () => void
  initialPlan?: 'monthly' | 'annual' 
}

export function PaywallModal({ onClose, onSuccess, initialPlan = 'annual' }: PaywallModalProps) {
  const [packages, setPackages]     = useState<PurchasePackage[]>([])
  const [loading, setLoading]       = useState(false)
  const [restoring, setRestoring]   = useState(false)
  const [selected, setSelected]     = useState<'monthly' | 'annual' >(initialPlan)

  useEffect(() => {
    if (isNative()) {
      getOfferings().then(setPackages)
    }
  }, [])

  useEffect(() => {
    setSelected(initialPlan)
  }, [initialPlan])

  // Price strings from RevenueCat (locale-aware) or static fallback
  const monthlyPrice = packages.find(p => p.productIdentifier === PRODUCT_MONTHLY)?.priceString ?? PRICE_MONTHLY_USD
  const annualPrice  = packages.find(p => p.productIdentifier === PRODUCT_ANNUAL)?.priceString  ?? PRICE_ANNUAL_USD

  const monthlyPkg = packages.find(p => p.productIdentifier === PRODUCT_MONTHLY)
  const annualPkg  = packages.find(p => p.productIdentifier === PRODUCT_ANNUAL)

  async function handlePurchase() {
    setLoading(true)
    try {
      if (isNative()) {
        // ── iOS: RevenueCat / StoreKit ───────────────────────────────────────
        const pkgId = selected === 'monthly' ? monthlyPkg?.identifier : annualPkg?.identifier
        if (!pkgId) return
        const ok = await purchasePackage(pkgId)
        if (ok) onSuccess()
      } else {
        // ── Web: Stripe Checkout ─────────────────────────────────────────────
        // DO NOT pre-flight the session with the BROWSER client.
        //
        // The magic-link callback stores the session in httpOnly cookies (@supabase/ssr).
        // JavaScript cannot read httpOnly cookies, so browser getSession() returns null for
        // a user who IS correctly signed in. The old code bounced that user to /login, which
        // mailed another magic link, which landed back on /upgrade -- an infinite sign-in
        // loop that made it impossible for ANY customer to pay.
        //
        // The server is the only authority: /api/stripe/checkout revalidates with getUser()
        // against the httpOnly cookies we send via credentials:'include'. Ask it, and let a
        // real 401 -- not a phantom client-side one -- be what redirects to /login.
        const res  = await fetch('/api/stripe/checkout', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body:    JSON.stringify({ plan: selected }),
        })
        let data: { url?: string; error?: string } = {}
        try {
          data = await res.json() as { url?: string; error?: string }
        } catch {
          data = {}
        }

        const requiresSignIn =
          res.status === 401 ||
          res.status === 403 ||
          (typeof data.error === 'string' && /(sign in required|unauthorized|forbidden)/i.test(data.error))

        if (data.url) {
          window.location.href = data.url
        } else {
          if (requiresSignIn) {
            const next = encodeURIComponent('/upgrade')
            window.location.href = `/login?next=${next}`
          } else {
            // Keep user-facing flow quiet; avoid noisy console errors in production.
            alert('Unable to start checkout right now. Please try again in a moment.')
          }
        }
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleRestore() {
    setRestoring(true)
    try {
      const ok = await restorePurchases()
      if (ok) onSuccess()
    } finally {
      setRestoring(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl overflow-hidden">

        {/* Header */}
        <div className="relative bg-gradient-to-b from-red-950/60 to-zinc-900 px-6 pt-8 pb-6 text-center">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-zinc-400 hover:text-white text-xl leading-none"
            aria-label="Close"
          >
            ✕
          </button>
          <div className="text-4xl mb-2">⚡</div>
          <h2 className="text-white font-bold text-xl tracking-tight">EPIC FURY PRO</h2>
          <p className="text-zinc-400 text-sm mt-1">Full-spectrum war intelligence</p>
        </div>

        {/* Feature list */}
        <ul className="px-6 py-4 space-y-2 text-sm text-zinc-300">
          {[
            'ORACLE-9 AI threat assessments',
            'Real-time NEXUS forecast (24h/72h/30d)',
            'Full SITREP archive + export',
            'COMPASS economic cascade model',
            'No ads',
          ].map(f => (
            <li key={f} className="flex items-center gap-2">
              <span className="text-green-400 font-bold">✓</span> {f}
            </li>
          ))}
        </ul>

        {/* Plan selector */}
        <div className="px-6 pb-4 space-y-2">
          {([...(isNative() ? ['annual', 'monthly'] : ['annual', 'monthly'])] as Array<'monthly' | 'annual' >).map(plan => (
            <button
              key={plan}
              onClick={() => setSelected(plan)}
              className={`w-full flex justify-between items-center px-4 py-3 rounded-xl border text-sm transition-colors ${
                selected === plan
                  ? 'border-red-500 bg-red-950/30 text-white'
                  : 'border-zinc-700 bg-zinc-800/50 text-zinc-400'
              }`}
            >
              <span className="font-semibold capitalize">
                {plan === 'annual' ? 'Annual' : 'Monthly'}
                {plan === 'annual' && (
                  <span className="ml-2 text-xs bg-red-600 text-white px-1.5 py-0.5 rounded">2 MONTHS FREE</span>
                )}
              </span>
              <span className="font-mono">
                {plan === 'annual' ? annualPrice : monthlyPrice}
                <span className="text-zinc-500 text-xs">/{plan === 'annual' ? 'yr' : 'mo'}</span>
              </span>
            </button>
          ))}
        </div>

        {/* CTA */}
        <div className="px-6 pb-6 space-y-3">
          <button
            onClick={handlePurchase}
            disabled={loading}
            className="w-full bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl transition-colors tracking-wide"
          >
            {loading ? 'Processing…' : 'Subscribe Now'}
          </button>
          <button
            onClick={handleRestore}
            disabled={restoring}
            className="w-full text-zinc-500 hover:text-zinc-300 text-xs py-1 transition-colors"
          >
            {restoring ? 'Restoring…' : 'Restore previous purchase'}
          </button>
          <p className="text-center text-zinc-600 text-xs pt-1">
            {typeof window !== 'undefined' && !isNative()
              ? 'Secure payment via Stripe. Cancel anytime.'
              : 'Subscription managed by Apple. Cancel anytime in Settings.'}
          </p>
        </div>
      </div>
    </div>
  )
}
