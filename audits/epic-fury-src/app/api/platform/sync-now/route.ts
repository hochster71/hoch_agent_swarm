/**
 * POST /api/platform/sync-now
 *
 * On-demand full-pipeline sync. Chains ingest → analyze-batch → cross-ref →
 * digest sequentially so callers get a complete, cited content refresh in a
 * single request rather than waiting for individual cron windows.
 *
 * Auth: Bearer CRON_SECRET  (required even in dev when CRON_SECRET is set)
 *
 * Request body (optional JSON):
 *   { force?: boolean }   // if true, bypasses the 5-minute anti-stampede guard
 *
 * Response:
 *   {
 *     ok: boolean
 *     stages: Record<string, { ok: boolean; status: number; durationMs: number }>
 *     totalDurationMs: number
 *     generatedAt: string
 *   }
 *
 * Vercel maxDuration is capped at 60 s on most plans; the ingest stage alone
 * can take ~30 s, so this route fires sub-calls with AbortSignal timeouts and
 * returns whatever each stage completed within the budget.
 */

import { NextRequest, NextResponse } from 'next/server'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0
export const maxDuration = 60

// Minimum gap between forced syncs (5 min) — prevents accidental hammering
const SYNC_COOLDOWN_MS = 5 * 60_000
let _lastSyncMs = 0

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET?.trim()
  if (!secret) {
    // No secret configured — allow in dev, block in prod
    return process.env.NODE_ENV !== 'production'
  }
  const auth = req.headers.get('authorization') ?? ''
  return auth === `Bearer ${secret}`
}

function getBaseUrl(req: NextRequest): string {
  if (process.env.NEXT_PUBLIC_SITE_URL) return process.env.NEXT_PUBLIC_SITE_URL
  if (process.env.VERCEL_URL)           return `https://${process.env.VERCEL_URL}`
  return req.nextUrl.origin || 'http://localhost:3003'
}

async function callStage(
  baseUrl: string,
  path: string,
  secret: string,
  timeoutMs: number,
): Promise<{ ok: boolean; status: number; durationMs: number }> {
  const t0 = Date.now()
  try {
    const res = await fetch(`${baseUrl}${path}`, {
      headers: {
        authorization: `Bearer ${secret}`,
        'x-vercel-cron': '1',
      },
      signal: AbortSignal.timeout(timeoutMs),
      cache: 'no-store',
    })
    return { ok: res.ok, status: res.status, durationMs: Date.now() - t0 }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    const timedOut = msg.includes('TimeoutError') || msg.includes('AbortError')
    return { ok: false, status: timedOut ? 408 : 500, durationMs: Date.now() - t0 }
  }
}

export async function POST(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let force = false
  try {
    const body = await req.json().catch(() => ({}))
    force = Boolean(body?.force)
  } catch { /* ignore */ }

  const now = Date.now()
  if (!force && now - _lastSyncMs < SYNC_COOLDOWN_MS) {
    return NextResponse.json({
      ok:             false,
      skipped:        true,
      reason:         'cooldown',
      nextEligibleMs: Math.round(SYNC_COOLDOWN_MS - (now - _lastSyncMs)),
      generatedAt:    new Date().toISOString(),
    }, { status: 429 })
  }
  _lastSyncMs = now

  const baseUrl = getBaseUrl(req)
  const secret  = process.env.CRON_SECRET ?? ''
  const t0      = Date.now()

  // ── Stage pipeline ────────────────────────────────────────────────────────
  // Each stage fires with a hard timeout so one slow stage doesn't kill the rest.
  // analyze-batch and cross-ref run in parallel after ingest completes.
  const stages: Record<string, { ok: boolean; status: number; durationMs: number }> = {}

  // Stage 1: Ingest — pull and store fresh headlines (up to 28 s)
  stages.ingest = await callStage(baseUrl, '/api/ingest', secret, 28_000)

  // Stage 2: Analyze-batch + cross-ref in parallel (up to 20 s each)
  const [batchResult, crossRefResult] = await Promise.allSettled([
    callStage(baseUrl, '/api/analyze-batch',    secret, 20_000),
    callStage(baseUrl, '/api/intel/cross-ref',  secret, 20_000),
  ])
  stages['analyze-batch'] = batchResult.status === 'fulfilled' ? batchResult.value : { ok: false, status: 500, durationMs: 0 }
  stages['cross-ref']     = crossRefResult.status === 'fulfilled' ? crossRefResult.value : { ok: false, status: 500, durationMs: 0 }

  // Stage 3: Digest (depends on analyze-batch completing) — up to 15 s
  stages.digest = await callStage(baseUrl, '/api/intel/digest', secret, 15_000)

  const totalDurationMs = Date.now() - t0
  const allOk = Object.values(stages).every(s => s.ok)

  return NextResponse.json({
    ok: allOk,
    stages,
    totalDurationMs,
    generatedAt: new Date().toISOString(),
  }, { status: allOk ? 200 : 207 })
}
