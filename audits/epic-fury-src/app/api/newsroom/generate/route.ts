/**
 * /api/newsroom/generate
 *
 * AI Newsroom Agent — generates broadcast-quality anchor scripts for the
 * current conflict day using GPT-4o, grounded by the live intel digest.
 *
 * Flow:
 *  GET  → returns cached scripts ONLY (sub-1s). Never calls OpenAI inline.
 *          Returns { ok: false } if no cache exists so client falls through
 *          to digest-driven scripts immediately.
 *  POST → force-regenerate (used by hourly cron or forced refresh button).
 *          Heavy OpenAI call — runs async via cron, never blocks the browser.
 *
 * Cache: Supabase `newsroom_scripts` table keyed by `conflict_day`.
 *        Scripts are regenerated hourly via cron.
 *
 * Security:
 *  - Cron endpoint protected by CRON_SECRET header (POST only)
 *  - All digest inputs sanitised before injecting into prompt
 *  - OpenAI key never logged or returned
 */

import { NextRequest, NextResponse } from 'next/server'
import { createServerClient }         from '@/lib/supabase-server'
import { getConflictDay }              from '@/lib/conflict-day'
import { safeOpenAIChatCompletion }    from '@/lib/openai-safe'

export const dynamic    = 'force-dynamic'
export const maxDuration = 60

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function sanitize(s: string, max = 1200): string {
  return s.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '').slice(0, max).trim()
}

/** Fetch the live intel digest from the internal API */
async function fetchDigest(baseUrl: string): Promise<DigestSummary | null> {
  try {
    const res = await fetch(`${baseUrl}/api/intel/digest`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(12_000),
    })
    if (!res.ok) return null
    return await res.json() as DigestSummary
  } catch {
    return null
  }
}

/** Call OpenAI GPT-4o and return parsed JSON segments */
async function generateScripts(
  day: number,
  digest: DigestSummary | null,
): Promise<GeneratedSegment[] | null> {
  if (!process.env.OPENAI_API_KEY) return null

  const devContext = digest
    ? sanitize(
        digest.keyDevelopments?.slice(0, 6).map(d => `• ${d.title} [${d.theater}]`).join('\n') ?? '',
      )
    : '• No live digest available — extrapolate from prior days of the conflict'

  const econContext = digest?.economics
    ? `Brent: $${digest.economics.brentUsd?.toFixed(0) ?? '?'}/bbl | Hormuz throughput: ${digest.economics.hormuzThroughputMbpd?.toFixed(1) ?? '?'} Mbpd | War-risk premium: ${digest.economics.lloydWarRiskPct?.toFixed(1) ?? '?'}%`
    : 'Economics: data pending'

  const threatContext = digest
    ? sanitize(
        digest.topThreats?.slice(0, 4).map(t => `• ${t.label} (${Math.round((t.probability ?? 0) * 100)}%, ${t.severity})`).join('\n') ?? '',
      )
    : ''

  const aiNarr = digest?.aiNarrative ? sanitize(digest.aiNarrative, 600) : ''
  const assessment = digest?.assessmentLevel ?? 'ELEVATED'

  const prompt = `You are the EPIC FURY NEWS NETWORK AI broadcast writer.
Today is Day ${day} of Operation Epic Fury — the US-Iran War (began 01 MAR 2026).

LIVE INTEL DIGEST — Day ${day}:
${devContext}

ECONOMICS:
${econContext}

TOP THREATS:
${threatContext}

${aiNarr ? `AI NARRATIVE SUMMARY:\n${aiNarr}` : ''}

THEATER ASSESSMENT: ${assessment}

Write a complete evening news broadcast for Day ${day}.
The broadcast must have EXACTLY 10 segments as follows:
1  Sarah Mitchell — Lead Anchor opening headlines
2  James Calloway — Air operations & coalition overview
3  Dr. Maya Chen — Intelligence & threat analysis
4  Dr. Amir Rostami — Nuclear watch & strategic deterrence
5  Col. Robert Harris — Tactical military situation
6  Natasha Webb — Diplomatic & back-channel developments
7  Marcus Thompson — Economics, energy, sanctions impact
8  Lt. Gen. Patricia Walsh — Pentagon readiness briefing
9  Cpl. Elena Vargas — Forward field report from Gulf of Oman
10 Sarah Mitchell — Closing summary & outlook

RULES:
- Each script 250–400 words. Broadcast-quality, authoritative, matter-of-fact anchors.
- Every segment must explicitly reference "Day ${day}" (do NOT say "Day 22" or any other day number).
- Reference real weapons systems, units, and geopolitical facts from the intel digest above.
- Make each segment feel like a live broadcast continuation — anchors hand off to each other.
- Citations must be 2–4 realistic intelligence/military/news sources (abbreviations OK).
- Return a JSON object with one key: "segments" — an array of 10 objects.

Each object:
{
  "id": <1-10>,
  "anchor": <one of: sarah|james|maya|rostami|harris|natasha|marcus|walsh|vargas>,
  "label": "<Segment topic — Day ${day}>",
  "topic": "<Short topic category>",
  "script": "<Full anchor script>",
  "citations": ["<source 1>", "<source 2>"]
}`

  try {
    const content = await safeOpenAIChatCompletion(
      [{ role: 'user', content: prompt }],
      { model: 'gpt-4o-mini', maxTokens: 4096, temperature: 0.65, timeoutMs: 55_000 },
    )
    if (!content) return null

    const parsed = JSON.parse(content) as { segments?: GeneratedSegment[] }
    const segments = parsed.segments
    if (!Array.isArray(segments) || segments.length !== 10) return null

    return segments
  } catch (err: unknown) {
    console.error('[newsroom/generate] error:', err instanceof Error ? err.message : err)
    return null
  }
}

// ---------------------------------------------------------------------------
// Route handlers
// ---------------------------------------------------------------------------

/** GET — return cached scripts ONLY (fast, sub-1s). Never blocks on OpenAI. */
export async function GET(_req: NextRequest) {
  const day      = getConflictDay()
  const supabase = await createServerClient()

  const cacheResult = await supabase
    .from('newsroom_scripts')
    .select('segments_json, created_at')
    .eq('conflict_day', day)
    .maybeSingle()

  const cached = cacheResult.data as { segments_json: unknown; created_at: string } | null

  if (cached?.segments_json) {
    const ageHours = (Date.now() - new Date(cached.created_at).getTime()) / 3_600_000
    return NextResponse.json({
      ok: true, day, source: ageHours < 1 ? 'cache' : 'stale_cache',
      ageHours: Math.round(ageHours * 10) / 10,
      segments: cached.segments_json,
    })
  }

  // No cache yet — tell client to fall through to digest immediately
  return NextResponse.json({ ok: false, day, error: 'no_cache_yet' })
}

/** POST — cron / forced regen. Requires CRON_SECRET header. */
export async function POST(req: NextRequest) {
  const secret = process.env.CRON_SECRET
  if (secret) {
    const auth = req.headers.get('authorization') ?? ''
    if (auth !== `Bearer ${secret}`) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
    }
  }

  const day     = getConflictDay()
  const supabase = await createServerClient()
  const baseUrl  = process.env.NEXT_PUBLIC_APP_URL ?? `https://${req.headers.get('host') ?? 'localhost:3000'}`

  const digest   = await fetchDigest(baseUrl)
  const segments = await generateScripts(day, digest)

  if (!segments) {
    return NextResponse.json({ ok: false, error: 'generation_failed', segments: null })
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  await (supabase as any)
    .from('newsroom_scripts')
    .upsert({ conflict_day: day, segments_json: segments, model: 'gpt-4o-mini' }, { onConflict: 'conflict_day' })

  return NextResponse.json({ ok: true, day, source: 'forced_regen', count: segments.length })
}
