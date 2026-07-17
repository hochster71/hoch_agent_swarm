// test/engine.test.js
//
// HRF — Compliance Change Digest — ENGINE tests (pure Node, no framework).
// Proves the citation-coverage linter is a real fail-closed moat: uncited claims,
// unresolved sources, and ungrounded (fabricated) quotes are all rejected; a
// fully-cited digest with grounded quotes renders with 100% coverage and the
// mandatory uncertainty + disclaimer. Run: node test/engine.test.js

'use strict';

const assert = require('assert');
const { generateDigest, buildDigest, DigestLintError, DISCLAIMER } = require('../engine');
const { lintDigest } = require('../engine/linter');
const { makeDigest } = require('../engine/schemas');

let pass = 0, fail = 0;
function ok(name, fn) {
  try { fn(); console.log('  PASS  ' + name); pass++; }
  catch (e) { console.log('  FAIL  ' + name + '  -> ' + e.message); fail++; }
}

console.log('HRF Compliance Change Digest — engine tests\n');

const SOURCE_TEXT =
  'Effective 1 January 2027, covered entities must complete an annual data ' +
  'protection impact assessment. The reporting deadline for breaches is reduced ' +
  'from 72 hours to 48 hours.';

const GOOD_REQUEST = {
  topic: 'Data Protection Rule Update 2027',
  period: 'Q4 2026 review',
  sources: [
    { id: 's1', title: 'Regulator Notice 2026-14', url: 'https://example.gov/notice/2026-14', text: SOURCE_TEXT },
  ],
  changes: [
    { text: 'Covered entities must now complete an annual data protection impact assessment.', affects: ['covered entities'], effective: '2027-01-01',
      citations: [{ source_id: 's1', quote: 'covered entities must complete an annual data protection impact assessment' }] },
    { text: 'The breach reporting deadline is shortened to 48 hours.', affects: ['compliance teams'],
      citations: [{ source_id: 's1', quote: 'reduced\nfrom 72 hours to 48 hours' }] },
  ],
};

// --- A fully-cited, grounded digest PASSES with 100% coverage ---
ok('fully-cited grounded digest -> 100% coverage, renders', () => {
  const { digest, markdown } = buildDigest(GOOD_REQUEST);
  assert.strictEqual(digest.coverage_pct, 100);
  assert.ok(markdown.includes('## What changed'));
  assert.ok(markdown.includes("What we're uncertain about"));
  assert.ok(markdown.includes(digest.sources[0].url), 'source url should appear');
  assert.ok(markdown.includes('[1]'), 'inline citation footnote should appear');
});

// --- Whitespace-normalized quote grounding survives reflow ---
ok('quote grounding tolerates whitespace/newline reflow', () => {
  const { digest } = buildDigest(GOOD_REQUEST);
  assert.strictEqual(digest.coverage_pct, 100); // second claim used a quote with a newline
});

// --- An UNCITED claim fails closed (COVERAGE) ---
ok('uncited change-claim -> DigestLintError (COVERAGE)', () => {
  const req = JSON.parse(JSON.stringify(GOOD_REQUEST));
  req.changes.push({ text: 'A brand-new obligation with no citation.', citations: [] });
  let threw = null;
  try { generateDigest(req); } catch (e) { threw = e; }
  assert.ok(threw instanceof DigestLintError, 'expected DigestLintError');
  assert.ok(threw.result.violations.some((v) => v.kind === 'COVERAGE'), 'expected COVERAGE violation');
});

// --- A citation to a non-existent source fails closed (UNRESOLVED_SOURCE) ---
ok('citation to unknown source -> UNRESOLVED_SOURCE', () => {
  const req = JSON.parse(JSON.stringify(GOOD_REQUEST));
  req.changes[0].citations = [{ source_id: 'does_not_exist', quote: '' }];
  let threw = null;
  try { generateDigest(req); } catch (e) { threw = e; }
  assert.ok(threw instanceof DigestLintError);
  assert.ok(threw.result.violations.some((v) => v.kind === 'UNRESOLVED_SOURCE'));
});

// --- A fabricated quote (not in source) fails closed (UNGROUNDED_QUOTE) ---
ok('fabricated quote -> UNGROUNDED_QUOTE (anti-fabrication)', () => {
  const req = JSON.parse(JSON.stringify(GOOD_REQUEST));
  req.changes[0].citations = [{ source_id: 's1', quote: 'entities must pay a $10,000 fine immediately' }];
  let threw = null;
  try { generateDigest(req); } catch (e) { threw = e; }
  assert.ok(threw instanceof DigestLintError);
  assert.ok(threw.result.violations.some((v) => v.kind === 'UNGROUNDED_QUOTE'));
});

// --- A source with no text cannot ground a non-empty quote (fail closed) ---
ok('empty-text source cannot ground a quote -> UNGROUNDED_QUOTE', () => {
  const req = {
    topic: 't', sources: [{ id: 's1', title: 'x', text: '' }],
    changes: [{ text: 'claim', citations: [{ source_id: 's1', quote: 'something' }] }],
  };
  let threw = null;
  try { generateDigest(req); } catch (e) { threw = e; }
  assert.ok(threw instanceof DigestLintError);
  assert.ok(threw.result.violations.some((v) => v.kind === 'UNGROUNDED_QUOTE'));
});

// --- The mandatory uncertainty section is auto-seeded when omitted ---
ok('uncertainty section is auto-seeded (never empty-by-omission)', () => {
  const { digest } = buildDigest(GOOD_REQUEST); // no uncertainty provided
  assert.ok(digest.uncertainty.length >= 1, 'expected auto-seeded uncertainty notes');
  assert.ok(digest.uncertainty.some((u) => /not an exhaustive review/i.test(u)));
});

// --- A digest with zero claims is not shippable ---
ok('zero-claim digest -> COVERAGE fail', () => {
  let threw = null;
  try { generateDigest({ topic: 't', sources: [{ id: 's1', text: 'x' }], changes: [] }); } catch (e) { threw = e; }
  assert.ok(threw instanceof DigestLintError);
  assert.ok(threw.result.violations.some((v) => v.kind === 'COVERAGE'));
});

// --- Missing disclaimer fails closed at the linter level ---
ok('empty disclaimer -> MISSING_DISCLAIMER (linter level)', () => {
  const d = makeDigest({
    topic: 't', disclaimer: '',
    sources: [{ id: 's1', text: SOURCE_TEXT }],
    changes: [{ text: 'c', citations: [{ source_id: 's1', quote: 'covered entities' }] }],
    uncertainty: ['x'],
  });
  const r = lintDigest(d);
  assert.strictEqual(r.passed, false);
  assert.ok(r.violations.some((v) => v.kind === 'MISSING_DISCLAIMER'));
});

// --- Every digest carries the exact disclaimer + 'not legal advice' ---
ok('digest embeds the mandatory not-legal-advice disclaimer', () => {
  const { digest, markdown } = buildDigest(GOOD_REQUEST);
  assert.strictEqual(digest.disclaimer, DISCLAIMER);
  assert.ok(/NOT LEGAL ADVICE/i.test(markdown));
});

// --- Partial coverage (some cited, some not) never rounds up to pass ---
ok('partial coverage cannot pass (coverage must be exactly 100)', () => {
  const req = JSON.parse(JSON.stringify(GOOD_REQUEST));
  req.changes.push({ text: 'uncited', citations: [] });
  const d = makeDigest(req);
  d.uncertainty = ['x'];
  const r = lintDigest(d);
  assert.ok(r.coverage_pct < 100);
  assert.strictEqual(r.passed, false);
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
