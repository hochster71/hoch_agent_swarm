// engine/linter.js
//
// Citation-coverage LINTER — the product's moat (Node port of the proven
// hrf-clarity-briefs linter). The rule: a factual change-claim without a
// grounded citation does not ship. Fails-closed on any of:
//
//   * a change-claim has zero citations               (COVERAGE)
//   * a citation references a source id that doesn't exist (UNRESOLVED_SOURCE)
//   * a citation's quote is not found verbatim in that source (UNGROUNDED_QUOTE)
//   * the mandatory "What we're uncertain about" section is empty (EMPTY_UNCERTAINTY)
//   * the mandatory disclaimer is missing (MISSING_DISCLAIMER)
//   * a change-claim's text is empty (EMPTY_CLAIM)
//   * the digest has no claims at all (COVERAGE)
//
// A shippable digest requires coverage_pct === 100 AND no violations.
//
// HONEST SCOPE: verbatim quote-grounding proves a quote was really present in the
// source. It does NOT prove the quote semantically supports the claim — that
// deeper fact-check is an optional LLM "council" pass (README integration point).
// This linter is the deterministic floor.

'use strict';

const COVERAGE = 'COVERAGE';
const UNRESOLVED_SOURCE = 'UNRESOLVED_SOURCE';
const UNGROUNDED_QUOTE = 'UNGROUNDED_QUOTE';
const EMPTY_UNCERTAINTY = 'EMPTY_UNCERTAINTY';
const MISSING_DISCLAIMER = 'MISSING_DISCLAIMER';
const EMPTY_CLAIM = 'EMPTY_CLAIM';

function normalize(text) {
  return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

// True iff `quote` appears (whitespace-normalized) within source.text.
// Empty quote => citation-by-reference only (allowed if the source id resolves),
// but it earns no anti-fabrication guarantee. Missing source text => fail closed.
function quoteIsGrounded(quote, source) {
  if (String(quote).trim() === '') return true;
  if (String(source.text).trim() === '') return false;
  return normalize(source.text).indexOf(normalize(quote)) !== -1;
}

function lintDigest(digest) {
  const violations = [];
  const sourceIds = {};
  for (const s of digest.sources) sourceIds[s.id] = s;

  const total = digest.changes.length;
  let cited = 0;

  digest.changes.forEach((change, i) => {
    if (String(change.text).trim() === '') {
      violations.push({ kind: EMPTY_CLAIM, message: 'empty change-claim text', claim_index: i, claim_text: change.text });
      return;
    }
    if (change.citations.length === 0) {
      violations.push({ kind: COVERAGE, message: 'change-claim has no citation (uncited claims may not ship)', claim_index: i, claim_text: change.text });
    } else {
      cited += 1;
    }
    for (const c of change.citations) {
      const src = sourceIds[c.source_id];
      if (!src) {
        violations.push({ kind: UNRESOLVED_SOURCE, message: `citation references unknown source_id '${c.source_id}'`, claim_index: i, claim_text: change.text });
        continue;
      }
      if (!quoteIsGrounded(c.quote, src)) {
        violations.push({ kind: UNGROUNDED_QUOTE, message: `quote not found verbatim in source '${c.source_id}' (${src.url || 'no url'}) — possible fabrication`, claim_index: i, claim_text: change.text });
      }
    }
  });

  const coverage_pct = total > 0 ? (cited / total) * 100 : 0;

  if (digest.uncertainty.filter((u) => String(u).trim()).length === 0) {
    violations.push({ kind: EMPTY_UNCERTAINTY, message: "the mandatory 'What we're uncertain about' section is empty" });
  }
  if (String(digest.disclaimer).trim() === '') {
    violations.push({ kind: MISSING_DISCLAIMER, message: 'mandatory disclaimer is missing' });
  }
  if (total === 0) {
    violations.push({ kind: COVERAGE, message: 'digest has no change-claims' });
  }

  const blocking = new Set([COVERAGE, UNRESOLVED_SOURCE, UNGROUNDED_QUOTE, EMPTY_UNCERTAINTY, MISSING_DISCLAIMER, EMPTY_CLAIM]);
  const passed = coverage_pct === 100 && total > 0 && !violations.some((v) => blocking.has(v.kind));

  return { passed, coverage_pct, violations, total_claims: total, cited_claims: cited };
}

function summarize(result) {
  const head = result.passed ? 'PASS' : 'FAIL';
  const lines = [`[${head}] citation coverage = ${result.coverage_pct.toFixed(1)}% (${result.cited_claims}/${result.total_claims} claims cited); ${result.violations.length} violation(s).`];
  for (const v of result.violations) {
    const loc = v.claim_index != null ? ` [claim #${v.claim_index}]` : '';
    lines.push(`  - ${v.kind}${loc}: ${v.message}`);
  }
  return lines.join('\n');
}

module.exports = {
  lintDigest, summarize, quoteIsGrounded, normalize,
  COVERAGE, UNRESOLVED_SOURCE, UNGROUNDED_QUOTE, EMPTY_UNCERTAINTY, MISSING_DISCLAIMER, EMPTY_CLAIM,
};
