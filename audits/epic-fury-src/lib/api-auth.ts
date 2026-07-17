/**
 * lib/api-auth.ts
 *
 * Shared API authentication helpers.
 *
 * requireCronAuth(req) — only Vercel cron scheduler or CRON_SECRET bearer token may call the route.
 * requireSubscriber(req) — valid Supabase session required (subscriber or admin).
 *
 * Usage:
 *   const deny = requireCronAuth(req)
 *   if (deny) return deny
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { getEntitlement } from '@/lib/entitlements'

// ---------------------------------------------------------------------------
// Cron / admin-only gate
// Vercel Cron sends x-vercel-cron: 1 on all scheduled invocations.
// External / manual callers must send Authorization: Bearer <CRON_SECRET>.
// ---------------------------------------------------------------------------
export function requireCronAuth(req: NextRequest): NextResponse | null {
  // Vercel's own cron infrastructure always sends x-vercel-cron: 1.
  // This header is only injected by Vercel itself, so it's safe to trust.
  if (req.headers.get('x-vercel-cron') === '1') return null

  const secret = process.env.CRON_SECRET
  if (!secret) {
    // No CRON_SECRET and not a Vercel cron call — fail closed in production
    if (process.env.NODE_ENV === 'production') {
      return NextResponse.json({ error: 'Service unavailable' }, { status: 503 })
    }
    return null // dev: allow through
  }

  const auth = req.headers.get('authorization') ?? ''
  if (auth === `Bearer ${secret}`) return null

  return NextResponse.json({ error: 'Unauthorized' }, {
    status: 401,
    headers: { 'WWW-Authenticate': 'Bearer realm="NEXUS"' },
  })
}

type UserRole = 'admin' | 'subscriber' | 'free'

async function resolveUserRole(req: NextRequest): Promise<UserRole> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !key) return 'free'

  try {
    const res = NextResponse.next()
    const supabase = createServerClient(url, key, {
      cookies: {
        getAll: () => req.cookies.getAll(),
        setAll: (cs: Array<{ name: string; value: string; options?: Record<string, unknown> }>) =>
          cs.forEach(({ name, value, options }) =>
            res.cookies.set(name, value, (options ?? {}) as Parameters<typeof res.cookies.set>[2]),
          ),
      },
    })

    const { data } = await supabase.auth.getSession()
    const user = data.session?.user ?? null
    const entitlement = getEntitlement(user)
    if (!entitlement.hasAccess) return 'free'
    if (entitlement.role === 'founder' || entitlement.role === 'admin' || entitlement.role === 'qa') return 'admin'
    return 'subscriber'
  } catch {
    return 'free'
  }
}

// ---------------------------------------------------------------------------
// Subscriber session gate — requires valid logged-in Supabase session
// ---------------------------------------------------------------------------
export async function requireSubscriber(req: NextRequest): Promise<NextResponse | null> {
  const role = await resolveUserRole(req)
  if (role === 'free') {
    // Return 403 (not 401) so clients can distinguish "need to sign in" from
    // a true upstream API key failure (which comes back as 401 from ElevenLabs).
    return NextResponse.json({ error: 'Forbidden', reason: 'session_required' }, { status: 403 })
  }
  return null
}

export async function requireAdmin(req: NextRequest): Promise<NextResponse | null> {
  const role = await resolveUserRole(req)
  if (role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden', reason: 'admin_required' }, { status: 403 })
  }
  return null
}

export async function requireAdminOrCron(req: NextRequest): Promise<NextResponse | null> {
  const cronDeny = requireCronAuth(req)
  if (!cronDeny) return null

  const adminDeny = await requireAdmin(req)
  if (!adminDeny) return null

  return NextResponse.json({ error: 'Forbidden', reason: 'admin_or_cron_required' }, { status: 403 })
}
