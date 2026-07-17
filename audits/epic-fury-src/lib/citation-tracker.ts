/**
 * lib/citation-tracker.ts — NEXUS Citation Intelligence System
 *
 * Provides structured, tier-classified citations for all intelligence
 * reports in the EPIC FURY pipeline.
 *
 * Citation tiers follow Intelligence Community source evaluation standards:
 *   T1 — Primary/Official: DOD, State, IAEA, wire services (Reuters, AP)
 *   T2 — Established media: major newspapers, broadcasters, specialist outlets
 *   T3 — OSINT/Unclassified: social media aggregators, blogs, unverified
 *
 * Citation format follows a modified ISOO/DoD hybrid appropriate for
 * unclassified open-source intelligence reporting.
 */

// ---------------------------------------------------------------------------
// Source Classification
// ---------------------------------------------------------------------------

const T1_DOMAINS = [
  'reuters.com', 'apnews.com',
  'dod.gov', 'state.gov', 'whitehouse.gov', 'defense.gov', 'navy.mil',
  'centcom.mil', 'eucom.mil', 'jcs.mil',
  'iaea.org', 'un.org', 'nato.int',
  'gov.il', 'mod.gov.il',
  'mod.go.jp', 'gov.uk',
] as const

const T2_DOMAINS = [
  'bbc.com', 'bbc.co.uk', 'cnn.com',
  'nytimes.com', 'wsj.com', 'ft.com', 'economist.com',
  'theguardian.com', 'washingtonpost.com',
  'aljazeera.com', 'middleeasteye.net',
  'foreignpolicy.com', 'foreignaffairs.com',
  'defensenews.com', 'janes.com',
  'usni.org',             // USNI News
  'understandingwar.org', // ISW
  'rand.org',
  'irannewsupdate.com', 'iranintl.com',
  'timesofisrael.com', 'jpost.com', 'haaretz.com',
  'oilprice.com', 'platts.com', 'icis.com',
] as const

/** Classify a source URL into a tier (1=official, 2=established, 3=OSINT) */
export function classifySourceTier(sourceUrl: string | null, sourceName = ''): 1 | 2 | 3 {
  if (!sourceUrl) {
    // Try to infer from name
    const name = sourceName.toLowerCase()
    if (name.includes('reuters') || name.includes('ap news') || name.includes('associated press')) return 1
    if (name.includes('bbc') || name.includes('al jazeera') || name.includes('usni') || name.includes('isw')) return 2
    return 3
  }
  const url = sourceUrl.toLowerCase()
  if (T1_DOMAINS.some(d => url.includes(d))) return 1
  if (T2_DOMAINS.some(d => url.includes(d))) return 2
  return 3
}

export type SourceTier = 1 | 2 | 3

export const TIER_LABELS: Record<SourceTier, string> = {
  1: 'Primary/Official',
  2: 'Established Media',
  3: 'OSINT/Unverified',
}

export const TIER_RELIABILITY: Record<SourceTier, string> = {
  1: 'HIGH',
  2: 'MEDIUM-HIGH',
  3: 'VARIABLE',
}

// ---------------------------------------------------------------------------
// Citation Data Shape
// ---------------------------------------------------------------------------

export interface Citation {
  index:       number
  title:       string
  sourceName:  string
  sourceUrl:   string | null
  sourceType:  string
  tier:        SourceTier
  tierLabel:   string
  reliability: string
  retrievedAt: string  // ISO 8601
  formatted:   string  // Pre-formatted citation string
}

// ---------------------------------------------------------------------------
// Build a single citation
// ---------------------------------------------------------------------------

export function buildCitation(params: {
  title:      string
  sourceName: string
  sourceUrl:  string | null
  sourceType: string
  index:      number
}): Citation {
  const { title, sourceName, sourceUrl, sourceType, index } = params
  const tier       = classifySourceTier(sourceUrl, sourceName)
  const tierLabel  = TIER_LABELS[tier]
  const reliability = TIER_RELIABILITY[tier]
  const retrievedAt = new Date().toISOString()

  const dateStr = new Date(retrievedAt).toLocaleDateString('en-US', {
    year:    'numeric',
    month:   'short',
    day:     'numeric',
    hour:    '2-digit',
    minute:  '2-digit',
    timeZone: 'UTC',
  })

  const titleSnip = title.length > 90 ? title.slice(0, 87) + '...' : title
  const formatted = [
    `[${index + 1}] ${sourceName} (${tierLabel} — ${reliability})`,
    `    "${titleSnip}"`,
    `    Retrieved: ${dateStr} UTC`,
    sourceUrl ? `    URL: ${sourceUrl}` : null,
  ].filter(Boolean).join('\n')

  return { index, title, sourceName, sourceUrl, sourceType, tier, tierLabel, reliability, retrievedAt, formatted }
}

// ---------------------------------------------------------------------------
// Build a citation block from multiple sources
// ---------------------------------------------------------------------------

export function buildCitationBlock(citations: Citation[]): string {
  return [
    'SOURCES / CITATIONS',
    '─'.repeat(50),
    ...citations.map(c => c.formatted),
    '─'.repeat(50),
  ].join('\n')
}

// ---------------------------------------------------------------------------
// Inline citation shorthand (for embedding in summaries)
// ---------------------------------------------------------------------------

export function inlineCite(citation: Citation): string {
  const year = new Date(citation.retrievedAt).getUTCFullYear()
  return `[${citation.index + 1}] ${citation.sourceName}, ${year} (T${citation.tier})`
}

// ---------------------------------------------------------------------------
// Parse citation metadata from a tag array (for Supabase round-trips)
// ---------------------------------------------------------------------------

export function getCitationTagValue(tags: string[] | null, prefix: string): string | null {
  if (!tags) return null
  const tag = tags.find(t => t.startsWith(`${prefix}:`))
  return tag ? tag.slice(prefix.length + 1) : null
}

export function buildCitationTags(citation: Citation): string[] {
  return [
    `source_tier:${citation.tier}`,
    `source_reliability:${citation.reliability}`,
    ...(citation.sourceUrl ? [`source_url:${citation.sourceUrl.slice(0, 200)}`] : []),
  ]
}
