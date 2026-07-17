/**
 * GET /api/intel/cross-ref
 *
 * NEXUS Auto-Verification Pipeline — called by Vercel Cron every 10 minutes.
 *
 * For each unverified intel row added in the last 3 hours:
 *   1. Extract significant words from the title (4+ chars, not stopwords)
 *   2. Compare in-memory against the last 24h corpus (ONE DB query)
 *      to find rows from DIFFERENT wire families with 3+ shared keywords.
 *   3. Wire-family grouping prevents AP wire re-publications across ABC/NBC/CBS
 *      from being counted as independent corroboration (fake confidence).
 *   4. If 2+ distinct wire families corroborate → mark verified=true,
 *      bump confidence by +12 (capped at 97), append 'cross-ref-verified' tag.
 *
 * Writes back to Supabase using the service-role key (bypasses RLS).
 * Auth: Bearer CRON_SECRET (omit in dev).
 *
 * Performance: replaces the previous N+1 pattern (200+ DB queries per run)
 * with exactly 3 DB operations: fetch candidates + fetch corpus + batch update.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { AI_AVAILABLE, detectSourceDisagreements } from '@/lib/ai-engine'
import { classifySourceTier } from '@/lib/citation-tracker'

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 60  // 3 DB operations; well within 60s

// ── Auth guard ─────────────────────────────────────────────────────────────
function isAuthorised(req: NextRequest): boolean {
  if (req.headers.get('x-vercel-cron') === '1') return true
  const secret = process.env.CRON_SECRET
  if (!secret) {
    if (process.env.NODE_ENV === 'production') return false
    return true
  }
  const auth = req.headers.get('authorization') ?? ''
  return auth === `Bearer ${secret}`
}

// ── Service client ─────────────────────────────────────────────────────────
function getServiceClient() {
  const url    = process.env.NEXT_PUBLIC_SUPABASE_URL
  const svcKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !svcKey) return null
  return createClient<any>(url, svcKey, { auth: { persistSession: false } })
}

// ── Common English stopwords ───────────────────────────────────────────────
const STOP = new Set([
  'that', 'this', 'with', 'from', 'have', 'will', 'been', 'says', 'said',
  'over', 'into', 'their', 'they', 'what', 'your', 'more', 'when', 'there',
  'also', 'were', 'after', 'about', 'against', 'some', 'calls', 'amid',
  'report', 'reports', 'reported', 'amid', 'amid', 'attack', 'strike',
])

function extractWords(title: string): string[] {
  return title
    .toLowerCase()
    .split(/[\s\W]+/)
    .filter(w => w.length >= 4 && !STOP.has(w) && /^[a-z]+$/.test(w))
    .slice(0, 8)
}

// ── Wire-family grouping ───────────────────────────────────────────────────
// Outlets in the same family all re-publish the same wire copy.
// Counting ABC+NBC+CBS as "3 independent sources" produces false high-confidence.
// Map each to a family; count unique families — not unique outlets.
const WIRE_FAMILIES: Record<string, string> = {
  'Reuters — World':       'Reuters',
  'Reuters — Middle East': 'Reuters',
  'AP — Top Headlines':    'AP',
  'AP — World News':       'AP',
  'ABC News':              'US-Broadcast',
  'NBC News':              'US-Broadcast',
  'CBS News':              'US-Broadcast',
  'PBS NewsHour':          'US-Broadcast',
  'NPR News':              'US-Broadcast',
  'USA Today':             'US-Broadcast',
  'Fox News':              'Fox',
  'Fox Business':          'Fox',
  'Washington Times':      'Washington-Times-Group',
  'Washington Examiner':   'Washington-Times-Group',
  'Times of Israel':       'Israeli-Press',
  'Jerusalem Post':        'Israeli-Press',
}

function wireFamily(sourceName: string | null | undefined): string {
  const s = (sourceName ?? '').trim()
  return WIRE_FAMILIES[s] ?? s
}

// ── Kinetic Contradiction Detector ────────────────────────────────────────
// Sites confirmed under active US/Israeli bombardment.
// A story using diplomatic/monitoring language about one of these sites
// is mutually exclusive with the current kinetic reality.
const KINETIC_TARGETS: string[][] = [
  ['fordow', 'fordo'],
  ['natanz', 'hall a', 'hall b'],
  ['arak', 'ir-40', 'heavy water reactor'],
  ['isfahan', 'esfahan', 'uranium conversion'],
  ['parchin'],
]

const KINETIC_DIPLOMAT_PATTERNS: RegExp[] = [
  /\biaea\b/i,
  /\binspect(or|ion|ors|ions)?\b/i,
  /\bsafeguards\b/i,
  /\benrichment (activity|resumed|reported|detected|ongoing)\b/i,
  /\bcentrifuge[s]? (operational|spinning|active|running)\b/i,
  /\b(access denied|denied access|inspectors barred)\b/i,
  /\bdirector general (report|says|warns)\b/i,
  /\binternational atomic energy\b/i,
]

function kineticContradictionDetected(title: string): boolean {
  const text  = title.toLowerCase()
  const site  = KINETIC_TARGETS.some(aliases => aliases.some(a => text.includes(a)))
  if (!site) return false
  return KINETIC_DIPLOMAT_PATTERNS.some(p => p.test(text))
}

// ── Main handler ────────────────────────────────────────────────────────────
export async function GET(req: NextRequest) {
  if (!isAuthorised(req)) {
    return NextResponse.json({ error: 'Unauthorised' }, { status: 401 })
  }
  try {
    return await _handleCrossRef()
  } catch (err) {
    console.error('[cross-ref] unhandled error', err)
    return NextResponse.json({ ok: false, error: 'Internal error', verified: 0 }, { status: 500 })
  }
}

async function _handleCrossRef() {
  const supabase = getServiceClient()
  if (!supabase) {
    return NextResponse.json({ ok: false, error: 'No service-role credentials', verified: 0 }, { status: 503 })
  }

  const now          = Date.now()
  const windowStart  = new Date(now - 3  * 60 * 60 * 1000).toISOString()  // candidates: last 3h
  const corpusStart  = new Date(now - 24 * 60 * 60 * 1000).toISOString()  // corpus:     last 24h

  // ── Query 1: unverified candidates from the last 3 hours ──────────────
  const { data: candidates, error: candidateErr } = await supabase
    .from('intel')
    .select('id,title,confidence,source_name,tags,verified')
    .eq('verified', false)
    .gte('created_at', windowStart)
    .order('created_at', { ascending: false })
    .limit(40)

  if (candidateErr) {
    console.error('[cross-ref] candidate fetch error', candidateErr.message)
    return NextResponse.json({ ok: false, error: candidateErr.message, verified: 0 }, { status: 503 })
  }

  const rows: any[] = candidates ?? []
  if (rows.length === 0) {
    return NextResponse.json({ ok: true, candidates: 0, verified: 0, skipped: 0, verifiedIds: [], windowStart, ts: new Date().toISOString() })
  }

  // ── Query 2: reference corpus — last 24h intel (all sources) ──────────
  // Pulling the corpus in a SINGLE query replaces the previous N+1 pattern
  // (per-row × per-word × DB round-trip = 200+ queries per cron run).
  const { data: corpusRows, error: corpusErr } = await supabase
    .from('intel')
    .select('id,title,source_name')
    .gte('created_at', corpusStart)
    .order('created_at', { ascending: false })
    .limit(500)

  if (corpusErr) {
    console.error('[cross-ref] corpus fetch error', corpusErr.message)
    return NextResponse.json({ ok: false, error: corpusErr.message, verified: 0 }, { status: 503 })
  }

  const corpus: any[] = corpusRows ?? []

  // Pre-compute word fingerprints for the entire corpus
  const corpusFingerprints = corpus.map(r => ({
    id:      r.id       as string,
    source:  r.source_name as string | null,
    family:  wireFamily(r.source_name),
    words:   new Set(extractWords(r.title ?? '')),
  }))

  // ── In-memory corroboration (no more DB queries in the loop) ──────────
  let verifiedCount = 0
  let skippedCount  = 0
  const verifiedIds: string[] = []
  const batchUpdates: Array<{ id: string; verified: boolean; confidence: number; tags: string[] }> = []

  for (const row of rows) {
    const candidateWords = extractWords(row.title ?? '')
    if (candidateWords.length < 3) { skippedCount++; continue }

    const candidateFamily = wireFamily(row.source_name)
    const corrobFamilies  = new Set<string>()
    const corrobSources   = new Set<string>()

    for (const corpusItem of corpusFingerprints) {
      if (corpusItem.id === row.id) continue              // skip self
      if (corpusItem.family === candidateFamily) continue // same wire family = no credit

      // Count shared meaningful keywords
      let shared = 0
      for (const word of candidateWords) {
        if (corpusItem.words.has(word)) shared++
        if (shared >= 3) break  // threshold met — no need to keep counting
      }
      if (shared < 3) continue

      corrobFamilies.add(corpusItem.family)
      corrobSources.add((corpusItem.source ?? '').trim())
    }

    if (corrobFamilies.size >= 2) {
      // Never auto-verify a story that contradicts confirmed kinetic ground truth.
      // Example: "IAEA reports enrichment at Fordow" while Fordow is under daily
      // bombardment.  Corroboration cannot rescue a logical impossibility.
      if (kineticContradictionDetected(row.title ?? '')) {
        const tags = Array.isArray(row.tags) ? [...row.tags] : []
        if (!tags.includes('kinetic-contradiction')) tags.push('kinetic-contradiction')
        // Downgrade confidence — corroborated disinformation is still disinformation
        const newConf = Math.max(5, Math.min(25, (row.confidence ?? 60) - 30))
        batchUpdates.push({ id: row.id, verified: false, confidence: newConf, tags })
        skippedCount++
        continue
      }

      const newConf = Math.min(97, (row.confidence ?? 60) + 12)
      const tags    = Array.isArray(row.tags) ? [...row.tags] : []
      if (!tags.includes('cross-ref-verified')) tags.push('cross-ref-verified')
      tags.push(`corroborated-by:${[...corrobSources].slice(0, 3).join(',')}`)

      batchUpdates.push({ id: row.id, verified: true, confidence: newConf, tags })
      verifiedIds.push(row.id)
      verifiedCount++
    }
  }

  // ── Query 3: batch-write verifications ────────────────────────────────
  // One DB round-trip per verified item (could be further batched with RPC
  // but individual updates are fine for ≤40 rows per cron run).
  for (const update of batchUpdates) {
    const { error: updateErr } = await supabase
      .from('intel')
      .update({ verified: update.verified, confidence: update.confidence, tags: update.tags })
      .eq('id', update.id)

    if (updateErr) {
      console.error(`[cross-ref] update failed for ${update.id}:`, updateErr.message)
    }
  }

  // ── Query 4: Temporal confidence decay ────────────────────────────────
  // Unverified items older than 2 hours lose 5 confidence per hour (max -20).
  // This prevents stale unverified reports from sitting at artificially high
  // confidence indefinitely.
  let decayedCount = 0
  const decayThreshold = new Date(now - 2 * 60 * 60 * 1000).toISOString() // 2h ago
  const { data: staleRows, error: staleErr } = await supabase
    .from('intel')
    .select('id,confidence,created_at,tags')
    .eq('verified', false)
    .lte('created_at', decayThreshold)
    .gte('created_at', corpusStart)       // only last 24h, not ancient rows
    .gt('confidence', 20)                 // don't decay already-low items
    .limit(60)

  if (!staleErr && staleRows) {
    for (const stale of staleRows as any[]) {
      const ageMs = now - new Date(stale.created_at).getTime()
      const hoursOld = Math.floor(ageMs / (60 * 60 * 1000))
      const decay = Math.min(20, (hoursOld - 2) * 5) // 5 per hour past 2h, capped at 20
      if (decay <= 0) continue
      const newConf = Math.max(15, (stale.confidence ?? 60) - decay)
      if (newConf === stale.confidence) continue

      const tags = Array.isArray(stale.tags) ? [...stale.tags] : []
      if (!tags.includes('confidence-decayed')) tags.push('confidence-decayed')

      await supabase
        .from('intel')
        .update({ confidence: newConf, tags })
        .eq('id', stale.id)
      decayedCount++
    }
  }

  // ── Query 5: Source disagreement detection (AI-powered) ───────────────
  // Identify cases where T1/T2 credible sources report conflicting info.
  let sourceDisagreementCount = 0
  if (AI_AVAILABLE && rows.length >= 2) {
    try {
      const allRecentItems = [...rows, ...corpus.slice(0, 20)].slice(0, 30)
      const itemsForDisagreement = allRecentItems.map((r: any, i: number) => ({
        index:      i,
        title:      r.title ?? '',
        source:     r.source_name ?? '',
        tier:       classifySourceTier(null, r.source_name ?? ''),
        confidence: r.confidence ?? 50,
      }))

      const disagreements = await detectSourceDisagreements(itemsForDisagreement)
      if (disagreements && disagreements.length > 0) {
        for (const d of disagreements) {
          const itemA = allRecentItems[d.indexA]
          const itemB = allRecentItems[d.indexB]
          if (!itemA?.id || !itemB?.id) continue

          for (const item of [itemA, itemB]) {
            const { data: current } = await supabase
              .from('intel')
              .select('tags')
              .eq('id', item.id)
              .single()
            if (!current) continue
            const tags = Array.isArray(current.tags) ? [...current.tags] : []
            if (!tags.includes('source-disagreement')) {
              tags.push('source-disagreement')
              tags.push(`disagrees-with:${item === itemA ? d.sourceB : d.sourceA}`)
              await supabase.from('intel').update({ tags }).eq('id', item.id)
              sourceDisagreementCount++
            }
          }
        }
      }
    } catch (err) {
      console.error('[cross-ref] source disagreement detection error', err)
    }
  }

  return NextResponse.json({
    ok:          true,
    candidates:  rows.length,
    corpusSize:  corpus.length,
    verified:    verifiedCount,
    skipped:     skippedCount,
    decayed:     decayedCount,
    sourceDisagreements: sourceDisagreementCount,
    verifiedIds,
    windowStart,
    ts:          new Date().toISOString(),
  })
}

