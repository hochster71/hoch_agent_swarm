/**
 * GET /api/ingest
 *
 * Master autonomous ingestion pipeline — called by Vercel Cron every 5 minutes.
 * Also callable manually via browser or curl.
 *
 * Pipeline steps:
 *  1. Fetch live headlines from /api/news (RSS aggregator)
 *  2. Score each headline with the HERALD-3 IO/threat engine
 *  3. Run ORACLE-9 Bayesian threat model
 *  4. Run COMPASS economic cascade model
 *  5. Write CRITICAL/HIGH headlines as new Intel rows to Supabase (dedup by URL)
 *  6. Write model snapshot (ORACLE + COMPASS) to model_snapshots table
 *
 * Auth: protected by CRON_SECRET header (set in Vercel env / .env.local)
 * Service-role key: SUPABASE_SERVICE_ROLE_KEY (write access bypasses RLS)
 */

import { NextRequest, NextResponse, after } from 'next/server'
import { createClient }              from '@supabase/supabase-js'
import { scoreHeadlines, isConflictRelevant } from '@/lib/herald-engine'
import { computeAllThreats }         from '@/lib/oracle-engine'
import { computeEconomicCascade }    from '@/lib/compass-engine'
import { getConflictDay }            from '@/lib/conflict-day'
import { AI_AVAILABLE, enhanceSummary, assessPipelineHealth, detectContradictions, setGroundTruth, buildGroundTruthDigest, deduplicateHeadlines } from '@/lib/ai-engine'
import { buildCitation, buildCitationTags } from '@/lib/citation-tracker'
import type { NewsItem }             from '@/lib/news-fetcher'
import { fetchAllNews }              from '@/lib/news-fetcher'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 300  // master pipeline: RSS fetch + AI enhancement + DB writes

// ── Pipeline self-tuning state ─────────────────────────────────────────────
// These are adjusted per-run by the assessPipelineHealth feedback loop.
// Persisted in-process between cron invocations (resets on cold start).
let _expandedTheaters: Set<string> = new Set()      // theaters where we capture MEDIUM too
let _boostedSources: Set<string>   = new Set()      // sources whose confidence gets +8 boost
let _lastHealthCheckMs = 0

// ── Auth guard ─────────────────────────────────────────────────────────────
// Vercel Cron sends: Authorization: Bearer <CRON_SECRET>
// Local testing: omit header (allowed when CRON_SECRET is unset)
function isAuthorised(req: NextRequest): boolean {
  // Vercel cron always sends x-vercel-cron: 1 — trust it (only Vercel infra sets this)
  if (req.headers.get('x-vercel-cron') === '1') return true
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true  // dev mode
  }
  const auth = req.headers.get('authorization') ?? ''
  return auth === `Bearer ${secret}`
}

// ── Supabase service-role client (bypasses RLS for writes) ─────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyClient = ReturnType<typeof createClient<any>>

function getServiceClient(): AnyClient | null {
  const url     = process.env.NEXT_PUBLIC_SUPABASE_URL
  const svcKey  = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !svcKey) return null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return createClient<any>(url, svcKey, {
    auth: { persistSession: false },
  })
}

// ── Conflict day / theater inference ───────────────────────────────────────
const THEATER_KEYWORDS: Record<string, string> = {
  hormuz: 'Persian Gulf / Hormuz', gulf: 'Persian Gulf / Hormuz',
  naval: 'Persian Gulf / Hormuz', ship: 'Persian Gulf / Hormuz',
  tanker: 'Persian Gulf / Hormuz', mine: 'Persian Gulf / Hormuz',
  missile: 'Iran', irgc: 'Iran', ballistic: 'Iran',
  nuclear: 'Iran', natanz: 'Iran', fordow: 'Iran',
  israel: 'Israel / Levant', hezbollah: 'Israel / Levant', beirut: 'Israel / Levant',
  red: 'Red Sea / Yemen', houthi: 'Red Sea / Yemen', yemen: 'Red Sea / Yemen',
  gcc: 'GCC / Arabian Peninsula', saudi: 'GCC / Arabian Peninsula', uae: 'GCC / Arabian Peninsula',
  cyber: 'Cyber', cisa: 'Cyber', apt: 'Cyber',
  conus: 'CONUS', homeland: 'CONUS', fbi: 'CONUS',
}

function inferTheater(title: string): string {
  const lower = title.toLowerCase()
  for (const [kw, theater] of Object.entries(THEATER_KEYWORDS)) {
    if (lower.includes(kw)) return theater
  }
  return 'Unknown'
}

function inferTags(title: string, category: string): string[] {
  const tags: string[] = [category.toLowerCase().replace(/_/g, '-')]
  const lower = title.toLowerCase()
  if (lower.includes('missile') || lower.includes('ballistic')) tags.push('missile')
  if (lower.includes('drone') || lower.includes('shahed'))      tags.push('drone')
  if (lower.includes('naval') || lower.includes('ship'))        tags.push('naval')
  if (lower.includes('nuclear') || lower.includes('uranium'))   tags.push('nuclear')
  if (lower.includes('cyber') || lower.includes('apt'))         tags.push('cyber')
  if (lower.includes('ceasefire') || lower.includes('talks'))   tags.push('diplomacy')
  return [...new Set(tags)]
}

// ── Main handler ────────────────────────────────────────────────────────────
export async function GET(req: NextRequest) {
  const startMs = Date.now()

  if (!isAuthorised(req)) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 })
  }

  const conflictDay = getConflictDay()
  const results = {
    news:      { fetched: 0, scored: 0, critical: 0, high: 0, conflictRelevant: 0 },
    intel:     { inserted: 0, skipped: 0, errors: 0, aiEnhanced: 0, semanticDedups: 0, contradictions: 0 },
    oracle:    { threats: 0, topThreat: '' },
    compass:   { severity: 'CONTESTED', brentUsd: 0 },
    snapshot:  { written: false },
    aiAvailable: AI_AVAILABLE,
    pipelineSelfTuned: false,
    durationMs: 0,
  }

  // ── Run pipeline health check every 30 min to self-tune thresholds ─────
  if (AI_AVAILABLE && Date.now() - _lastHealthCheckMs > 30 * 60_000) {
    try {
      const supabaseCheck = getServiceClient()
      if (supabaseCheck) {
        const { count: totalCount } = await supabaseCheck.from('intel').select('count', { count: 'exact', head: true }).then(r => r as { count: number })
        const { count: verifiedCount } = await supabaseCheck.from('intel').select('count', { count: 'exact', head: true }).eq('verified', true).then(r => r as { count: number })
        const { data: srcData } = await supabaseCheck.from('intel').select('source_name').gte('created_at', new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString()).limit(200)
        const { data: theaterData } = await supabaseCheck.from('intel').select('theater').gte('created_at', new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString()).limit(300)
        const { data: lastRow } = await supabaseCheck.from('intel').select('created_at').order('created_at', { ascending: false }).limit(1)

        const totalSafe         = totalCount ?? 0
        const verifiedSafe      = verifiedCount ?? 0
        const allSources        = Array.from(new Set((srcData ?? []).map((r: { source_name: string | null }) => r.source_name).filter(Boolean))) as string[]
        const activeTheaters    = new Set((theaterData ?? []).map((r: { theater: string | null }) => r.theater).filter(Boolean)) as Set<string>
        const knownTheaters     = ['Persian Gulf / Hormuz', 'Iran', 'Israel / Levant', 'Red Sea / Yemen', 'GCC / Arabian Peninsula', 'Cyber', 'CONUS']
        const zeroTheaters      = knownTheaters.filter(t => !activeTheaters.has(t))
        const lastRowDate       = lastRow?.[0]?.created_at ? new Date(lastRow[0].created_at) : null
        const lastIngestAge     = lastRowDate ? Math.floor((Date.now() - lastRowDate.getTime()) / 60_000) : 999

        const health = await assessPipelineHealth({
          totalIntel:            totalSafe,
          verifiedRatio:         totalSafe > 0 ? verifiedSafe / totalSafe : 0,
          sourceCount:           allSources.length,
          topSources:            allSources.slice(0, 5),
          theatersWithZeroIntel: zeroTheaters,
          lastIngestAge,
        })

        if (health) {
          // Apply recommendations: expand capture for identified coverage gaps
          if (health.lowerScoreThresholdForTheaters?.length) {
            _expandedTheaters = new Set(health.lowerScoreThresholdForTheaters.map(t => t.toLowerCase()))
          }
          if (health.boostConfidenceForSources?.length) {
            _boostedSources = new Set(health.boostConfidenceForSources.map(s => s.toLowerCase()))
          }
          _lastHealthCheckMs = Date.now()
          results.pipelineSelfTuned = true
        }

        // ── Ground Truth Builder — compile verified facts for AI context ──
        // Runs alongside health check (every 30 min). Feeds setGroundTruth()
        // which injects verified facts into ALL subsequent AI prompts.
        try {
          const { data: verifiedRows } = await supabaseCheck
            .from('intel')
            .select('title,theater,confidence')
            .eq('verified', true)
            .gte('confidence', 60)
            .gte('created_at', new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString())
            .order('confidence', { ascending: false })
            .limit(25)

          if (verifiedRows && verifiedRows.length > 0) {
            const digest = await buildGroundTruthDigest(
              verifiedRows.map((r: { title?: string; theater?: string; confidence?: number }) => ({
                title:      r.title ?? '',
                theater:    r.theater ?? 'Unknown',
                confidence: r.confidence ?? 60,
              })),
            )
            if (digest) setGroundTruth(digest)
          }
        } catch {
          // Non-fatal — AI prompts continue without ground truth
        }
      }
    } catch {
      // Non-fatal — continue with existing thresholds
    }
  }

  // 1. Fetch headlines ────────────────────────────────────────────────────
  // Import fetchAllNews directly — avoids Vercel self-referencing fetch issues
  function getSiteBaseUrl(): string {
    if (process.env.NEXT_PUBLIC_SITE_URL) return process.env.NEXT_PUBLIC_SITE_URL
    if (process.env.VERCEL_URL)           return `https://${process.env.VERCEL_URL}`
    return 'http://localhost:3003'
  }
  const siteBaseUrl = getSiteBaseUrl()

  let newsItems: NewsItem[] = []
  try {
    newsItems = await fetchAllNews()
  } catch {
    // Non-fatal — proceed with empty items
  }
  results.news.fetched = newsItems.length

  // 2. Score with HERALD-3 ────────────────────────────────────────────────
  const scored = scoreHeadlines(newsItems.map((n) => ({
    title: n.title, url: n.url, source: n.source, body: n.summary,
  })))
  results.news.scored   = scored.length
  results.news.critical = scored.filter((s) => s.herald.risk === 'CRITICAL').length
  results.news.high     = scored.filter((s) => s.herald.risk === 'HIGH').length

  // 3. Write critical + high intel to Supabase ───────────────────────────
  const supabase = getServiceClient()
  if (supabase) {
    // ── Dimension 1: IO-flagged items (disinformation / information-ops risk) ──
    const ioFlagged = scored.filter((s) => {
      if (s.herald.risk === 'CRITICAL' || s.herald.risk === 'HIGH') return true
      if (s.herald.risk === 'MODERATE') {
        const news = newsItems.find((n) => n.url === s.url)
        if (!news) return false
        const theater = inferTheater(news.title).toLowerCase()
        return [..._expandedTheaters].some(t => theater.includes(t) || t.includes(theater))
      }
      return false
    })

    // ── Dimension 2: Conflict-relevant headlines from ANY IO risk level ────────
    // This captures REAL war news from credible sources (Reuters, AP, BBC, etc.)
    // that score LOW/CLEAN on IO risk because they are legitimate journalism.
    const ioUrls = new Set(ioFlagged.map(s => s.url))
    const conflictItems = scored
      .filter(s => !ioUrls.has(s.url))
      .filter(s => {
        const news = newsItems.find((n) => n.url === s.url)
        return news ? isConflictRelevant(news.title) : false
      })
      .slice(0, 20) // cap per cycle to prevent flooding

    results.news.conflictRelevant = conflictItems.length
    const actionable = [...ioFlagged, ...conflictItems]

    // ── Semantic Dedup — remove near-duplicate headlines before insert ───
    // Uses trigram Jaccard similarity (no API call) to catch paraphrased
    // wire rewrites that would otherwise create duplicate intel rows.
    const dedup = deduplicateHeadlines(actionable.map(a => {
      const news = newsItems.find(n => n.url === a.url)
      return news?.title ?? ''
    }))
    const keepSet = new Set(dedup.keepIndices)
    const dedupedActionable = actionable.filter((_, i) => keepSet.has(i))
    results.intel.semanticDedups = actionable.length - dedupedActionable.length

    // Track inserted item metadata for post-insert contradiction detection
    const insertedItems: { index: number; title: string; source: string; id?: string }[] = []

    // ── Batch URL dedup — one query instead of N serial .single() calls ───────
    // Previous: for each of up to 40 items, one SELECT … WHERE source_url = $x
    //           → up to 40 serial round-trips before any insert begins
    // Now: one SELECT … WHERE source_url IN ($x, $y, …) and build a Set
    //       → 1 round-trip, same correctness, dramatically lower latency
    const candidateUrls = dedupedActionable
      .map(a => a.url)
      .filter(Boolean)
    const { data: existingRows } = await supabase
      .from('intel')
      .select('source_url')
      .in('source_url', candidateUrls)
    const existingUrlSet = new Set(
      (existingRows ?? []).map((r: { source_url: string | null }) => r.source_url).filter(Boolean)
    )

    for (const item of dedupedActionable) {
      const news = newsItems.find((n) => n.url === item.url)
      if (!news) continue

      // Dedup — check against pre-fetched Set (no extra DB round-trip)
      if (existingUrlSet.has(item.url)) { results.intel.skipped++; continue }

      const h          = item.herald
      const sourceLower = (news.source ?? '').toLowerCase()
      const sourceBoost = [..._boostedSources].some(s => sourceLower.includes(s)) ? 8 : 0
      // For IO-flagged items, confidence is IO-score driven.
      // For conflict-relevant items (IO score near 0), use source credibility instead.
      const newsCredibility = (news as { credibility?: number }).credibility ?? 0
      const baseConf = h.score >= 15
        ? 50 + h.score * 0.8
        : Math.max(55, newsCredibility * 0.85) // credible sources like Reuters/AP → 68-80
      const confidence = Math.min(95, Math.round(baseConf) + sourceBoost)
      const theater    = inferTheater(news.title)
      const tags       = inferTags(news.title, h.categories[0] ?? 'osint')

      const { error } = await supabase.from('intel').insert({
        title:       news.title.slice(0, 280),
        summary:     news.summary.slice(0, 600) || `${h.risk} IO/threat signal detected. Score: ${h.score}. Category: ${h.categories[0] ?? 'n/a'}. Matched: ${h.flags[0]?.matched ?? 'n/a'}.`,
        theater,
        confidence,
        source_url:  item.url,
        source_name: news.source,
        source_type: 'OSINT',
        verified:    false,
        tags,
        author:      'HERALD-3',
      })

      if (error) {
        results.intel.errors++
        continue
      }
      results.intel.inserted++

      // Track for post-insert contradiction detection and AI enhancement queue
      insertedItems.push({
        index: insertedItems.length,
        title: news.title,
        source: news.source,
        // Carry forward fields needed for parallel AI enhancement below
        _url:  item.url,
        _summary: news.summary,
        _heraldRisk: h.risk,
        _tags: tags,
      } as typeof insertedItems[0] & { _url: string; _summary: string; _heraldRisk: string; _tags: string[] })
    }

    // ── Parallel AI enhancement ─────────────────────────────────────────────
    // Previous pattern: serial `await enhanceSummary(...)` inside the insert
    // loop → wall-time ≈ N × ~1.5 s (each call blocks the next insert).
    // Now: all inserts complete first; then up to 10 AI calls fire concurrently
    // via Promise.allSettled, reducing enhancement wall-time by ~10×.
    // Output: identical DB writes, identical error isolation (non-fatal).
    if (AI_AVAILABLE) {
      const enhancementCandidates = (
        insertedItems as (typeof insertedItems[0] & { _url?: string; _summary?: string; _heraldRisk?: string; _tags?: string[] })[]
      ).filter(it => {
        const risk = it._heraldRisk ?? ''
        return it._url &&
          (risk === 'CRITICAL' || risk === 'HIGH' || isConflictRelevant(it.title))
      }).slice(0, 10)

      const enhancementResults = await Promise.allSettled(
        enhancementCandidates.map(async (it) => {
          const url     = it._url!
          const summary = it._summary ?? ''
          const tags    = it._tags ?? []

          const enhanced = await enhanceSummary(it.title, summary, url, it.source)
          if (!enhanced) return

          const citation = buildCitation({
            title:      it.title,
            sourceName: it.source,
            sourceUrl:  url,
            sourceType: 'OSINT',
            index:      0,
          })
          const citationTags = buildCitationTags(citation)
          const kfTags = enhanced.keyFacts
            .slice(0, 3)
            .map((f, i) => `kf${i}:${f.slice(0, 80)}`)

          await supabase.from('intel').update({
            summary: `${enhanced.summary}\n\nKEY FACTS:\n${enhanced.keyFacts.map((f, i) => `${i + 1}. ${f}`).join('\n')}\n\nSOURCE: ${enhanced.citation}`,
            tags:    [...new Set([...tags, 'ai_enhanced', ...kfTags, ...citationTags])],
            author:  'HERALD-3+AI',
          }).eq('source_url', url)
        })
      )

      results.intel.aiEnhanced = enhancementResults.filter(r => r.status === 'fulfilled').length
    }

    // ── Post-insert: Contradiction Detection (AI-powered) ─────────────
    // After inserting new items, check the batch for contradictory claims.
    // Tag contradicting items so the UI can surface warnings.
    if (AI_AVAILABLE && insertedItems.length >= 2) {
      try {
        const contradictions = await detectContradictions(insertedItems)
        if (contradictions && contradictions.length > 0) {
          results.intel.contradictions = contradictions.length
          for (const c of contradictions) {
            const itemA = insertedItems[c.indexA]
            const itemB = insertedItems[c.indexB]
            if (!itemA || !itemB) continue

            // Tag both items as contradiction-flagged in Supabase
            for (const item of [itemA, itemB]) {
              const { data: row } = await supabase
                .from('intel')
                .select('id,tags')
                .eq('source_url', dedupedActionable.find(a => {
                  const n = newsItems.find(nn => nn.url === a.url)
                  return n?.title === item.title
                })?.url ?? '')
                .single()

              if (row) {
                const tags = Array.isArray(row.tags) ? [...row.tags] : []
                if (!tags.includes('contradiction-flagged')) {
                  tags.push('contradiction-flagged')
                  tags.push(`contradiction:${c.severity}`)
                  await supabase.from('intel').update({ tags }).eq('id', row.id)
                }
              }
            }
          }
        }
      } catch {
        // Non-fatal — continue without contradiction detection
      }
    }
  }

  // 4. Run ORACLE-9 ──────────────────────────────────────────────────────
  const threats = computeAllThreats(conflictDay)
  results.oracle.threats    = threats.length
  results.oracle.topThreat  = threats[0]?.label ?? ''

  // 5. Run COMPASS ───────────────────────────────────────────────────────
  const cascade = computeEconomicCascade(conflictDay, 'CONTESTED')
  results.compass.brentUsd  = cascade.brentUsd
  results.compass.severity  = 'CONTESTED'

  // 6. Write model snapshot ──────────────────────────────────────────────
  if (supabase) {
    const { error } = await supabase.from('model_snapshots').insert({
      conflict_day:   conflictDay,
      oracle_payload: threats          as unknown as Record<string, unknown>,
      compass_payload: cascade         as unknown as Record<string, unknown>,
      herald_summary: {
        total:             results.news.scored,
        critical:          results.news.critical,
        high:              results.news.high,
        conflictRelevant:  results.news.conflictRelevant,
      },
    })
    results.snapshot.written = !error
  }

  results.durationMs = Date.now() - startMs

  // Fire AI extraction pipeline after response is sent — uses Next.js `after()`
  // so the task survives response completion on Vercel serverless
  if (supabase && results.intel.inserted > 0) {
    after(async () => {
      try {
        await fetch(`${siteBaseUrl}/api/intel/extract`, {
          method:  'POST',
          headers: {
            'Content-Type':  'application/json',
            'Authorization': `Bearer ${process.env.CRON_SECRET ?? ''}`,
          },
          signal: AbortSignal.timeout(110_000),
        })
      } catch { /* non-fatal */ }
    })
  }

  return NextResponse.json(
    { ok: true, conflictDay, ...results, ts: new Date().toISOString() },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
