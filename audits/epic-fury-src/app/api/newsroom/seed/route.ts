/**
 * /api/newsroom/seed
 *
 * One-shot generation trigger — called by the browser on first load when
 * /api/newsroom/generate returns no_cache_yet.
 *
 * Rate-limited: only generates if no cache exists for today (naturally
 * self-throttles to one expensive OpenAI call per conflict day).
 * No auth required — the natural guard is the Supabase cache check.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient }         from '@/lib/supabase-server'
import { getConflictDay }              from '@/lib/conflict-day'
import { safeOpenAIChatCompletion }    from '@/lib/openai-safe'

export const dynamic     = 'force-dynamic'
export const maxDuration = 60

interface GeneratedSegment {
  id:        number
  anchor:    string
  label:     string
  topic:     string
  script:    string
  citations: string[]
}

interface DigestSummary {
  ok?:              boolean
  conflictDay:      number
  assessmentLevel:  string
  assessmentReason: string
  aiNarrative:      string | null
  keyDevelopments:  { title: string; theater: string; confidence: number }[]
  topThreats:       { label: string; domain: string; probability: number; severity: string }[]
  economics:        { brentUsd: number; lloydWarRiskPct: number; hormuzThroughputMbpd: number }
}

function sanitize(s: string, max = 1200): string {
  return s.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '').slice(0, max).trim()
}

export async function GET(req: NextRequest) {
  const day      = getConflictDay()
  const supabase = await createServerClient()

  if (!process.env.OPENAI_API_KEY) {
    return NextResponse.json({ ok: false, reason: 'no_openai_key' }, { status: 503 })
  }

  // ── Atomic generation lock ────────────────────────────────────────────────
  // INSERT a placeholder row before calling OpenAI. Only the first concurrent
  // request succeeds; all others see a 23505 unique-conflict error and return
  // early — eliminating the SELECT → (race window) → OpenAI pattern.
  //
  // Lock semantics:
  //   segments_json = null  → generation in-progress
  //   segments_json = [...]  → generation complete
  //   row age > STALE_LOCK_MS with null segments → previous request failed; reclaim

  const STALE_LOCK_MS = 180_000  // 3 minutes — safe above the 50s OpenAI timeout

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { error: claimErr } = await (supabase as any)
    .from('newsroom_scripts')
    .insert({ conflict_day: day, segments_json: null, model: 'gpt-4o-mini' })

  if (claimErr) {
    // A row already exists for today — either valid or in-progress.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data: existingRow } = await (supabase as any)
      .from('newsroom_scripts')
      .select('segments_json, created_at')
      .eq('conflict_day', day)
      .maybeSingle()

    const segmentsValid =
      Array.isArray(existingRow?.segments_json) &&
      (existingRow!.segments_json as unknown[]).length >= 9

    if (segmentsValid) {
      return NextResponse.json({ ok: false, reason: 'already_cached', day })
    }

    // If the lock is fresh (< STALE_LOCK_MS), another request is still generating.
    const ageMs = existingRow?.created_at
      ? Date.now() - new Date(existingRow.created_at as string).getTime()
      : 0

    if (ageMs < STALE_LOCK_MS) {
      return NextResponse.json({ ok: false, reason: 'generating', day })
    }

    // Stale lock from a failed previous attempt — reclaim by deleting and re-inserting.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (supabase as any).from('newsroom_scripts').delete().eq('conflict_day', day)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error: reclaimErr } = await (supabase as any)
      .from('newsroom_scripts')
      .insert({ conflict_day: day, segments_json: null, model: 'gpt-4o-mini' })
    if (reclaimErr) {
      // Another process beat us to the reclaim — treat as in-progress.
      return NextResponse.json({ ok: false, reason: 'generating', day })
    }
  }
  // We hold the lock. Proceed with OpenAI generation below.

  // Fetch live digest for grounding
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? `https://${req.headers.get('host') ?? 'localhost:3000'}`
  let digest: DigestSummary | null = null
  try {
    const dr = await fetch(`${baseUrl}/api/intel/digest`, { cache: 'no-store', signal: AbortSignal.timeout(10_000) })
    if (dr.ok) digest = await dr.json() as DigestSummary
  } catch { /* generate without digest */ }

  const devContext = digest
    ? sanitize(digest.keyDevelopments?.slice(0, 6).map(d => `• ${d.title} [${d.theater}]`).join('\n') ?? '')
    : '• No live digest — extrapolate from the ongoing US-Iran conflict'

  const narrative = digest?.aiNarrative ? sanitize(digest.aiNarrative, 600) : ''
  const threats = digest?.topThreats?.slice(0, 3)
    .map(t => `• ${t.label}: ${Math.round(t.probability * 100)}% — ${t.severity}`)
    .join('\n') ?? ''
  const econ = digest?.economics
  const econStr = econ
    ? `Brent: $${econ.brentUsd?.toFixed(0)}, Hormuz: ${econ.hormuzThroughputMbpd?.toFixed(1)} Mbpd, Lloyd's war risk: ${econ.lloydWarRiskPct?.toFixed(1)}%`
    : 'Brent ~$109, WTI ~$112, Hormuz 40% degraded, Lloyd\'s war risk elevated'

  const prompt = `You are the AI newsroom director for Epic Fury News Network, a fictional 24/7 conflict news platform covering Operation Epic Fury — the US/Israel vs Iran war that began 1 March 2026.

Today is conflict Day ${day}. Write a complete 10-segment broadcast for the 9-anchor team. Use the live intel data below as ground truth.

LIVE INTEL — Day ${day}:
${devContext}

SITUATION NARRATIVE:
${narrative || `Day ${day} of Operation Epic Fury. Coalition operations continue.`}

TOP THREATS (ORACLE-9):
${threats || '• All domains elevated'}

ECONOMICS: ${econStr}

ANCHOR ASSIGNMENTS:
• sarah — Lead Anchor (US female, authoritative)
• james — Co-Anchor (British male, measured)
• maya — Defense Correspondent (US female, analytical)
• harris — Military Analyst (US male, commanding)
• natasha — Foreign Affairs Reporter (Australian female, diplomatic)
• marcus — Economics Correspondent (US male, financial)
• walsh — Pentagon Correspondent (US female, official)
• rostami — Nuclear & Iran Analyst (British male, expert)
• vargas — Forward Correspondent (US female, energetic field reporter)

RULES:
- Each script must be 2–4 sentences ONLY. Concise, authoritative, no filler.
- Sarah opens and closes (segments 1 and 10). She passes to James at end of segment 1.
- Each anchor passes to the next by name at the end of their segment.
- Use real Day ${day} intel. NO references to any other day number.
- Sarah's opening must NOT start with "Good evening" — vary the opening each day.
- Keep each script under 80 words total.

Return ONLY valid JSON:
{
  "segments": [
    {
      "id": <1-10>,
      "anchor": <sarah|james|maya|harris|natasha|marcus|walsh|rostami|vargas>,
      "label": "<topic — Day ${day}>",
      "topic": "<short category>",
      "script": "<full broadcast script>",
      "citations": ["<source>", "<source>"]
    }
  ]
}`

  try {
    const content = await safeOpenAIChatCompletion(
      [{ role: 'user', content: prompt }],
      { model: 'gpt-4o-mini', maxTokens: 2500, temperature: 0.65, timeoutMs: 50_000 },
    )

    if (!content) {
      // Release lock so a future request can retry.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (supabase as any).from('newsroom_scripts').delete().eq('conflict_day', day)
      return NextResponse.json({ ok: false, reason: 'openai_unavailable' }, { status: 502 })
    }

    const parsed   = JSON.parse(content) as { segments?: GeneratedSegment[] }
    const segments = parsed.segments
    if (!Array.isArray(segments) || segments.length !== 10) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (supabase as any).from('newsroom_scripts').delete().eq('conflict_day', day)
      return NextResponse.json({ ok: false, reason: 'invalid_segment_count', count: segments?.length ?? 0 }, { status: 502 })
    }

    // Update the locked placeholder row with the generated segments.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (supabase as any)
      .from('newsroom_scripts')
      .update({ segments_json: segments, model: 'gpt-4o-mini' })
      .eq('conflict_day', day)

    return NextResponse.json({ ok: true, day, count: segments.length, segments })
  } catch (err) {
    console.error('[newsroom/seed] error:', err instanceof Error ? err.message : err)
    // Release lock so a future request can retry.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (supabase as any).from('newsroom_scripts').delete().eq('conflict_day', day).then(() => {})
    return NextResponse.json({ ok: false, reason: 'exception' }, { status: 500 })
  }
}
