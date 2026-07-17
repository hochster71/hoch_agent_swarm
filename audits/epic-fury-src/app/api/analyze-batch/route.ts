/**
 * /api/analyze-batch
 *
 * NEXUS Batch Analysis Cron — runs every 15 minutes via Vercel cron
 *
 * Pipeline:
 *  1. Pull the last 8 CRITICAL or HIGH intel rows from Supabase (by HERALD score)
 *  2. Re-run deep /api/analyze logic on each to update corroboration counts
 *  3. Write back `tags` field with updated corroboration + verdict metadata
 *  4. Write a model_snapshot row summarising the batch run
 *
 * Auth: Bearer CRON_SECRET header (same as /api/ingest)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient }        from '@/lib/supabase-server'
import { scoreHeadline }             from '@/lib/herald-engine'
import { computeAllThreats }         from '@/lib/oracle-engine'
import { getConflictDay }            from '@/lib/conflict-day'
import { AI_AVAILABLE, assessIntelBatch } from '@/lib/ai-engine'
import type { Database } from '@/lib/types'

type SupabaseClient = Awaited<ReturnType<typeof createServerClient>>

export const runtime     = 'nodejs'
export const dynamic     = 'force-dynamic'
export const revalidate  = 0
export const maxDuration = 60  // re-analyzes up to 20 intel rows via Supabase

// ── Types ──────────────────────────────────────────────────────────────────
interface IntelRow {
  id:          string
  title:       string
  summary:     string | null
  theater:     string | null
  confidence:  number | null
  source_url:  string | null
  source_name: string | null
  source_type: string | null
  verified:    boolean | null
  tags:        string[] | null
  author:      string | null
  created_at:  string
}

interface BatchRunResult {
  processed:   number
  updated:     number
  errors:      number
  aiAssessed:  number
  items:       { id: string; title: string; verdict: string; corrobCount: number; confidence: number }[]
}

// ── Verdict logic (mirrors /api/analyze) ──────────────────────────────────
function computeVerdict(heraldScore: number, tier: number, corrobCount: number, ioFlagCount: number) {
  let truthScore = 50

  // Source tier contribution  (max 30 pts)
  truthScore += tier === 1 ? 30 : tier === 2 ? 15 : 0

  // Corroboration bonus (max 30 pts)
  truthScore += Math.min(corrobCount * 10, 30)

  // HERALD penalty (up to -50 pts)
  truthScore -= Math.min(heraldScore / 2, 50)

  // IO flag penalty
  truthScore -= ioFlagCount * 8

  truthScore = Math.max(0, Math.min(100, Math.round(truthScore)))

  let verdict: string
  if (heraldScore >= 75 || ioFlagCount >= 3) {
    verdict = 'DISINFORMATION'
  } else if (heraldScore >= 45 || (tier >= 3 && corrobCount === 0)) {
    verdict = 'SUSPICIOUS'
  } else if (corrobCount >= 2 && tier <= 2) {
    verdict = 'VERIFIED'
  } else if (tier === 1 && heraldScore < 20) {
    verdict = 'LIKELY_TRUE'
  } else {
    verdict = 'UNCONFIRMED'
  }

  return { truthScore, verdict }
}

// ── Keyword corroboration search ──────────────────────────────────────────
// Previous: one `.ilike()` query per keyword (up to 5 round-trips per row,
//           100 round-trips for 20 rows).
// Now: single query with OR filter across all keywords → 1 round-trip per row.
// Geopolitical stopwords are filtered out before building the query because
// terms like "iran", "attack", "war" match every row and inflate the count.
const CORROBORATION_STOPWORDS = new Set([
  'iran', 'iraq', 'israel', 'irgc', 'ussf', 'force', 'forces',
  'attack', 'strike', 'missile', 'military', 'killed', 'dead',
  'war', 'news', 'report', 'says', 'that', 'with', 'have',
  'from', 'into', 'over', 'amid', 'after', 'amid', 'claims',
])

async function corroborateRow(supabase: SupabaseClient, row: IntelRow): Promise<number> {
  const words = row.title
    .split(/\s+/)
    .map((w: string) => w.replace(/[^a-zA-Z0-9]/g, ''))
    .filter((w: string) => w.length >= 4)
    .filter((w: string) => !CORROBORATION_STOPWORDS.has(w.toLowerCase()))
    .slice(0, 5)

  if (words.length === 0) return 0

  // Build a single OR filter: title.ilike.%word1%,title.ilike.%word2%,...
  const orFilter = words.map(w => `title.ilike.%${w}%`).join(',')

  const { data } = await supabase
    .from('intel')
    .select('id, title')
    .neq('id', row.id)
    .or(orFilter)
    .limit(25)

  if (!Array.isArray(data)) return 0
  const matches = new Set((data as { id: string; title: string }[]).map(r => r.title))
  return matches.size
}

// ── Main handler ──────────────────────────────────────────────────────────
export async function GET(req: NextRequest) {
  // Auth check
  const auth   = req.headers.get('authorization')
  const secret = process.env.CRON_SECRET
  if (secret && auth !== `Bearer ${secret}`) {
    // Also allow Vercel cron invocation (no auth header on Vercel infrastructure)
    const isVercelCron = req.headers.get('x-vercel-cron') === '1'
    if (!isVercelCron) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
  }

  // Guard: skip gracefully when Supabase is not configured (local dev without Docker)
  const supaUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? ''
  const supaKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ''
  if (!supaUrl || supaUrl.includes('localhost') || !supaKey || supaKey === 'placeholder-anon-key') {
    return NextResponse.json({
      ok: true, processed: 0, updated: 0, errors: 0, items: [], durationMs: 0,
      note: 'Batch analysis skipped — Supabase not configured',
    })
  }

  const supabase    = await createServerClient()
  const conflictDay = getConflictDay()
  const startedAt   = Date.now()
  const result: BatchRunResult = { processed: 0, updated: 0, errors: 0, aiAssessed: 0, items: [] }

  try {
    // Step 1: Pull recent intel rows (HERALD-3 authored, confidence ≥65)
    const { data: rows, error: fetchErr } = await supabase
      .from('intel')
      .select('*')
      .in('author', ['HERALD-3', 'HERALD-3+AI'])
      .gte('confidence', 65)
      .order('created_at', { ascending: false })
      .limit(20)

    if (fetchErr) {
      console.warn('[analyze-batch] Supabase fetch error:', fetchErr.message)
      return NextResponse.json({ ok: true, processed: 0, updated: 0, errors: 0, items: [], durationMs: 0, note: fetchErr.message })
    }

    const intelRows = (rows ?? []) as IntelRow[]

    // Step 2a: Run AI batch assessment on up to 10 items (fast gpt-4o-mini call)
    const aiVerdictMap = new Map<number, { verdict: string; confidence: number; reasoning: string }>()
    if (AI_AVAILABLE && intelRows.length > 0) {
      try {
        const batchItems = intelRows.slice(0, 10).map(r => ({
          title: r.title,
          theater: r.theater ?? 'Unknown',
          sourceTier: r.source_type === 'wire' ? 1 : r.source_type === 'analysis' || r.source_type === 'regional' ? 2 : 3,
        }))
        const aiVerdicts = await assessIntelBatch(batchItems)
        if (aiVerdicts) {
          for (const v of aiVerdicts) {
            aiVerdictMap.set(v.index, { verdict: v.verdict, confidence: v.confidence, reasoning: v.reasoning })
          }
          result.aiAssessed = aiVerdicts.length
        }
      } catch {
        // Non-fatal — continue with deterministic fallback
      }
    }

    // Step 2b: Re-score and corroborate each row
    for (let idx = 0; idx < intelRows.length; idx++) {
      const row = intelRows[idx]
      result.processed++

      try {
        // Re-run HERALD on title
        const herald = scoreHeadline(
          row.title,
          row.source_url ?? '',
          row.summary ?? '',
        )

        // Cross-corroborate
        const corrobCount = await corroborateRow(supabase, row)

        // Determine source tier from source_type
        const tier = row.source_type === 'wire'
          ? 1
          : row.source_type === 'analysis' || row.source_type === 'regional'
            ? 2
            : 3

        const { truthScore, verdict: detVerdict } = computeVerdict(
          herald.score,
          tier,
          corrobCount,
          herald.flags.length,
        )

        // Merge AI verdict if available for this index
        const aiResult = aiVerdictMap.get(idx)
        const verdict  = aiResult?.verdict ?? detVerdict

        // Blend deterministic truth score with AI confidence
        // Deterministic score anchors accuracy; AI confidence refines it
        const finalConfidence = aiResult
          ? Math.round((truthScore + aiResult.confidence) / 2)
          : Math.round((row.confidence ?? 50 + truthScore) / 2)

        // Build updated tags array
        const baseTags = (row.tags ?? []).filter((t: string) =>
          !t.startsWith('verdict:') &&
          !t.startsWith('truth:') &&
          !t.startsWith('corroboration:')
        )
        const newTags = [
          ...baseTags,
          `verdict:${verdict}`,
          `truth:${truthScore}`,
          `corroboration:${corrobCount}`,
          `herald:${herald.score}`,
          `batch_reviewed:${new Date().toISOString().split('T')[0]}`,
          ...(aiResult ? ['ai_batch_assessed'] : []),
        ]

        // Write back tags + confidence + verified
        const intelWriter = supabase.from('intel') as unknown as {
          update: (values: Database['public']['Tables']['intel']['Update']) => {
            eq: (column: string, value: string) => Promise<{ error: { message: string } | null }>
          }
        }
        const { error: updateErr } = await intelWriter
          .update({
            tags:       newTags,
            confidence: finalConfidence,
            verified:   verdict === 'VERIFIED' || verdict === 'LIKELY_TRUE',
          })
          .eq('id', row.id)

        if (!updateErr) {
          result.updated++
          result.items.push({ id: row.id, title: row.title.slice(0, 60), verdict, corrobCount, confidence: finalConfidence })
        } else {
          console.error('[analyze-batch] update error id=%s: %s', row.id, updateErr.message)
          result.errors++
        }
      } catch (err) {
        console.error('[analyze-batch] processing error id=%s: %s', row.id, err instanceof Error ? err.message : String(err))
        result.errors++
      }
    }

    // Step 3: Write model_snapshot summary of batch run
    const threats     = computeAllThreats(conflictDay)
    const topThreats  = threats.slice(0, 3).map(t => ({ label: t.label, prob: t.probability }))

    const snapshotWriter = supabase.from('model_snapshots') as unknown as {
      insert: (values: Database['public']['Tables']['model_snapshots']['Insert']) => Promise<unknown>
    }

    await snapshotWriter.insert({
      conflict_day:    conflictDay,
      oracle_payload:  JSON.stringify({ topThreats }),
      compass_payload: JSON.stringify({}),
      herald_summary:  JSON.stringify({
        batch:       true,
        processed:   result.processed,
        updated:     result.updated,
        aiAssessed:  result.aiAssessed,
        verdicts:    result.items.map(i => i.verdict),
        durationMs:  Date.now() - startedAt,
      }),
    })

    return NextResponse.json({
      ok:          true,
      processed:   result.processed,
      updated:     result.updated,
      errors:      result.errors,
      aiAssessed:  result.aiAssessed,
      items:       result.items,
      durationMs:  Date.now() - startedAt,
    })

  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
