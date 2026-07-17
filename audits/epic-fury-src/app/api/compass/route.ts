import { NextResponse } from 'next/server'
import { computeEconomicCascade, type ClosureSeverity } from '@/lib/compass-engine'
import { getConflictDay } from '@/lib/conflict-day'

// Force dynamic — fetches live Brent crude price each request
export const revalidate = 0

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const severityParam = (searchParams.get('severity') ?? 'CONTESTED').toUpperCase() as ClosureSeverity
    const baselineParam = parseFloat(searchParams.get('baseline') ?? '78')

    const validSeverities: ClosureSeverity[] = ['PARTIAL', 'CONTESTED', 'CLOSED']
    const severity   = validSeverities.includes(severityParam) ? severityParam : 'CONTESTED'
    const baseline   = isNaN(baselineParam) || baselineParam < 20 || baselineParam > 300 ? 78 : baselineParam

    const day    = getConflictDay()

    // Fetch live Brent crude — override the query-param baseline if we get a real price
    let liveBrent = baseline
    try {
      const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : 'http://localhost:3003')
      const priceRes = await fetch(`${baseUrl}/api/market/prices`, {
        next: { revalidate: 300 },
      })
      if (priceRes.ok) {
        const prices = await priceRes.json() as { brentUsd?: number }
        if (prices.brentUsd && prices.brentUsd > 20) liveBrent = prices.brentUsd
      }
    } catch { /* non-fatal — use query-param or default */ }

    const result = computeEconomicCascade(day, severity, liveBrent)

    return NextResponse.json(
      {
        cascade:      result,
        conflictDay:  day,
        generatedAt:  new Date().toISOString(),
        modelVersion: 'COMPASS-2.1',
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=120',
        },
      },
    )
  } catch (err) {
    const message = err instanceof Error ? err.message : 'COMPASS engine error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
