/**
 * Conflict-day runtime utilities
 *
 * All values are computed fresh on every server render because every dashboard
 * page sets `export const revalidate = 0` (no ISR caching). This means the
 * dashboard never needs a rebuild or a VS Code session to advance — just serve
 * the next request and Day N+1 resolves automatically.
 *
 * Operation Epic Fury started 0200Z 01 MAR 2026 (Day 1).
 */

/** UTC epoch for Day 1 — 2026-03-01T00:00:00Z */
export const CONFLICT_EPOCH = Date.UTC(2026, 2, 1)

/** War start date string, fixed */
export const CONFLICT_START = '01 MAR 2026'

/** Current conflict day (1-indexed). Always up-to-date at request time. */
export function getConflictDay(): number {
  return Math.max(1, Math.floor((Date.now() - CONFLICT_EPOCH) / 86_400_000) + 1)
}

/**
 * Full date string for a given conflict day.
 * @example toDateStr(22) → "22 MARCH 2026"
 */
export function toDateStr(day: number): string {
  const date = new Date(CONFLICT_EPOCH + (day - 1) * 86_400_000)
  return date
    .toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      timeZone: 'UTC',
    })
    .toUpperCase()
}

/**
 * Short date string for a given conflict day.
 * @example toShortDate(22) → "22 MAR 2026"
 */
export function toShortDate(day: number): string {
  const date = new Date(CONFLICT_EPOCH + (day - 1) * 86_400_000)
  return date
    .toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    })
    .toUpperCase()
}

/**
 * Military DTG string for a given conflict day and hour (UTC).
 * @example toDTG(22, 8) → "220800Z MAR 2026"
 */
export function toDTG(day: number, hourZ = 8): string {
  const date = new Date(CONFLICT_EPOCH + (day - 1) * 86_400_000)
  const dd = String(day).padStart(2, '0')
  const hh = String(hourZ).padStart(2, '0')
  const mon = date
    .toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' })
    .toUpperCase()
  const yr = date.getUTCFullYear()
  return `${dd}${hh}00Z ${mon} ${yr}`
}

/**
 * Zero-padded day number string, e.g. "22" → for SITREP numbering.
 */
export function dayPad(day: number): string {
  return String(day).padStart(2, '0')
}
