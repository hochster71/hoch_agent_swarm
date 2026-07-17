/**
 * DATA PROVENANCE — the single source of truth for what is REAL and what is SIMULATED.
 *
 * WHY THIS EXISTS
 * ---------------
 * Epic Fury sells BOTH: a simulated conflict (Operation Epic Fury, Day N from a fixed
 * epoch) AND real open-source intelligence (live Supabase feeds, ingested advisories).
 * Before this file, a customer could not tell them apart. `/dashboard/homeland`
 * hardcoded APT33 / Holmium — a REAL Iranian threat actor, with real aliases and real
 * TTPs — marked `status: 'ACTIVE'`, inside a fictional war, under a header reading LIVE.
 * `/dashboard/bda` next to it pulled genuinely live data. Same chrome. No distinction.
 *
 * An intelligence product that blurs that line is worthless at best and dangerous at
 * worst. A paying analyst must never have to guess whether what they are reading is
 * the world or the scenario.
 *
 * THE RULE
 * --------
 * Every dashboard declares its provenance HERE, and the dashboard layout renders that
 * declaration on the page automatically. A dashboard cannot render without a verdict:
 * anything not listed is UNKNOWN and is labelled UNVERIFIED, never quietly "live".
 * Absence of a declaration is never treated as evidence of liveness.
 */

export type Provenance =
  | 'LIVE'       // observed at request time from a real source (Supabase, ingested feed, API)
  | 'SIMULATED'  // Operation Epic Fury scenario content. Not the real world. By design.
  | 'MIXED'      // live source, but scenario elements are interleaved on the page
  | 'PLACEHOLDER'// the page exists but nothing is behind it yet. Not sold.
  | 'UNKNOWN'    // undeclared -> shown as UNVERIFIED. Never assumed live.

export interface ProvenanceInfo {
  provenance: Provenance
  /** Plain-English, shown to the customer. No jargon, no hedging. */
  note: string
}

const P: Record<string, ProvenanceInfo> = {
  // ── LIVE: real data, fetched at request time ──────────────────────────────
  '/dashboard/feed':      { provenance: 'LIVE',      note: 'Live intel feed from the ingestion pipeline.' },
  '/dashboard/newsroom':  { provenance: 'LIVE',      note: 'Generated from live ingested news sources.' },
  '/dashboard/intel':     { provenance: 'LIVE',      note: 'Live records from the intel store.' },
  '/dashboard/oracle':    { provenance: 'LIVE',      note: 'Live model inference over current inputs.' },
  '/dashboard/timeline':  { provenance: 'LIVE',      note: 'Live event records, newest first.' },
  '/dashboard/world':     { provenance: 'LIVE',      note: 'Live world-state records.' },

  // ── SIMULATED: Operation Epic Fury scenario. Real actors may appear, but the
  //    scenario around them is fiction. Say so, loudly, on every page. ────────
  '/dashboard/homeland':  { provenance: 'SIMULATED', note: 'Scenario content. Threat actors named here are real, but their status in this dashboard is part of the Epic Fury simulation — not current reporting.' },
  '/dashboard/hva':       { provenance: 'SIMULATED', note: 'Scenario high-value asset list. Not a real target deck.' },
  '/dashboard/econ':      { provenance: 'SIMULATED', note: 'Scenario economic effects. Not real market data.' },
  '/dashboard/ceasefire': { provenance: 'SIMULATED', note: 'Scenario negotiation track. No such negotiations exist.' },
  '/dashboard/threats':   { provenance: 'SIMULATED', note: 'Scenario threat board. Not a current threat assessment.' },
  '/dashboard/news':      { provenance: 'SIMULATED', note: 'Scenario wire copy. These events did not occur.' },
  '/dashboard/brief':     { provenance: 'SIMULATED', note: 'Scenario daily brief.' },
  '/dashboard/sitrep':    { provenance: 'SIMULATED', note: 'Scenario situation report.' },
  '/dashboard/bda':       { provenance: 'SIMULATED', note: 'Scenario battle damage assessment. Live store, simulated engagements.' },
  '/dashboard/orbat':     { provenance: 'SIMULATED', note: 'Scenario order of battle. Live store, simulated force posture.' },
  '/dashboard/cop':       { provenance: 'SIMULATED', note: 'Scenario common operating picture.' },
  '/dashboard/dmo':       { provenance: 'SIMULATED', note: 'Animated scenario simulation.' },
  '/dashboard/logistics': { provenance: 'SIMULATED', note: 'Scenario logistics picture.' },

  // ── MIXED: the hub interleaves live feed items with scenario narrative ─────
  '/dashboard':           { provenance: 'MIXED',     note: 'This hub shows live feed items alongside Epic Fury scenario narrative. Each panel is labelled.' },

  // ── PLACEHOLDER: shells with no content. They are NOT in the paid tier — you do
  //    not charge for an empty page, and you do not pretend it is "coming soon" while
  //    taking money for it. ───────────────────────────────────────────────────
  '/dashboard/command':   { provenance: 'PLACEHOLDER', note: 'Not built yet. This view has no content behind it.' },
  '/dashboard/debate':    { provenance: 'PLACEHOLDER', note: 'Not built yet. This view has no content behind it.' },
  '/dashboard/foresight': { provenance: 'PLACEHOLDER', note: 'Not built yet. This view has no content behind it.' },
  '/dashboard/visuals':   { provenance: 'PLACEHOLDER', note: 'Not built yet. This view has no content behind it.' },

  // ── Admin surfaces: operator tooling, real by construction ────────────────
  '/dashboard/nexus':     { provenance: 'LIVE',      note: 'Live platform telemetry.' },
  '/dashboard/agents':    { provenance: 'LIVE',      note: 'Live agent roster.' },
  '/dashboard/revenue':   { provenance: 'LIVE',      note: 'Live revenue records.' },
  '/dashboard/workflows': { provenance: 'LIVE',      note: 'Live workflow state.' },
  '/dashboard/autonomous':{ provenance: 'LIVE',      note: 'Live autonomous-enhancement state.' },
  '/dashboard/settings':  { provenance: 'LIVE',      note: 'Your account settings.' },
}

/**
 * Undeclared routes are UNKNOWN — surfaced to the customer as UNVERIFIED.
 * Never assume liveness. Absence of evidence is not evidence of liveness.
 */
export function getProvenance(pathname: string): ProvenanceInfo {
  const exact = P[pathname]
  if (exact) return exact
  const seg = Object.keys(P)
    .filter((k) => k !== '/dashboard' && pathname.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0]
  if (seg) return P[seg]
  return {
    provenance: 'UNKNOWN',
    note: 'This view has not declared where its data comes from. Treat it as unverified.',
  }
}

/** Every route that is scenario content. Used by marketing/legal copy — one source. */
export const SIMULATED_ROUTES = Object.entries(P)
  .filter(([, v]) => v.provenance === 'SIMULATED')
  .map(([k]) => k)

/** Shells with nothing behind them. Must never appear in SUBSCRIBER_ROUTES. */
export const PLACEHOLDER_ROUTES = Object.entries(P)
  .filter(([, v]) => v.provenance === 'PLACEHOLDER')
  .map(([k]) => k)

export const LIVE_ROUTES = Object.entries(P)
  .filter(([, v]) => v.provenance === 'LIVE')
  .map(([k]) => k)
