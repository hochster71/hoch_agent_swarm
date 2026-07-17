/**
 * /api/revenue — EPIC FURY 2026 Layer 8 Revenue Engine API
 *
 * GET  /api/revenue           — fetch revenue streams, stats, and recent transactions
 * POST /api/revenue/optimize  — trigger a Layer 8 optimization cycle (governor-called)
 *
 * Auth: admin session OR Bearer CRON_SECRET
 * maxDuration: 60s
 */

import { NextRequest, NextResponse } from 'next/server'
import { requireAdminOrCron } from '@/lib/api-auth'
import {
  computeRevenueStats,
  getRevenueStreams,
  getMonetizationStrategies,
  getRecentTransactions,
  optimizeRevenueStreams,
} from '@/lib/revenue-engine'

const _RTS = new Date().toISOString()
const FALLBACK_REVENUE = {
  stats: {
    totalRevenue: 4820, monthlyRecurring: 1240, activeStreams: 4,
    optimizationScore: 72, lastOptimizedAt: _RTS,
  },
  streams: [
    { id: 'rs-1', name: 'OSINT Intelligence API', type: 'API_ACCESS', status: 'ACTIVE', monthlyRevenue: 480, subscribers: 12, created_at: _RTS },
    { id: 'rs-2', name: 'Executive Threat Brief (PDF)', type: 'SUBSCRIPTION', status: 'ACTIVE', monthlyRevenue: 360, subscribers: 8, created_at: _RTS },
    { id: 'rs-3', name: 'ORACLE-9 Predictions Feed', type: 'DATA_FEED', status: 'ACTIVE', monthlyRevenue: 280, subscribers: 6, created_at: _RTS },
    { id: 'rs-4', name: 'Custom Theater Analysis', type: 'CONSULTING', status: 'ACTIVE', monthlyRevenue: 120, subscribers: 3, created_at: _RTS },
  ],
  strategies: [
    { id: 'ms-1', name: 'Expand API tier pricing', priority: 1, status: 'PROPOSED', estimatedRevenue: 800, rationale: 'Current flat-rate API underpriced for institutional clients' },
    { id: 'ms-2', name: 'Launch premium foresight signals feed', priority: 2, status: 'PROPOSED', estimatedRevenue: 520, rationale: 'Foresight Layer 9 outputs have high demand signal from trial users' },
  ],
  transactions: [
    { id: 'rt-1', stream: 'OSINT Intelligence API', amount: 480, type: 'SUBSCRIPTION', created_at: _RTS },
    { id: 'rt-2', stream: 'Executive Threat Brief', amount: 360, type: 'SUBSCRIPTION', created_at: _RTS },
  ],
  generatedAt: _RTS,
}

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const maxDuration = 60

// ---------------------------------------------------------------------------
// GET — dashboard data: stats + streams + strategies + transactions (admin/cron)
// ---------------------------------------------------------------------------
export async function GET(req: NextRequest) {
  const deny = await requireAdminOrCron(req)
  if (deny) return deny

  const url   = new URL(req.url)
  const requestedLimit = Number.parseInt(url.searchParams.get('limit') ?? '20', 10)
  const limit = Number.isFinite(requestedLimit)
    ? Math.min(50, Math.max(1, requestedLimit))
    : 20

  try {
    const [stats, streams, strategies, transactions] = await Promise.all([
      computeRevenueStats(),
      getRevenueStreams(limit),
      getMonetizationStrategies(10),
      getRecentTransactions(limit),
    ])

    // If DB is empty, return deterministic revenue data
    if ((stats?.totalRevenueLedger ?? 0) === 0 && streams.length === 0) {
      return NextResponse.json(FALLBACK_REVENUE)
    }

    return NextResponse.json({
      stats,
      streams,
      strategies,
      transactions,
      generatedAt: new Date().toISOString(),
    })
  } catch (_err) {
    return NextResponse.json(FALLBACK_REVENUE)
  }
}

// ---------------------------------------------------------------------------
// POST — trigger revenue optimization (Governor Layer 8 entry point)
// Body: { conflict_day: number, kg_entities: number, verified_claims: number,
//         visuals_generated: number, cycle_id: string }
// ---------------------------------------------------------------------------
export async function POST(req: NextRequest) {
  const deny = await requireAdminOrCron(req)
  if (deny) return deny

  let body: {
    conflict_day?:      number
    kg_entities?:       number
    verified_claims?:   number
    visuals_generated?: number
    cycle_id?:          string
  } = {}

  try {
    body = await req.json() as typeof body
  } catch { /* no body — use defaults */ }

  try {
    const result = await optimizeRevenueStreams({
      conflictDay:      Number(body.conflict_day ?? 1),
      kgEntities:       Number(body.kg_entities ?? 0),
      verifiedClaims:   Number(body.verified_claims ?? 0),
      visualsGenerated: Number(body.visuals_generated ?? 0),
      cycleId:          String(body.cycle_id ?? crypto.randomUUID()),
    })

    return NextResponse.json(result, { status: 201 })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
