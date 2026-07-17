// engine/schemas.js
//
// Data model for the Compliance Change Digest. A digest is built ONLY from the
// source documents the customer provides; every change-claim must be cited back
// to one of those sources, and each citation's quote must appear verbatim in the
// cited source's text (deterministic anti-fabrication).

'use strict';

const DISCLAIMER =
  'INFORMATION, NOT LEGAL ADVICE. This digest is a plain-English summary generated ' +
  'ONLY from the source documents you provided. It is not legal, compliance, or ' +
  'regulatory advice, does not create any professional relationship, and may be ' +
  'incomplete or out of date. Every statement is cited to your sources; verify ' +
  'against the primary text and consult qualified counsel before you act.';

// A Source is one provided regulatory/reference document.
function makeSource(o) {
  return {
    id: String(o.id),
    title: o.title ? String(o.title) : '',
    url: o.url ? String(o.url) : '',
    text: o.text ? String(o.text) : '',
  };
}

// A Citation points at a source and (ideally) quotes it verbatim.
function makeCitation(o) {
  return {
    source_id: String(o.source_id),
    quote: o.quote != null ? String(o.quote) : '',
  };
}

// A Change is one plain-English claim about what changed / who it affects.
function makeChange(o) {
  return {
    text: o.text != null ? String(o.text) : '',
    affects: Array.isArray(o.affects) ? o.affects.map(String) : (o.affects ? [String(o.affects)] : []),
    effective: o.effective ? String(o.effective) : '',
    citations: Array.isArray(o.citations) ? o.citations.map(makeCitation) : [],
  };
}

// A Digest is the assembled, to-be-linted product.
function makeDigest(o) {
  return {
    topic: o.topic != null ? String(o.topic) : '',
    period: o.period ? String(o.period) : '',
    changes: Array.isArray(o.changes) ? o.changes.map(makeChange) : [],
    uncertainty: Array.isArray(o.uncertainty) ? o.uncertainty.map(String) : [],
    sources: Array.isArray(o.sources) ? o.sources.map(makeSource) : [],
    disclaimer: o.disclaimer != null ? String(o.disclaimer) : DISCLAIMER,
    coverage_pct: 0,
    generated_at: '',
  };
}

module.exports = { DISCLAIMER, makeSource, makeCitation, makeChange, makeDigest };
