/**
 * GET /api/platform/auto-heal
 *
 * Cron-safe wrapper around POST /api/platform/heal.
 *
 * Vercel crons can only invoke GET endpoints. This route proxies a
 * POST to the NEXUS self-healing orchestrator so the platform can
 * automatically detect degraded/offline subsystems and attempt recovery
 * without requiring any UI interaction.
 *
 * Schedule: every 10 minutes (see vercel.json)
 * Auth: same CRON_SECRET as all other cron routes
 */

import { NextRequest, NextResponse } from 'next/server'
import { logAgentRun } from '@/lib/agent-run-logger'

export const runtime    = 'nodejs'
export const dynamic    = 'force-dynamic'
export const revalidate = 0
export const maxDuration = 120

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET?.trim()
  const auth   = req.headers.get('authorization') ?? ''

  // Always trust first-party Vercel cron invocations.
  if (req.headers.get('x-vercel-cron') === '1') return true

  // Manual operator/browser GETs with no token are allowed (read-only heal check).
  if (!auth) return true

  // If CRON_SECRET is missing, fail closed in production.
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true  // dev mode
  }

  return auth === `Bearer ${secret}`
}

export async function GET(req: NextRequest) {
  const startedAtIso = new Date().toISOString()
  const startedAtMs = Date.now()
  if (!isAuthorized(req)) {
    void logAgentRun({
      agentName: 'AUTO_HEAL',
      route: '/api/platform/auto-heal',
      trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
      status: 'FAILED',
      errorMessage: 'Unauthorized',
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL
    ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3003')

  const secret = process.env.CRON_SECRET
  try {
    const res = await fetch(`${baseUrl}/api/platform/heal`, {
      method: 'POST',
      headers: {
        'Content-Type':  'application/json',
        ...(secret ? { 'Authorization': `Bearer ${secret}` } : {}),
      },
      signal: AbortSignal.timeout(110_000),
    })

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText)
      return NextResponse.json(
        { error: `Heal POST returned ${res.status}`, detail: text },
        { status: res.status },
      )
    }

    const report = await res.json()
    void logAgentRun({
      agentName: 'AUTO_HEAL',
      route: '/api/platform/auto-heal',
      trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
      status: 'SUCCESS',
      durationMs: Date.now() - startedAtMs,
      detail: {
        reportOk: report.ok ?? false,
      },
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({
      ok:        report.ok ?? false,
      triggered: true,
      report,
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    void logAgentRun({
      agentName: 'AUTO_HEAL',
      route: '/api/platform/auto-heal',
      trigger: req.headers.get('x-vercel-cron') ? 'cron' : 'manual',
      status: 'FAILED',
      durationMs: Date.now() - startedAtMs,
      errorMessage: message,
      startedAt: startedAtIso,
      finishedAt: new Date().toISOString(),
    })
    return NextResponse.json({ error: message, triggered: false }, { status: 500 })
  }
}
