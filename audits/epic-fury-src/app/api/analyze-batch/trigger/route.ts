/**
 * POST /api/analyze-batch/trigger
 *
 * Operator-UI manual fire for the batch analysis pipeline.  No client-side
 * secret needed — CRON_SECRET is read server-side and forwarded to the
 * actual /api/analyze-batch GET handler internally.
 */
import { NextResponse } from 'next/server'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const maxDuration = 60

export async function POST(): Promise<NextResponse> {
  try {
    const secret  = process.env.CRON_SECRET
    const baseUrl = process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}`
      : (process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3003')

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(secret ? { Authorization: `Bearer ${secret}` } : {}),
    }

    const res  = await fetch(`${baseUrl}/api/analyze-batch`, { method: 'GET', headers, cache: 'no-store' })
    const data = await res.json()

    return NextResponse.json(data, { status: res.ok ? 200 : res.status })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error('[analyze-batch/trigger] failed:', msg)
    return NextResponse.json({ ok: false, error: msg }, { status: 500 })
  }
}
