/**
 * GET /api/news
 *
 * Aggregates RSS headlines from open, publicly accessible news feeds.
 * Caching: 5 minutes (Next.js route segment config)
 */

import { NextResponse } from 'next/server'
import { fetchAllNews, RSS_FEEDS_LIST } from '@/lib/news-fetcher'
import type { NewsItem } from '@/lib/news-fetcher'

export type { NewsItem }

export const revalidate  = 300  // cache for 5 minutes at the edge
export const maxDuration = 30   // allow up to 30s for concurrent RSS fetches (requires Vercel Pro/Hobby ≥2024)

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------
export async function GET() {
  try {
    const items = await fetchAllNews()

    // Compute summary stats for consumer use
    const singleSourceCount        = items.filter(i => i.singleSource).length
    const multiSourceCount         = items.filter(i => i.corroborationCount >= 2).length
    const crossIdeologicalCount    = items.filter(i => i.crossIdeological).length
    const kineticContradictionCount = items.filter(i => i.kineticContradiction).length
    const biasSpread = {
      left:   items.filter(i => i.mediaBias <= -0.5).length,
      center: items.filter(i => i.mediaBias > -0.5 && i.mediaBias < 0.5).length,
      right:  items.filter(i => i.mediaBias >= 0.5).length,
    }

    return NextResponse.json(
      {
        items,
        fetchedAt:        new Date().toISOString(),
        sources:          RSS_FEEDS_LIST.map((f) => f.name),
        verification: {
          totalStories:         items.length,
          singleSourceCount,
          multiSourceCount,
          crossIdeologicalCount,
          corroborationRate:    items.length > 0
            ? Math.round((multiSourceCount / items.length) * 100)
            : 0,
          biasSpread,
          kineticContradictionCount,
        },
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=60',
        },
      }
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Internal server error'
    return NextResponse.json(
      { error: message, items: [], sources: [] },
      { status: 500, headers: { 'Cache-Control': 'no-store' } }
    )
  }
}
