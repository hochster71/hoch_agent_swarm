// engine/engine.js
//
// Orchestrator: a DigestRequest -> validated, cited Digest (fail-closed).
//
// Pipeline (the deterministic part that is REAL here):
//   1. Assemble a candidate Digest from the request (topic, sources, drafted
//      change-claims, uncertainty).
//   2. Auto-seed the uncertainty section if the author left it empty (the
//      mandatory section can never be empty-by-omission): claims with only
//      single-source support and any source with no verifiable text are surfaced
//      as honest, machine-derived limits — it never invents topical doubts.
//   3. Run the citation-coverage linter. If it fails, THROW — the digest does not
//      render. This is the moat.
//   4. Return the Digest (coverage stamped). Rendering is engine/render.js.

'use strict';

const { makeDigest, DISCLAIMER } = require('./schemas');
const { lintDigest, summarize } = require('./linter');

class DigestLintError extends Error {
  constructor(result) {
    super('digest failed the citation-coverage linter:\n' + summarize(result));
    this.name = 'DigestLintError';
    this.code = 'DIGEST_LINT_FAILED';
    this.result = result;
  }
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function autoUncertainty(digest) {
  if (digest.uncertainty.some((u) => String(u).trim())) return;
  const notes = [];
  const single = digest.changes.filter((c) => c.citations.length === 1);
  if (single.length) {
    notes.push(`${single.length} change(s) rest on a single source; treat as provisional until corroborated.`);
  }
  const thin = digest.sources.filter((s) => String(s.text).trim() === '');
  if (thin.length) {
    notes.push('Some sources could not be quote-grounded from provided text; their exact support was not machine-verified.');
  }
  notes.push('This digest covers only what the provided sources state; it is not an exhaustive review, and newer or superseding regulations may exist.');
  digest.uncertainty = notes;
}

// request: { topic, period, sources[], changes[], uncertainty[] }
function generateDigest(request) {
  const digest = makeDigest({
    topic: request.topic,
    period: request.period,
    changes: request.changes || [],
    uncertainty: request.uncertainty || [],
    sources: request.sources || [],
    disclaimer: DISCLAIMER,
  });

  autoUncertainty(digest);

  const result = lintDigest(digest);
  digest.coverage_pct = result.coverage_pct;
  digest.generated_at = nowIso();
  if (!result.passed) throw new DigestLintError(result);

  return digest;
}

module.exports = { generateDigest, DigestLintError, autoUncertainty };
