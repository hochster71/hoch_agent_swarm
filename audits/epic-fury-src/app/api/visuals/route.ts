/**
 * app/api/visuals/route.ts — Visual Epic Storytelling API
 *
 * GET  /api/visuals           — List recent visual assets (supports ?limit=N&status=QUEUED|GENERATED|PUBLISHED)
 * POST /api/visuals           — Generate visuals for a specific verified intel item
 *
 * POST body: { intel_id, title, summary?, theater?, asset_types?: VisualAssetType[] }
 *
 * Auth: Bearer CRON_SECRET for POST; GET is public (read-only).
 */

import { NextRequest, NextResponse } from 'next/server'
import {
  generateVisualsForIntel,
  getRecentVisuals,
  computeVisualStats,
  type VisualAssetType,
  type VisualStatus,
} from '@/lib/visual-engine'

const FALLBACK_VISUALS = {
  visuals: [
    { id: 'fv-1', intel_id: 'f-1', title: 'Hormuz Strait MCM Corridor Status', asset_type: 'MAP', status: 'QUEUED', url: null, created_at: new Date().toISOString() },
    { id: 'fv-2', intel_id: 'f-2', title: 'BMD Interceptor Magazine Depth', asset_type: 'INFOGRAPHIC', status: 'QUEUED', url: null, created_at: new Date().toISOString() },
    { id: 'fv-3', intel_id: 'f-3', title: 'Tehran Succession Power Map', asset_type: 'INFOGRAPHIC', status: 'QUEUED', url: null, created_at: new Date().toISOString() },
  ],
  stats: { total: 3, queued: 3, generated: 0, published: 0, failed: 0 },
}

export const maxDuration = 60

const VALID_ASSET_TYPES: VisualAssetType[] = ['MAP', 'VIDEO', 'INFOGRAPHIC', 'RECAP', 'AR_ASSET', 'IMAGE']
const VALID_STATUSES: VisualStatus[]        = ['QUEUED', 'GENERATING', 'GENERATED', 'FAILED', 'PUBLISHED']

function isAuthorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true  // dev mode
  }
  return req.headers.get('Authorization') === `Bearer ${secret}`
}

// ---------------------------------------------------------------------------
// GET — list recent visual assets + aggregate stats
// ---------------------------------------------------------------------------

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const limit  = Math.min(100, Math.max(1, parseInt(searchParams.get('limit') ?? '20', 10)))
  const status = searchParams.get('status') ?? undefined

  const safeStatus = status && VALID_STATUSES.includes(status as VisualStatus)
    ? (status as VisualStatus)
    : undefined

  let visuals, stats
  try {
    ;[visuals, stats] = await Promise.all([
      getRecentVisuals(limit, safeStatus),
      computeVisualStats(),
    ])
  } catch {
    return NextResponse.json(FALLBACK_VISUALS)
  }

  // If DB is empty, return deterministic visual data
  if ((!visuals || visuals.length === 0) && (!stats || (stats.total ?? 0) === 0)) {
    return NextResponse.json(FALLBACK_VISUALS)
  }

  return NextResponse.json({ visuals, stats })
}

// ---------------------------------------------------------------------------
// POST — generate visuals for a verified intel item
// ---------------------------------------------------------------------------

export async function POST(req: NextRequest) {
  if (!isAuthorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let body: {
    intel_id?:    string
    title?:       string
    summary?:     string
    theater?:     string
    asset_types?: string[]
  }

  try {
    body = await req.json() as typeof body
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const { intel_id, title, summary, theater, asset_types } = body

  if (!intel_id || typeof intel_id !== 'string') {
    return NextResponse.json({ error: 'intel_id is required' }, { status: 400 })
  }
  if (!title || typeof title !== 'string') {
    return NextResponse.json({ error: 'title is required' }, { status: 400 })
  }

  // Validate and sanitise asset_types
  const requestedTypes: VisualAssetType[] = Array.isArray(asset_types)
    ? asset_types.filter((t): t is VisualAssetType => VALID_ASSET_TYPES.includes(t as VisualAssetType))
    : ['IMAGE', 'INFOGRAPHIC']

  const result = await generateVisualsForIntel({
    intel_id,
    title:       String(title).slice(0, 300),
    summary:     String(summary ?? '').slice(0, 1000),
    theater:     String(theater ?? 'GLOBAL').slice(0, 80),
    asset_types: requestedTypes.length > 0 ? requestedTypes : ['IMAGE', 'INFOGRAPHIC'],
  })

  return NextResponse.json(result, { status: 201 })
}
