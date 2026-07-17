/**
 * GET /api/market/prices
 *
 * Fetches live commodity prices for the COMPASS economic model.
 * Returns Brent crude spot (USD/bbl), WTI, and natural gas.
 *
 * Data sources (in priority order):
 *  1. Yahoo Finance public chart API  — no key required
 *  2. Static conflict-adjusted fallback — used if fetch fails
 *
 * Cached for 5 minutes at the edge (price volatility doesn't warrant more frequent polling).
 */

import { NextResponse }          from 'next/server'
import { computeEconomicCascade } from '@/lib/compass-engine'
import { getConflictDay }         from '@/lib/conflict-day'

export const revalidate = 300 // 5-minute edge cache

// COMPASS-modelled fallback — derived from conflict-day oil shock model.
// More accurate than a stale static value; updates automatically each day.
function getCompassFallback() {
  const cascade = computeEconomicCascade(getConflictDay(), 'CONTESTED')
  return {
    brentUsd:   cascade.brentUsd,
    // wtiDiscount is negative in CONTESTED/CLOSED (WTI trades above Brent when Hormuz is contested)
    wtiUsd:     Math.round((cascade.brentUsd - cascade.wtiDiscount) * 10) / 10,
    // COMPASS lngSpotUsd models Asian JKM LNG, not NYMEX Henry Hub NG=F.
    // Use a conflict-day-anchored Henry Hub value for the dashboard.
    ngUsdMmbtu: 3.59,
    source:     'compass-model' as const,
    stale:      false,
  }
}

interface PricesResponse {
  brentUsd:    number
  wtiUsd:      number
  ngUsdMmbtu:  number
  source:      string
  stale:       boolean
  fetchedAt:   string
}

async function fetchYahooPrice(ticker: string): Promise<number | null> {
  try {
    // Yahoo Finance v8 chart API — public, no key required
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=1d`
    const res = await fetch(url, {
      headers: {
        // Full browser UA — truncated UA strings get 403'd by Yahoo
        'User-Agent':      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept':          'application/json, */*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control':   'no-cache',
        'Pragma':          'no-cache',
      },
      signal: AbortSignal.timeout(6_000),
      cache:  'no-store',
    })
    if (!res.ok) return null
    const data = await res.json() as {
      chart?: { result?: Array<{ meta?: { regularMarketPrice?: number } }> }
    }
    const price = data.chart?.result?.[0]?.meta?.regularMarketPrice
    if (typeof price !== 'number' || price <= 0) return null
    // Sanity range: crude oil and NG must be plausibly priced
    if (price < 1 || price > 500) return null
    return Math.round(price * 100) / 100
  } catch {
    return null
  }
}

export async function GET(): Promise<NextResponse<PricesResponse>> {
  let brentUsd:   number | null = null
  let wtiUsd:     number | null = null
  let ngUsdMmbtu: number | null = null

  // Fetch in parallel with graceful per-ticker fallback
  const [brent, wti, ng] = await Promise.allSettled([
    fetchYahooPrice('BZ=F'),   // Brent Crude Futures
    fetchYahooPrice('CL=F'),   // WTI Crude Futures
    fetchYahooPrice('NG=F'),   // Natural Gas Futures
  ])

  if (brent.status  === 'fulfilled') brentUsd   = brent.value
  if (wti.status    === 'fulfilled') wtiUsd     = wti.value
  if (ng.status     === 'fulfilled') ngUsdMmbtu = ng.value

  // If any fetch failed, fill gaps with COMPASS model (dynamic, updates daily)
  const allLive = brentUsd !== null && wtiUsd !== null && ngUsdMmbtu !== null
  const fb = !allLive ? getCompassFallback() : null
  brentUsd   = brentUsd   ?? fb?.brentUsd   ?? 94
  wtiUsd     = wtiUsd     ?? fb?.wtiUsd     ?? 90
  ngUsdMmbtu = ngUsdMmbtu ?? fb?.ngUsdMmbtu ?? 3.2

  return NextResponse.json(
    {
      brentUsd,
      wtiUsd,
      ngUsdMmbtu,
      source:    allLive ? 'yahoo-finance' : (fb ? 'compass-model' : 'partial-fallback'),
      stale:     !allLive,
      fetchedAt: new Date().toISOString(),
    },
    {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    },
  )
}
