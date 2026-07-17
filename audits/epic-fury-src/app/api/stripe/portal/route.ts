/**
 * POST /api/stripe/portal
 *
 * Creates a Stripe Customer Portal session for the signed-in user,
 * allowing them to manage / cancel their web subscription.
 *
 * Returns { url } — client redirects there.
 *
 * Requirements:
 *   STRIPE_SECRET_KEY           — sk_live_xxx
 *   NEXT_PUBLIC_SITE_URL        — for return_url
 *
 * The user must have a stripe_customer_id stored in their
 * Supabase app_metadata (set by /api/webhooks/stripe on checkout.session.completed).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient }        from '@/lib/supabase-server'

export const runtime = 'nodejs'

export async function POST(_req: NextRequest) {
  // ── Auth ──────────────────────────────────────────────────────────────────
  const supabase = await createServerClient()
  const { data: { session } } = await supabase.auth.getSession()

  if (!session?.user) {
    return NextResponse.json({ error: 'Sign in required' }, { status: 401 })
  }

  // ── Env ───────────────────────────────────────────────────────────────────
  const stripeKey = process.env.STRIPE_SECRET_KEY
  const siteUrl   = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://epic-fury-2026.vercel.app'

  if (!stripeKey) {
    return NextResponse.json({ error: 'Stripe not configured' }, { status: 503 })
  }

  // ── Look up Stripe customer ID ────────────────────────────────────────────
  const customerId = session.user.app_metadata?.stripe_customer_id as string | undefined

  if (!customerId) {
    return NextResponse.json(
      { error: 'No Stripe account found. If you subscribed via iOS App Store, manage your subscription in Apple Settings → Subscriptions.' },
      { status: 404 }
    )
  }

  // ── Create portal session ─────────────────────────────────────────────────
  try {
    const Stripe = (await import('stripe')).default
    const stripe = new Stripe(stripeKey, { apiVersion: '2026-04-22.dahlia' })

    const portalSession = await stripe.billingPortal.sessions.create({
      customer:   customerId,
      return_url: `${siteUrl}/dashboard`,
    })

    return NextResponse.json({ url: portalSession.url })
  } catch (e) {
    console.error('[stripe/portal]', e)
    return NextResponse.json({ error: 'Failed to create portal session' }, { status: 500 })
  }
}
