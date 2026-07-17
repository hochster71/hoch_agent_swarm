/**
 * POST /api/webhooks/revenuecat
 *
 * Receives RevenueCat server-side webhooks and promotes / demotes the
 * corresponding Supabase user's app_metadata.role field.
 *
 * Events handled:
 *   INITIAL_PURCHASE   → role = 'subscriber'
 *   RENEWAL            → role = 'subscriber'
 *   UNCANCELLATION     → role = 'subscriber'
 *   CANCELLATION       → role = 'free'  (access until billing period end)
 *   EXPIRATION         → role = 'free'
 *   BILLING_ISSUE      → role = 'free'
 *
 * Security:
 *   - Validates the X-RevenueCat-Secret header against REVENUECAT_WEBHOOK_SECRET
 *   - Uses Supabase service-role key (never exposed to client)
 *   - Idempotent — re-processing the same event is safe
 *
 * Setup in RevenueCat dashboard:
 *   Project → Integrations → Webhooks → Add Endpoint
 *   URL: https://epic-fury-2026.vercel.app/api/webhooks/revenuecat
 *   Secret: set REVENUECAT_WEBHOOK_SECRET in Vercel env vars
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient }              from '@supabase/supabase-js'

export const runtime = 'nodejs'

const SUBSCRIBER_EVENTS = new Set([
  'INITIAL_PURCHASE',
  'RENEWAL',
  'UNCANCELLATION',
  'PRODUCT_CHANGE',
])

const FREE_EVENTS = new Set([
  'CANCELLATION',
  'EXPIRATION',
  'BILLING_ISSUE',
  'SUBSCRIBER_ALIAS',
])

export async function POST(req: NextRequest) {
  // ── Auth ──────────────────────────────────────────────────────────────────
  const secret = process.env.REVENUECAT_WEBHOOK_SECRET
  if (!secret) {
    // Fail closed: never accept unsigned webhook traffic.
    return NextResponse.json({ error: 'RevenueCat webhook not configured' }, { status: 503 })
  }

  const incoming = req.headers.get('X-RevenueCat-Secret') ?? ''
  if (incoming !== secret) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // ── Parse event ───────────────────────────────────────────────────────────
  let body: Record<string, unknown>
  try {
    body = await req.json() as Record<string, unknown>
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const event = body?.event as Record<string, unknown> | undefined
  if (!event) return NextResponse.json({ ok: true })   // unknown shape — ack

  const eventType    = String(event.type ?? '')
  const appUserId    = String(event.app_user_id ?? event.original_app_user_id ?? '')
  const aliasIds     = (event.aliases as string[] | undefined) ?? []

  if (!appUserId) return NextResponse.json({ ok: true })

  // ── Determine target role ─────────────────────────────────────────────────
  let targetRole: 'subscriber' | 'free' | null = null
  if (SUBSCRIBER_EVENTS.has(eventType)) targetRole = 'subscriber'
  else if (FREE_EVENTS.has(eventType)) targetRole = 'free'

  if (!targetRole) return NextResponse.json({ ok: true })   // unhandled event type

  // ── Apply role in Supabase ────────────────────────────────────────────────
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false } },
  )

  // RevenueCat app_user_id is the Supabase user UUID (set at login via Purchases.logIn)
  const candidates = [appUserId, ...aliasIds].filter(Boolean)

  for (const uid of candidates) {
    // Try UUID lookup first
    const { error } = await supabase.auth.admin.updateUserById(uid, {
      app_metadata: { role: targetRole },
    })
    if (!error) break   // success — stop after first match
  }

  return NextResponse.json({ ok: true })
}
