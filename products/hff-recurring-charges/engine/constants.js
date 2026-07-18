// engine/constants.js
//
// HFF — Recurring Charge Finder. Shared constants for the deterministic engine.
'use strict';

const PRODUCT_NAME = 'Recurring Charge Finder';
const PRODUCT_SLUG = 'hff-recurring-charges';

// Mandatory disclaimer. Rendered on every artifact (XLSX summary, PDF, JSON).
// Wording is allowlisted in engine/advice_linter.js so the banner never trips
// its own guardrail.
const DISCLAIMER =
  'This report is organizational tooling only. It lists charges that repeat in the ' +
  'file you uploaded. It is not financial, tax, or legal advice, and it does not ' +
  'tell you what to keep, cancel, or dispute. Verify every line against your own ' +
  'statements before acting.';

// Cadence buckets, in days, keyed by label. [minInclusive, maxInclusive].
const CADENCES = [
  { label: 'weekly',      min: 5,   max: 9,   perYear: 52 },
  { label: 'biweekly',    min: 12,  max: 17,  perYear: 26 },
  { label: 'monthly',     min: 25,  max: 36,  perYear: 12 },
  { label: 'quarterly',   min: 80,  max: 105, perYear: 4 },
  { label: 'semiannual',  min: 165, max: 200, perYear: 2 },
  { label: 'annual',      min: 340, max: 400, perYear: 1 },
];

const IRREGULAR = 'irregular';

// Factual overlap tags. These are OBSERVATIONS about merchant names only — the
// engine never suggests which (if any) to act on.
const OVERLAP_TAGS = [
  { tag: 'video streaming', patterns: ['NETFLIX', 'HULU', 'DISNEY', 'MAX', 'PARAMOUNT', 'PEACOCK', 'APPLE TV'] },
  { tag: 'music streaming', patterns: ['SPOTIFY', 'APPLE MUSIC', 'TIDAL', 'PANDORA', 'YOUTUBE MUSIC'] },
  { tag: 'cloud storage',   patterns: ['DROPBOX', 'ICLOUD', 'GOOGLE STORAGE', 'GOOGLE ONE', 'BOX', 'ONEDRIVE'] },
  { tag: 'fitness',         patterns: ['PELOTON', 'CLASSPASS', 'PLANET FITNESS', 'EQUINOX', 'STRAVA'] },
  { tag: 'news',            patterns: ['NYTIMES', 'NEW YORK TIMES', 'WSJ', 'WASHINGTON POST', 'SUBSTACK', 'ATLANTIC'] },
];

module.exports = { PRODUCT_NAME, PRODUCT_SLUG, DISCLAIMER, CADENCES, IRREGULAR, OVERLAP_TAGS };
