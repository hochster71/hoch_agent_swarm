/**
 * POST /api/stripe/checkout
 *
 * Creates a Stripe Checkout Session for web subscribers.
 * Returns { url } — client redirects to Stripe-hosted checkout.
 *
 * Plans:
 *   monthly   → STRIPE_PRICE_MONTHLY  (recurring)
 *   annual    → STRIPE_PRICE_ANNUAL   (recurring)
 *   lifetime  → STRIPE_PRICE_LIFETIME (one-time)
 *
 * After payment, Stripe redirects to /upgrade?success=1
 * On cancel, Stripe redirects to /upgrade?canceled=1
 *
 * Stripe webhook (/api/webhooks/stripe) handles checkout.session.completed
 * and customer.subscription.deleted to flip Supabase user role.
 *
 * Required env vars:
 *   STRIPE_SECRET_KEY          — sk_live_xxx or sk_test_xxx
 *   STRIPE_PRICE_MONTHLY       — price_xxx (monthly recurring)
 *   STRIPE_PRICE_ANNUAL        — price_yyy (annual recurring)
 *   NEXT_PUBLIC_SITE_URL       — for success/cancel redirect URLs
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient }        from '@/lib/supabase-server'

export const runtime = 'nodejs'

export async function POST(req: NextRequest) {
  // ── Auth: must be signed in ───────────────────────────────────────────────
  // getUser() revalidates the token against Supabase; getSession() only reads the cookie.
  // This route leads to a charge and to an entitlement — verify, don't assume.
  const supabase = await createServerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    return NextResponse.json({ error: 'Sign in required to subscribe' }, { status: 401 })
  }

  // ── Parse plan ────────────────────────────────────────────────────────────
  let plan: string
  try {
    const body = await req.json() as { plan?: unknown }
    plan = typeof body.plan === 'string' ? body.plan : 'annual'
  } catch {
    plan = 'annual'
  }

  const stripeKey      = process.env.STRIPE_SECRET_KEY
  const priceMonthly   = process.env.STRIPE_PRICE_MONTHLY
  const priceAnnual    = process.env.STRIPE_PRICE_ANNUAL
  const siteUrl        = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://epic-fury-2026.vercel.app'

  if (!stripeKey) {
    return NextResponse.json({ error: 'Web payments not yet configured' }, { status: 503 })
  }

  const priceId = plan === 'monthly' ? priceMonthly : priceAnnual
  if (!priceId) {
    return NextResponse.json({ error: `Stripe price ID for plan "${plan}" not configured` }, { status: 503 })
  }

  // ── Lazy-import Stripe ────────────────────────────────────────────────────
  let stripe: import('stripe').default
  try {
    const Stripe = (await import('stripe')).default
    stripe = new Stripe(stripeKey, { apiVersion: '2026-04-22.dahlia' })
  } catch {
    return NextResponse.json({ error: 'Stripe SDK unavailable' }, { status: 503 })
  }

  // ── Create Checkout Session (MANAGED PAYMENTS) ────────────────────────────
  //
  // `managed_payments.enabled` is the ONLY thing that makes Stripe the MERCHANT OF
  // RECORD. Without it this is an ordinary Checkout Session: Stripe processes the card,
  // but YOU are the legal seller and YOU personally owe VAT/GST/sales tax in every
  // jurisdiction you sell into. Nothing in the response tells you that — the checkout
  // works either way. You would only find out at an audit.
  //
  // With it: Stripe is the seller of record, calculates/collects/remits indirect tax in
  // 80+ countries, absorbs fraud and disputes, and the customer sees "Sold through Link".
  //
  // Managed Payments TAKES OVER parts of the session, so several parameters are REJECTED
  // and must not be sent (docs: /payments/managed-payments/update-checkout):
  //   payment_method_types  -- MP picks payment methods dynamically
  //   automatic_tax         -- MP does the tax
  //   tax_id_collection     -- ditto
  //   adaptive_pricing      -- always on under MP
  //   shipping_*            -- digital goods only
  //   invoice_creation      -- MP sends the invoices
  // We previously sent `payment_method_types: ['card']`. That alone would have failed.
  try {
    const checkoutSession = await stripe.checkout.sessions.create({
      mode: 'subscription',
      managed_payments: { enabled: true },
      line_items: [{ price: priceId, quantity: 1 }],

      // Bind the purchase to the Supabase user TWO ways. The webhook is the only thing
      // that may grant access, and it must know WHO paid. Never match on email alone —
      // anyone can type someone else's email into a checkout form.
      client_reference_id: user.id,
      customer_email: user.email,
      subscription_data: {
        metadata: { supabase_user_id: user.id, plan },
      },
      metadata: { supabase_user_id: user.id, plan },

      success_url: `${siteUrl}/upgrade?success=1&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${siteUrl}/upgrade?canceled=1`,
      allow_promotion_codes: true,
    })

    return NextResponse.json({ url: checkoutSession.url })
  } catch (e) {
    // Fail LOUDLY and specifically. A checkout that silently 500s is how you discover,
    // weeks later, that nobody could have paid you even if they wanted to.
    const msg = e instanceof Error ? e.message : String(e)
    console.error('[stripe/checkout] session creation failed:', msg)
    if (/managed_payments/i.test(msg)) {
      console.error(
        '[stripe/checkout] Managed Payments appears not to be enabled on this account. ' +
          'Accept the terms at https://dashboard.stripe.com/settings/managed-payments',
      )
    }
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 })
  }
}
