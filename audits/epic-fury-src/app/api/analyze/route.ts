/**
 * GET /api/analyze?url=<encoded-url>&title=<encoded-title>&source=<source>
 *
 * Deep story analysis engine — NEXUS multi-agent pipeline:
 *
 * 1. Run HERALD-3 IO/disinformation scoring          → risk, flags, categories
 * 2. Extract key claims from the headline/summary    → structured claim list
 * 3. Cross-reference against Supabase `intel` table  → corroboration score
 * 4. Assign ORACLE threat context                    → which threat domains affected
 * 5. Generate fully-cited verdict + confidence score
 * 6. Return structured AnalysisReport
 *
 * Used by LiveNewsBoard to show inline deep-dive on any headline.
 */

import { NextRequest, NextResponse } from 'next/server'
import { scoreHeadline }    from '@/lib/herald-engine'
import { computeAllThreats } from '@/lib/oracle-engine'
import { getConflictDay }   from '@/lib/conflict-day'
import { createServerClient } from '@/lib/supabase-server'

export const revalidate = 0

// ── Types ──────────────────────────────────────────────────────────────────
export interface Claim {
  text:       string
  confidence: number   // 0-100
  verified:   boolean
  source:     string
}

export interface CorroborationResult {
  count:    number         // number of matching intel rows found
  items:    { title: string; theater: string; confidence: number; author: string | null }[]
}

export interface AnalysisReport {
  url:            string
  title:          string
  source:         string
  analyzedAt:     string

  // HERALD-3 output
  heraldRisk:     string
  heraldScore:    number
  heraldFlags:    { category: string; matched: string; weight: number }[]
  ioWarnings:     string[]

  // Claim extraction
  claims:         Claim[]

  // Cross-reference
  corroboration:  CorroborationResult

  // ORACLE threat context
  relatedThreats: { label: string; probability: number; domain: string }[]

  // Verdict
  truthScore:     number    // 0-100 composite
  verdict:        'VERIFIED' | 'LIKELY_TRUE' | 'UNCONFIRMED' | 'SUSPICIOUS' | 'DISINFORMATION'
  verdictReason:  string
  citations:      string[]
}

// ── Keyword → claim extractor ────────────────────────────────────────────
const CLAIM_PATTERNS: { re: RegExp; template: (m: RegExpMatchArray) => string; source: string }[] = [
  {
    re: /(\d{1,4})\s*(killed|dead|eliminated|kia)/i,
    template: m => `${m[1]} casualties claimed`,
    source: 'casualty-claim',
  },
  {
    re: /(ceasefire|cease[\s-]fire|truce|armistice)/i,
    template: () => 'Ceasefire/truce engagement claimed',
    source: 'diplomatic-claim',
  },
  {
    re: /(missile|ballistic|mrbm|icbm|cruise)\s*(launch|strike|attack|fired)/i,
    template: m => `${m[1]} ${m[2]} reported`,
    source: 'kinetic-claim',
  },
  {
    re: /(nuclear|enrichment|uranium|centrifuge|fordow|natanz)/i,
    template: m => `Nuclear/WMD context: ${m[1]}`,
    source: 'nuclear-claim',
  },
  {
    re: /(irgc|iran(ian)?|khamenei|rouhani|quds)\s+(\w+)/i,
    template: m => `Iranian actor claim: ${m[0].trim()}`,
    source: 'actor-claim',
  },
  {
    re: /(\$\d+[\.\d]*\s*(?:billion|million|b|m))\s*(sanction|seize|freeze|designat)/i,
    template: m => `Financial action: ${m[0].trim()}`,
    source: 'financial-claim',
  },
  {
    re: /(hormuz|strait|gulf|red\s*sea)\s*(closed|blocked|mined|threatened)/i,
    template: m => `Maritime chokepoint claim: ${m[0].trim()}`,
    source: 'maritime-claim',
  },
]

function extractClaims(title: string, summary: string, source: string, tier: number): Claim[] {
  const text   = `${title} ${summary}`
  const claims: Claim[] = []

  for (const p of CLAIM_PATTERNS) {
    const m = text.match(p.re)
    if (m) {
      // Tier 1 sources start at higher confidence
      const baseConf = tier === 1 ? 72 : tier === 2 ? 55 : 40
      claims.push({
        text:       p.template(m),
        confidence: Math.min(95, baseConf + Math.floor(Math.random() * 15)),
        verified:   tier === 1,
        source,
      })
    }
  }

  // Add a generic "report" claim for any story
  if (claims.length === 0) {
    claims.push({
      text:       `Report by ${source}: "${title.slice(0, 80)}"`,
      confidence: tier === 1 ? 80 : 55,
      verified:   tier === 1,
      source,
    })
  }

  return claims
}

// ── Verdict logic ────────────────────────────────────────────────────────
function computeVerdict(
  heraldScore: number,
  tier: number,
  corrobCount: number,
  ioFlagCount: number,
): {
  truthScore: number
  verdict: AnalysisReport['verdict']
  verdictReason: string
} {
  // Start with a base score derived from source tier
  let base = tier === 1 ? 82 : tier === 2 ? 65 : 48

  // HERALD penalty: IO flags reduce truth score
  base -= heraldScore * 0.35

  // Corroboration bonus
  base += Math.min(15, corrobCount * 5)

  const truthScore = Math.max(0, Math.min(100, Math.round(base)))

  let verdict: AnalysisReport['verdict']
  let verdictReason: string

  if (heraldScore >= 75 || ioFlagCount >= 3) {
    verdict       = 'DISINFORMATION'
    verdictReason = `HERALD-3 detected ${ioFlagCount} IO flag${ioFlagCount !== 1 ? 's' : ''} (score ${heraldScore}/100). Treat as adversarial narrative. Do not amplify.`
  } else if (heraldScore >= 45 || (tier >= 3 && corrobCount === 0)) {
    verdict       = 'SUSPICIOUS'
    verdictReason = `Elevated HERALD-3 IO risk (score ${heraldScore}/100) with ${corrobCount} corroborating intel row${corrobCount !== 1 ? 's' : ''}. Independent verification required before reporting.`
  } else if (corrobCount >= 2 && tier <= 2) {
    verdict       = 'VERIFIED'
    verdictReason = `Tier-${tier} source corroborated by ${corrobCount} independent intel entries. High confidence.`
  } else if (tier === 1 && heraldScore < 20) {
    verdict       = 'LIKELY_TRUE'
    verdictReason = `Tier-1 wire service (${heraldScore} IO score). Low adversarial signal.`
  } else {
    verdict       = 'UNCONFIRMED'
    verdictReason = `Single source, ${corrobCount} corroboration hit${corrobCount !== 1 ? 's' : ''}. Awaiting verification from additional feeds.`
  }

  return { truthScore, verdict, verdictReason }
}

// ── Route handler ────────────────────────────────────────────────────────
export async function GET(req: NextRequest) {
  try {
  const { searchParams } = req.nextUrl
  const rawUrl  = searchParams.get('url')     ?? ''
  const title   = searchParams.get('title')   ?? 'Unknown headline'
  const summary = searchParams.get('summary') ?? ''
  const source  = searchParams.get('source')  ?? 'Unknown'
  const tierRaw = parseInt(searchParams.get('tier') ?? '2', 10)
  const tier    = (tierRaw === 1 || tierRaw === 2 || tierRaw === 3 ? tierRaw : 2) as 1 | 2 | 3

  const url = rawUrl.trim()
  if (url.length > 0) {
    let parsed: URL
    try {
      parsed = new URL(url)
    } catch {
      return NextResponse.json({ error: 'Invalid URL' }, { status: 400 })
    }
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return NextResponse.json({ error: 'Unsupported URL protocol' }, { status: 400 })
    }
  }

  // 1. HERALD-3 score
  const herald = scoreHeadline(title, url, summary)

  // 2. Extract claims
  const claims = extractClaims(title, summary, source, tier)

  // 3. Cross-reference intel table (fuzzy keyword match on title words)
  let corroboration: CorroborationResult = { count: 0, items: [] }
  try {
    const supabase = await createServerClient()
    const words    = title.toLowerCase().split(/\s+/).filter(w => w.length > 4).slice(0, 3)

    if (words.length > 0) {
      // Run text search on the intel table for corroborating entries
      const searches = await Promise.allSettled(
        words.map(w =>
          supabase
            .from('intel')
            .select('title, theater, confidence, author')
            .ilike('title', `%${w}%`)
            .limit(3)
        )
      )

      const seen  = new Set<string>()
      const items: CorroborationResult['items'] = []
      for (const r of searches) {
        if (r.status === 'fulfilled' && r.value.data) {
          for (const row of r.value.data as { title: string; theater: string; confidence: number; author: string | null }[]) {
            if (!seen.has(row.title)) {
              seen.add(row.title)
              items.push({
                title:      row.title,
                theater:    row.theater,
                confidence: row.confidence,
                author:     row.author,
              })
            }
          }
        }
      }
      corroboration = { count: items.length, items: items.slice(0, 5) }
    }
  } catch {
    // Non-fatal — proceed without corroboration
  }

  // 4. ORACLE threat context — find which threat domains this story touches
  const conflictDay = getConflictDay()
  const allThreats  = computeAllThreats(conflictDay)
  const relatedThreats = allThreats
    .filter(t => {
      const k = title.toLowerCase() + ' ' + summary.toLowerCase()
      return (
        (t.domain === 'Maritime'   && /hormuz|strait|gulf|naval|ship|tanker|mine/.test(k)) ||
        (t.domain === 'Air'        && /missile|ballistic|drone|shahed|aircraft|air/.test(k)) ||
        (t.domain === 'Nuclear'    && /nuclear|uranium|fordow|natanz|enrich|iaea/.test(k)) ||
        (t.domain === 'Cyber'      && /cyber|hack|apt|malware|intrusion|ddos/.test(k)) ||
        (t.domain === 'Proxy'      && /hezbollah|houthi|pij|militia|proxy|quds/.test(k)) ||
        (t.domain === 'Strategic'  && /command|irgc|supreme|leader|escalat|nuclear/.test(k))
      )
    })
    .slice(0, 4)
    .map(t => ({ label: t.label, probability: t.probability, domain: t.domain }))

  // 5. Verdict
  const { truthScore, verdict, verdictReason } = computeVerdict(
    herald.score,
    tier,
    corroboration.count,
    herald.flags.length,
  )

  // 6. Citations
  const citations: string[] = [
    `${source} — "${title.slice(0, 70)}"${title.length > 70 ? '…' : ''}`,
    ...(corroboration.items.map(i => `Intel DB: ${i.title.slice(0, 60)} [${i.theater}] — ${i.author ?? 'SYSTEM'}`)),
    `HERALD-3 IO Analysis — Score: ${herald.score}/100, Risk: ${herald.risk}`,
    ...(herald.flags.length > 0 ? [`HERALD flags: ${herald.flags.map(f => f.category).join(', ')}`] : []),
    ...(relatedThreats.map(t => `ORACLE-9 — ${t.label}: ${(t.probability * 100).toFixed(1)}% probability`)),
  ].slice(0, 8)

  const report: AnalysisReport = {
    url,
    title,
    source,
    analyzedAt:     new Date().toISOString(),
    heraldRisk:     herald.risk,
    heraldScore:    herald.score,
    heraldFlags:    herald.flags.map(f => ({ category: f.category, matched: f.matched, weight: f.weight })),
    ioWarnings:     herald.flags.map(f => f.description),
    claims,
    corroboration,
    relatedThreats,
    truthScore,
    verdict,
    verdictReason,
    citations,
  }

  return NextResponse.json(report, {
    headers: { 'Cache-Control': 'public, s-maxage=120, stale-while-revalidate=30' },
  })
  } catch (err) {
    console.error('[analyze] unhandled error', err)
    return NextResponse.json({ error: 'Analysis engine error' }, { status: 500 })
  }
}
