import { NextResponse } from 'next/server'
import { scoreHeadlines } from '@/lib/herald-engine'

// Re-score every 5 minutes (news changes slowly; HERALD score is deterministic)
export const revalidate = 300

export async function GET(request: Request) {
  try {
    const { origin } = new URL(request.url)

    // Pull fresh news from our aggregator
    const newsRes = await fetch(`${origin}/api/news`, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(30_000),
    })

    if (!newsRes.ok) {
      return NextResponse.json({ error: 'Failed to fetch news feed' }, { status: 502 })
    }

    const newsData = await newsRes.json() as {
      items: Array<{
        title:     string
        url:       string
        source:    string
        pubDate?:  string
        summary?:  string
      }>
    }

    const items = (newsData.items ?? []).slice(0, 100)

    const scored = scoreHeadlines(
      items.map(i => ({
        title:  i.title,
        url:    i.url,
        source: i.source,
        body:   i.summary ?? '',
      })),
    )

    // Segment by risk tier
    const critical = scored.filter(s => s.herald.risk === 'CRITICAL')
    const high     = scored.filter(s => s.herald.risk === 'HIGH')
    const moderate = scored.filter(s => s.herald.risk === 'MODERATE')
    const clean    = scored.filter(s => s.herald.risk === 'CLEAN' || s.herald.risk === 'LOW')

    return NextResponse.json(
      {
        scored,
        summary: {
          total:    scored.length,
          critical: critical.length,
          high:     high.length,
          moderate: moderate.length,
          clean:    clean.length,
          topFlag:  critical[0]?.herald.flags[0]?.description ?? high[0]?.herald.flags[0]?.description ?? null,
        },
        generatedAt:  new Date().toISOString(),
        modelVersion: 'HERALD-3.1',
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=60',
        },
      },
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : 'HERALD engine error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
