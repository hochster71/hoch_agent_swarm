/**
 * GET /api/platform/heartbeat
 *
 * Browser-safe proxy that triggers a governor heartbeat cycle (including
 * the Autonomous Enhancement Cycle) without exposing CRON_SECRET to the client.
 *
 * Called by the AutonomousPanel "Trigger Heartbeat" button.
 */

import { NextResponse } from 'next/server'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 300

export async function GET() {
  const secret  = process.env.CRON_SECRET?.trim()
  const appUrl  = process.env.NEXT_PUBLIC_SITE_URL
    ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3003')

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    // Vercel strips the Authorization header on same-deployment self-calls.
    // Use a custom header that the edge won't modify.
    ...(secret ? {
      'Authorization':           `Bearer ${secret}`,
      'X-Nexus-Internal-Token':  secret,
    } : {}),
  }

  try {
    const res  = await fetch(`${appUrl}/api/governor/heartbeat`, {
      method: 'GET',
      headers,
      signal: AbortSignal.timeout(290_000),
    })

    const data = await res.json().catch(() => ({ ok: res.ok }))
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 502 },
    )
  }
}
