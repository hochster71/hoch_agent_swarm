/**
 * POST /api/webhooks/stripe
 *
 * Receives Stripe webhook events and syncs subscription status to Supabase.
 *
 * Events handled:
 *   checkout.session.completed      → role = 'subscriber'
 *   customer.subscription.updated  → role = 'subscriber' (if active)
 *   customer.subscription.deleted  → role = 'free'
 *   invoice.payment_failed         → role = 'free' (grace period handled by Stripe)
 *
 * Security:
 *   - Verifies Stripe-Signature header with STRIPE_WEBHOOK_SECRET
 *   - Uses Supabase service-role key (server-side only)
 *   - Idempotent — safe to replay
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'

export const runtime = 'nodejs'

function isTransientError(message: string): boolean {
  return /timeout|timed out|rate limit|429|5\d\d|network|fetch failed|temporarily unavailable/i.test(message)
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

async function updateUserRoleWithRetry(
  sb: {
    auth: {
      admin: {
        updateUserById: (userId: string, attributes: { app_metadata: Record<string, unknown> }) => Promise<{
          error: { message?: string } | null
        }>
      }
    }
  },
  userId: string,
  appMetadata: Record<string, unknown>,
): Promise<void> {
  let lastError: unknown = null

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const { error } = await sb.auth.admin.updateUserById(userId, { app_metadata: appMetadata })
    if (!error) return

    lastError = error
    const message = error.message ?? String(error)
    if (attempt >= 3 || !isTransientError(message)) {
      throw error
    }

    await sleep(150 * 2 ** (attempt - 1))
  }

  throw lastError instanceof Error ? lastError : new Error('Failed to update subscriber role')
}

// Stripe requires raw body for signature verification — must NOT parse as JSON
export async function POST(req: NextRequest) {
  const stripeKey     = process.env.STRIPE_SECRET_KEY
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET
  const supaUrl       = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supaKey       = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!stripeKey || !webhookSecret) {
    return NextResponse.json({ error: 'Stripe not configured' }, { status: 503 })
  }
  if (!supaUrl || !supaKey) {
    return NextResponse.json({ error: 'Supabase not configured' }, { status: 503 })
  }

  // ── Verify signature ──────────────────────────────────────────────────────
  const rawBody  = await req.text()
  const sig      = req.headers.get('stripe-signature') ?? ''

  let event: import('stripe').Stripe.Event
  try {
    const Stripe = (await import('stripe')).default
    const stripe = new Stripe(stripeKey, { apiVersion: '2026-04-22.dahlia' })
    event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret)
  } catch (e) {
    console.error('[stripe/webhook] signature verification failed:', e)
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
  }

  const sb = createClient(supaUrl, supaKey)

  // ── Handle events ─────────────────────────────────────────────────────────
  try {
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object as import('stripe').Stripe.Checkout.Session
      const userId  = session.client_reference_id  // Supabase UUID set in checkout
      const isPaid = session.mode === 'subscription' || session.payment_status === 'paid'
      if (userId && isPaid) {
        // NEVER DOWNGRADE A PRIVILEGED ROLE.
        // This wrote role='subscriber' unconditionally. If an admin subscribed, their admin
        // role was silently replaced by 'subscriber' -- a real paying admin would LOSE their
        // admin access as a direct consequence of paying. Preserve the higher role and record
        // the subscription alongside it.
        const existing = await sb.auth.admin.getUserById(userId)
        const currentRole = existing?.data?.user?.app_metadata?.role as string | undefined
        const PRIVILEGED = ['admin', 'founder']
        const nextRole = PRIVILEGED.includes(currentRole ?? '') ? currentRole : 'subscriber'

        await updateUserRoleWithRetry(sb, userId, {
          role: nextRole,
          subscription_status: 'active',      // the fact of payment, independent of role
          stripe_customer_id: session.customer,
        })
        console.warn(`[stripe/webhook] ${userId} -> role=${nextRole} subscription=active (checkout complete)`)
      }
    }

    if (event.type === 'customer.subscription.updated') {
      const sub    = event.data.object as import('stripe').Stripe.Subscription
      const userId = sub.metadata?.supabase_user_id
      if (userId) {
        // Same no-downgrade rule: a privileged role survives any subscription change.
        const active = sub.status === 'active' || sub.status === 'trialing'
        const existing = await sb.auth.admin.getUserById(userId)
        const currentRole = existing?.data?.user?.app_metadata?.role as string | undefined
        const PRIVILEGED = ['admin', 'founder']
        const nextRole = PRIVILEGED.includes(currentRole ?? '')
          ? currentRole
          : (active ? 'subscriber' : 'free')
        await updateUserRoleWithRetry(sb, userId, {
          role: nextRole,
          subscription_status: active ? 'active' : 'inactive',
        })
        console.warn(`[stripe/webhook] ${userId} -> role=${nextRole} sub=${sub.status}`)
      }
    }

    if (event.type === 'customer.subscription.deleted') {
      const sub    = event.data.object as import('stripe').Stripe.Subscription
      const userId = sub.metadata?.supabase_user_id
      if (userId) {
        // WORST CASE OF THE DOWNGRADE BUG: cancelling a subscription set role='free',
        // which would have STRIPPED ADMIN from the founder the moment he cancelled.
        // A billing event must never revoke a privileged role.
        const existing = await sb.auth.admin.getUserById(userId)
        const currentRole = existing?.data?.user?.app_metadata?.role as string | undefined
        const PRIVILEGED = ['admin', 'founder']
        const nextRole = PRIVILEGED.includes(currentRole ?? '') ? currentRole : 'free'
        await updateUserRoleWithRetry(sb, userId, {
          role: nextRole,
          subscription_status: 'cancelled',
        })
        console.warn(`[stripe/webhook] ${userId} -> role=${nextRole} subscription=cancelled`)
      }
    }

    if (event.type === 'invoice.payment_failed') {
      const invoice = event.data.object as import('stripe').Stripe.Invoice
      console.warn(`[stripe/webhook] payment failed for customer ${invoice.customer}`)
    }
  } catch (e) {
    console.error('[stripe/webhook] handler error:', e)
    return NextResponse.json({ error: 'handler error' }, { status: 500 })
  }

  return NextResponse.json({ received: true })
}
