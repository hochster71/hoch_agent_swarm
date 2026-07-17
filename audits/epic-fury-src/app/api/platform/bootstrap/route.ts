/**
 * GET /api/platform/bootstrap
 *
 * Server-side proxy that triggers the ingest pipeline from the dashboard UI.
 * No auth required from the client — CRON_SECRET is added server-side so the
 * secret is never exposed to the browser.
 *
 * Called by PlatformHealth component on auto-bootstrap when HERALD has never run.
 *
 * Fire-and-forget: returns 202 immediately so the client never sees a 502
 * even if ingest is slow or fails. Ingest outcome is logged server-side only.
 */

import { after }       from 'next/server'
import { NextResponse } from 'next/server'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 30  // returns 202 fast; ingest runs in after()

export async function GET() {
  const secret = process.env.CRON_SECRET
  // Prefer explicit site URL; fallback to Vercel deployment URL
  const appUrl = process.env.NEXT_PUBLIC_SITE_URL
    ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3003')

  const headers: HeadersInit = secret ? { Authorization: `Bearer ${secret}` } : {}

  // Fire ingest + analyze-batch in parallel in the background — never block the client response
  after(async () => {
    const ingestUrl       = `${appUrl}/api/ingest`
    const analyzeBatchUrl = `${appUrl}/api/analyze-batch`

    const [ingestRes, batchRes] = await Promise.allSettled([
      fetch(ingestUrl, {
        cache: 'no-store',
        headers,
        signal: AbortSignal.timeout(290_000),
      }),
      // Small delay so analyze-batch runs after ingest has a head start
      new Promise<Response>(resolve => setTimeout(resolve, 10_000)).then(() =>
        fetch(analyzeBatchUrl, {
          cache: 'no-store',
          headers,
          signal: AbortSignal.timeout(60_000),
        })
      ),
    ])

    if (ingestRes.status === 'fulfilled') {
      const data = await ingestRes.value.json().catch(() => ({}))
      console.warn('[bootstrap] ingest completed', ingestRes.value.status, JSON.stringify(data).slice(0, 200))
    } else {
      console.error('[bootstrap] ingest error:', ingestRes.reason)
    }

    if (batchRes.status === 'fulfilled') {
      const data = await batchRes.value.json().catch(() => ({}))
      console.warn('[bootstrap] analyze-batch completed', batchRes.value.status, JSON.stringify(data).slice(0, 200))
    } else {
      console.error('[bootstrap] analyze-batch error:', batchRes.reason)
    }
  })

  return NextResponse.json({ ok: true, status: 'INGEST_TRIGGERED', message: 'Pipeline bootstrap fired — check logs for result.' }, { status: 202 })
}
