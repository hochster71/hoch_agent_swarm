// test/engine.test.js
//
// HSF — Coloring Book Export — engine verification with node:test.
// Dependency-free: node v18+ (node:test), no install, no network.
//
// Covers: story normalization (spec + scenes paths), the FAIL-CLOSED child-safety
// gate, deterministic output, PDF structural validity, page counts, and — the
// money guardrail — the watermark being ALWAYS present unless watermarkFree===true.
//
// Run:  node test/engine.test.js

'use strict';

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const { generateColoringBook, normalizeStory, MAX_SCENES } = require(path.join(ROOT, 'engine'));
const { WATERMARK_TEXT } = require(path.join(ROOT, 'engine', 'render_pdf.js'));
const { assertChildSafe } = require(path.join(ROOT, 'engine', 'safety.js'));

const SAFE_SPEC = {
  who: 'Maya the Brave Gardener',
  oneLiner: 'a girl who planted a garden on the moon',
  journey: 'Maya carried seeds up a silver ladder and learned that patience grows faster than flowers.',
  moments: ['The first sprout — a tiny green hello', 'The rainstorm: umbrellas for everyone'],
  tone: 'Warm',
  ending: 'The moon bloomed.',
  extras: 'Dedicated to grandpa Joe.',
};

const SAFE_SCENES = [
  { kicker: 'Prologue', heading: 'Maya the Brave Gardener', body: 'A girl who planted a garden on the moon.', chips: [] },
  { kicker: 'The Journey', heading: 'Up the silver ladder', body: 'Seeds in her pocket, stars in her hair.', chips: ['seeds'] },
  { kicker: 'The Next Launch', heading: 'The moon bloomed', body: 'And everyone came to picnic in the flowers.', chips: [] },
];

function pdfText(buf) { return buf.toString('latin1'); }
function countPages(buf) {
  const m = pdfText(buf).match(/\/Count (\d+)/);
  return m ? parseInt(m[1], 10) : -1;
}
function watermarkOccurrences(buf) {
  // The watermark string is escaped into the content stream; count raw occurrences.
  const t = pdfText(buf);
  let n = 0, i = 0;
  while ((i = t.indexOf('PREVIEW - PURCHASE TO REMOVE WATERMARK', i)) !== -1) { n++; i++; }
  return n;
}

// ---------------------------------------------------------------------------
// normalization
// ---------------------------------------------------------------------------
test('normalizeStory builds 8-10 scenes from a story SPEC via the vendored story engine', () => {
  const { title, scenes } = normalizeStory({ spec: SAFE_SPEC });
  assert.strictEqual(title, 'Maya the Brave Gardener');
  assert.ok(scenes.length >= 8 && scenes.length <= 10, `expected 8-10 scenes, got ${scenes.length}`);
  assert.match(scenes[0].kicker, /prologue/i);
  assert.match(scenes[scenes.length - 1].kicker, /mission patch/i);
});

test('normalizeStory accepts a prebuilt SCENES array (Story Studio shape)', () => {
  const { title, scenes } = normalizeStory({ scenes: SAFE_SCENES });
  assert.strictEqual(scenes.length, 3);
  assert.strictEqual(title, 'Maya the Brave Gardener'); // falls back to first heading
});

test('normalizeStory rejects empty / garbage input (fail-closed)', () => {
  assert.throws(() => normalizeStory(null), (e) => e.code === 'BAD_INPUT');
  assert.throws(() => normalizeStory({}), (e) => e.code === 'BAD_INPUT');
  assert.throws(() => normalizeStory({ scenes: [] }), (e) => e.code === 'BAD_INPUT');
  assert.throws(() => normalizeStory({ scenes: [{ kicker: '', heading: '', body: '' }] }), (e) => e.code === 'BAD_INPUT');
});

test('normalizeStory caps runaway scene lists at MAX_SCENES and reports the drop', () => {
  const many = Array.from({ length: 30 }, (_, i) => ({ kicker: 'Scene', heading: `Page ${i + 1}`, body: 'A friendly cloud floats by.' }));
  const { scenes, dropped } = normalizeStory({ scenes: many, title: 'Big Book' });
  assert.strictEqual(scenes.length, MAX_SCENES);
  assert.strictEqual(dropped, 30 - MAX_SCENES);
});

// ---------------------------------------------------------------------------
// child-safety gate (fail-closed)
// ---------------------------------------------------------------------------
test('safety gate PASSES ordinary storybook copy', () => {
  const r = assertChildSafe({ title: 'Maya', scenes: SAFE_SCENES });
  assert.strictEqual(r.ok, true);
  assert.ok(r.checked > 0);
});

test('safety gate BLOCKS each unsafe category (fail-closed, whole export refused)', () => {
  const cases = [
    ['weapons', 'The pirate loaded his shotgun and waited.'],
    ['violence_gore', 'Then the dragon was slaughtered in the square.'],
    ['adult_content', 'A sexy stranger appeared at the door.'],
    ['drugs_alcohol', 'Grandpa drank whiskey until late.'],
    ['profanity', 'Damnit, said the wizard.'],
    ['self_harm', 'The knight considered suicide at the bridge.'],
  ];
  for (const [category, body] of cases) {
    assert.throws(
      () => generateColoringBook({ story: { scenes: [{ kicker: 'Scene', heading: 'A page', body }] } }),
      (e) => e.code === 'SAFETY_GATE_FAILED' && e.category === category,
      `expected SAFETY_GATE_FAILED/${category} for: ${body}`
    );
  }
});

test('safety gate scans the TITLE too, not just scenes', () => {
  assert.throws(
    () => generateColoringBook({ story: { title: 'The Gun Club', scenes: SAFE_SCENES } }),
    (e) => e.code === 'SAFETY_GATE_FAILED' && e.category === 'weapons'
  );
});

// ---------------------------------------------------------------------------
// PDF output
// ---------------------------------------------------------------------------
test('generates a structurally valid multi-page PDF: cover + N scenes + back page', () => {
  const r = generateColoringBook({ story: { scenes: SAFE_SCENES } });
  const t = pdfText(r.files.pdf);
  assert.ok(t.startsWith('%PDF-1.4'), 'PDF header');
  assert.ok(t.endsWith('%%EOF'), 'PDF EOF');
  assert.strictEqual(countPages(r.files.pdf), 3 + 2, 'cover + 3 scenes + back');
  assert.strictEqual(r.pages, 5);
  assert.ok(t.includes('xref') && t.includes('trailer'), 'xref + trailer present');
  // line-art really present: stroked paths and outlined (mode 1) text
  assert.ok(/ S\n/.test(t) || / S /.test(t), 'stroke operators present');
  assert.ok(t.includes('1 Tr'), 'outlined (colorable) text present');
});

test('spec path renders 8-10 scene pages plus cover and back', () => {
  const r = generateColoringBook({ story: { spec: SAFE_SPEC } });
  assert.ok(r.scenes >= 8 && r.scenes <= 10);
  assert.strictEqual(countPages(r.files.pdf), r.scenes + 2);
});

test('deterministic: identical input -> identical bytes', () => {
  const a = generateColoringBook({ story: { scenes: SAFE_SCENES } });
  const b = generateColoringBook({ story: { scenes: SAFE_SCENES } });
  assert.ok(a.files.pdf.equals(b.files.pdf), 'same input must produce identical PDF bytes');
});

// ---------------------------------------------------------------------------
// WATERMARK guardrail — the paid boundary
// ---------------------------------------------------------------------------
test('watermark is present on EVERY page by default (preview mode)', () => {
  const r = generateColoringBook({ story: { scenes: SAFE_SCENES } });
  assert.strictEqual(r.watermarked, true);
  // 2 diagonal occurrences per page
  assert.strictEqual(watermarkOccurrences(r.files.pdf), r.pages * 2);
  assert.match(r.files.pdfName, /-preview\.pdf$/);
});

test('watermark disappears ONLY with watermarkFree === true (strict boolean)', () => {
  const free = generateColoringBook({ story: { scenes: SAFE_SCENES }, watermarkFree: true });
  assert.strictEqual(free.watermarked, false);
  assert.strictEqual(watermarkOccurrences(free.files.pdf), 0);
  assert.doesNotMatch(free.files.pdfName, /-preview/);

  // truthy-but-not-true must NOT strip the watermark
  for (const sneaky of [1, 'true', 'yes', {}, []]) {
    const r = generateColoringBook({ story: { scenes: SAFE_SCENES }, watermarkFree: sneaky });
    assert.strictEqual(r.watermarked, true, `watermarkFree=${JSON.stringify(sneaky)} must stay watermarked`);
    assert.ok(watermarkOccurrences(r.files.pdf) > 0);
  }
});

test('story content cannot break the PDF or smuggle the watermark away (escaping)', () => {
  const hostile = [{
    kicker: 'Prologue',
    heading: 'A ) sneaky ( heading \\ with parens',
    body: 'endstream endobj trailer %%EOF 1 Tr Q q — a friendly dragon reads PDF specs.',
    chips: [],
  }];
  const r = generateColoringBook({ story: { scenes: hostile, title: 'Escape (Test)' } });
  const t = pdfText(r.files.pdf);
  assert.ok(t.startsWith('%PDF-1.4') && t.endsWith('%%EOF'), 'still a valid PDF envelope');
  assert.strictEqual(countPages(r.files.pdf), 3, 'cover + 1 scene + back');
  assert.strictEqual(watermarkOccurrences(r.files.pdf), 3 * 2, 'watermark intact on every page');
});

test('non-ASCII is stripped, never crashes the latin1 renderer', () => {
  const r = generateColoringBook({
    story: { scenes: [{ kicker: 'Prologue', heading: 'Café 🚀 Über-fun', body: 'Émojis 🌈 and àccents everywhere.' }], title: 'Fün' },
  });
  assert.ok(pdfText(r.files.pdf).startsWith('%PDF-1.4'));
});
