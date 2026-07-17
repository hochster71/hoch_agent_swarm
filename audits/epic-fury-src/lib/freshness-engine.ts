/**
 * Content Freshness Engine
 *
 * Centralized freshness tracking, SLA enforcement, and content-age computation.
 * Every piece of dashboard content has a freshness SLA. The engine computes
 * whether content is FRESH / AGING / STALE based on when it was last produced
 * relative to the current time and CONFLICT_DAY.
 *
 * This runs on EVERY request (revalidate = 0) — no manual intervention needed.
 */

import { getConflictDay } from './conflict-day'

// ── Freshness tiers ──────────────────────────────────────────────────────────

export type FreshnessLevel = 'FRESH' | 'AGING' | 'STALE'

export interface FreshnessStatus {
  level: FreshnessLevel
  ageMs: number
  ageDays: number
  maxAgeMs: number
  pctConsumed: number    // 0-100+ : how much of the SLA is consumed
  label: string          // Human-readable, e.g. "FRESH · 4m ago"
  dayDrift: number       // How many days behind CONFLICT_DAY the content is
}

/** Content types and their freshness SLAs (milliseconds) */
export const FRESHNESS_SLA: Record<string, number> = {
  intel:          5 * 60_000,       // 5 min — live intel rows
  ingest:        10 * 60_000,       // 10 min — HERALD pipeline
  sitrep:        15 * 60_000,       // 15 min — batch analysis
  threat:        30 * 60_000,       // 30 min — ORACLE threat model
  digest:        30 * 60_000,       // 30 min — intel digest
  forecast:      30 * 60_000,       // 30 min — foresight forecast
  economic:      10 * 60_000,       // 10 min — spot prices
  newsroom:      6 * 3_600_000,     // 6 hours — broadcast scripts
  staticFallback: 24 * 3_600_000,   // 24 hours — hardcoded fallback data
}

// ── Core freshness computation ───────────────────────────────────────────────

/**
 * Compute freshness status for any piece of content.
 *
 * @param lastUpdatedAt  ISO timestamp or epoch ms of when content was last produced
 * @param contentType    Key into FRESHNESS_SLA
 * @param authoredDay    Optional: the conflict day the content was written for
 */
export function computeFreshness(
  lastUpdatedAt: string | number | null,
  contentType: keyof typeof FRESHNESS_SLA,
  authoredDay?: number,
): FreshnessStatus {
  const now = Date.now()
  const sla = FRESHNESS_SLA[contentType] ?? FRESHNESS_SLA.staticFallback
  const currentDay = getConflictDay()

  // If no timestamp, content is maximally stale
  if (lastUpdatedAt == null) {
    return {
      level: 'STALE',
      ageMs: Infinity,
      ageDays: Infinity,
      maxAgeMs: sla,
      pctConsumed: 999,
      label: 'STALE · no timestamp',
      dayDrift: authoredDay != null ? currentDay - authoredDay : Infinity,
    }
  }

  const updatedMs = typeof lastUpdatedAt === 'number'
    ? lastUpdatedAt
    : new Date(lastUpdatedAt).getTime()

  const ageMs = Math.max(0, now - updatedMs)
  const ageDays = ageMs / 86_400_000
  const pctConsumed = Math.round((ageMs / sla) * 100)
  const dayDrift = authoredDay != null ? currentDay - authoredDay : 0

  // Level determination
  let level: FreshnessLevel
  if (dayDrift > 1) {
    level = 'STALE'   // Content is for a previous conflict day
  } else if (pctConsumed <= 100) {
    level = 'FRESH'
  } else if (pctConsumed <= 200) {
    level = 'AGING'
  } else {
    level = 'STALE'
  }

  // Human-readable label
  let label: string
  if (ageMs < 60_000) {
    label = `${level} · ${Math.round(ageMs / 1000)}s ago`
  } else if (ageMs < 3_600_000) {
    label = `${level} · ${Math.round(ageMs / 60_000)}m ago`
  } else if (ageMs < 86_400_000) {
    label = `${level} · ${(ageMs / 3_600_000).toFixed(1)}h ago`
  } else {
    label = `${level} · ${ageDays.toFixed(1)}d ago`
  }

  if (dayDrift > 0) {
    label += ` (D${authoredDay} → D${currentDay})`
  }

  return { level, ageMs, ageDays, maxAgeMs: sla, pctConsumed, label, dayDrift }
}

// ── Day-aware content adaptation ─────────────────────────────────────────────

/**
 * Given a static template string authored for a specific day, adapt it
 * so day references stay contextually accurate. Replaces absolute day
 * references with relative framing ("N days ago") when content is stale.
 *
 * @param text       The original static text
 * @param authoredDay The conflict day the text was written about
 */
export function adaptContentForCurrentDay(text: string, authoredDay: number): string {
  const currentDay = getConflictDay()
  if (currentDay === authoredDay) return text  // Still current — no adaptation needed

  const drift = currentDay - authoredDay

  // Prepend a staleness notice for significantly drifted content
  if (drift >= 2) {
    return `[ARCHIVED — Day ${authoredDay} content · ${drift} days ago] ${text}`
  }

  return text
}

// ── Aggregate freshness for platform health ──────────────────────────────────

export interface PlatformFreshnessReport {
  overallLevel: FreshnessLevel
  conflictDay: number
  generatedAt: string
  contentTypes: Record<string, FreshnessStatus>
  staleCount: number
  agingCount: number
  freshCount: number
}

/**
 * Build a platform-wide freshness report from multiple content timestamps.
 * Used by the governor and platform status endpoint.
 */
export function buildFreshnessReport(
  timestamps: Record<string, { lastUpdatedAt: string | number | null; authoredDay?: number }>
): PlatformFreshnessReport {
  const contentTypes: Record<string, FreshnessStatus> = {}
  let staleCount = 0
  let agingCount = 0
  let freshCount = 0

  for (const [key, val] of Object.entries(timestamps)) {
    const slaKey = key as keyof typeof FRESHNESS_SLA
    const status = computeFreshness(val.lastUpdatedAt, slaKey, val.authoredDay)
    contentTypes[key] = status
    if (status.level === 'STALE') staleCount++
    else if (status.level === 'AGING') agingCount++
    else freshCount++
  }

  let overallLevel: FreshnessLevel = 'FRESH'
  if (staleCount > 0) overallLevel = 'STALE'
  else if (agingCount > 0) overallLevel = 'AGING'

  return {
    overallLevel,
    conflictDay: getConflictDay(),
    generatedAt: new Date().toISOString(),
    contentTypes,
    staleCount,
    agingCount,
    freshCount,
  }
}

// ── Static content day-drift detection ───────────────────────────────────────

/**
 * Check if static/fallback content is stale relative to current conflict day.
 * Returns true if content should be regenerated or flagged.
 */
export function isStaticContentStale(authoredDay: number, maxDriftDays = 1): boolean {
  return getConflictDay() - authoredDay > maxDriftDays
}

/**
 * Build an "as-of" disclaimer for stale static content.
 */
export function staleDisclaimer(authoredDay: number): string | null {
  const currentDay = getConflictDay()
  const drift = currentDay - authoredDay
  if (drift <= 0) return null
  return `Content reflects Day ${authoredDay} assessment. Current: Day ${currentDay} (+${drift}d).`
}
