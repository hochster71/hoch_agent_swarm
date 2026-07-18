// test/engine.test.js
//
// HFF — Recurring Charge Finder — engine tests (node:test, no install, no network).
// Run: node test/engine.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

const ROOT = path.resolve(__dirname, '..');
const { analyze, buildReport } = require(path.join(ROOT, 'engine'));
const { ingestCsv, parseAmount, parseDate, detectDateOrder } = require(path.join(ROOT, 'engine', 'ingest'));
const { normalizeMerchant, detectRecurring, classifyCadence } = require(path.join(ROOT, 'engine', 'recurring'));
const { lintStrings, assertNoAdvice } = require(path.join(ROOT, 'engine', 'advice_linter'));
const { validateCsvInput } = require(path.join(ROOT, 'engine', 'validate'));
const { renderXlsx } = require(path.join(ROOT, 'engine', 'render_xlsx'));
const { renderPdf } = require(path.join(ROOT, 'engine', 'render_pdf'));

// Walks a zip built by engine/zip.js and returns { name: Buffer } for every part.
function readZip(buf) {
  const eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  if (eocd < 0) throw new Error('no end-of-central-directory');
  const count = buf.readUInt16LE(eocd + 10);
  let off = buf.readUInt32LE(eocd + 16);
  const out = {};
  for (let i = 0; i < count; i++) {
    if (buf.readUInt32LE(off) !== 0x02014b50) throw new Error('bad central header');
    const method = buf.readUInt16LE(off + 10);
    const csize = buf.readUInt32LE(off + 20);
    const usize = buf.readUInt32LE(off + 24);
    const nlen = buf.readUInt16LE(off + 28);
    const elen = buf.readUInt16LE(off + 30);
    const clen = buf.readUInt16LE(off + 32);
    const lho = buf.readUInt32LE(off + 42);
    const name = buf.slice(off + 46, off + 46 + nlen).toString('utf8');
    const dataStart = lho + 30 + buf.readUInt16LE(lho + 26) + buf.readUInt16LE(lho + 28);
    const raw = buf.slice(dataStart, dataStart + csize);
    const data = method === 8 ? zlib.inflateRawSync(raw) : raw;
    if (data.length !== usize) throw new Error(name + ' size mismatch');
    out[name] = data;
    off += 46 + nlen + elen + clen;
  }
  return out;
}

const SAMPLE = fs.readFileSync(path.join(ROOT, 'engine', 'sample', 'sample_transactions.csv'), 'utf8');
const UK = fs.readFileSync(path.join(ROOT, 'engine', 'sample', 'sample_uk_messy.csv'), 'utf8');

// ------------------------------------------------------------------ amounts
test('parseAmount handles symbols, separators, parens, trailing minus, EU decimals', () => {
  assert.strictEqual(parseAmount('$15.49'), 15.49);
  assert.strictEqual(parseAmount('£1,234.56'), 1234.56);
  assert.strictEqual(parseAmount('(9.99)'), -9.99);
  assert.strictEqual(parseAmount('42.00-'), -42);
  assert.strictEqual(parseAmount('-€11.99'), -11.99);
  assert.strictEqual(parseAmount('1.234,56'), 1234.56);
  assert.strictEqual(parseAmount('42,50'), 42.5);
  assert.strictEqual(parseAmount('  '), null);
  assert.strictEqual(parseAmount('n/a'), null);
});

// -------------------------------------------------------------------- dates
test('parseDate accepts ISO / US / UK and rejects impossible dates', () => {
  assert.deepStrictEqual(parseDate('2026-02-29', 'us'), null, 'not a leap year');
  assert.deepStrictEqual(parseDate('2024-02-29', 'us'), { y: 2024, m: 2, d: 29 });
  assert.deepStrictEqual(parseDate('03/04/2026', 'us'), { y: 2026, m: 3, d: 4 });
  assert.deepStrictEqual(parseDate('03/04/2026', 'uk'), { y: 2026, m: 4, d: 3 });
  assert.strictEqual(parseDate('13/13/2026', 'us'), null);
  assert.strictEqual(parseDate('nope', 'us'), null);
});

test('detectDateOrder infers UK only when a first component exceeds 12', () => {
  assert.strictEqual(detectDateOrder(['01/02/2026', '03/04/2026']), 'us');
  assert.strictEqual(detectDateOrder(['15/01/2026', '03/04/2026']), 'uk');
  assert.strictEqual(detectDateOrder(['15/01/2026'], 'us'), 'us', 'explicit wins');
});

// ------------------------------------------------------------------- ingest
test('ingest flags unreadable rows with line numbers instead of dropping them', () => {
  const r = ingestCsv(UK);
  const reasons = r.skipped.map((s) => s.reason).sort();
  assert.deepStrictEqual(reasons, ['missing_description', 'unreadable_amount', 'unreadable_date', 'zero_amount']);
  for (const s of r.skipped) assert.ok(Number.isInteger(s.line) && s.line > 1, 'skipped row carries its CSV line');
  assert.strictEqual(r.dateOrder, 'uk');
});

test('ingest rejects a file with no usable columns (fails closed, names the header)', () => {
  assert.throws(() => ingestCsv('foo,bar\n1,2\n'), (e) => e.code === 'MISSING_COLUMNS');
});

test('ingest handles RFC4180 quoting, escaped quotes, CRLF and a BOM', () => {
  const csv = '﻿Date,Description,Amount\r\n2026-01-01,"ACME ""PRO"", INC",10.00\r\n';
  const r = ingestCsv(csv);
  assert.strictEqual(r.transactions.length, 1);
  assert.strictEqual(r.transactions[0].description, 'ACME "PRO", INC');
});

test('validate gate rejects empty and oversized input', () => {
  assert.throws(() => validateCsvInput(''), (e) => e.code === 'EMPTY_FILE');
  assert.throws(() => validateCsvInput(123), (e) => e.code === 'BAD_INPUT_TYPE');
  assert.throws(() => validateCsvInput('x'.repeat(9 * 1024 * 1024)), (e) => e.code === 'FILE_TOO_LARGE');
});

// -------------------------------------------------------------- normalizing
test('normalizeMerchant collapses processor prefixes, store numbers, refs and state tails', () => {
  assert.strictEqual(normalizeMerchant('SQ *SPOTIFY USA INC NY'), normalizeMerchant('SPOTIFY USA INC'));
  assert.strictEqual(normalizeMerchant('NETFLIX.COM  #1000'), normalizeMerchant('NETFLIX.COM #1042'));
  assert.strictEqual(normalizeMerchant('NAMECHEAP.COM RENEWAL REF#A81992'), normalizeMerchant('NAMECHEAP.COM RENEWAL REF#B22071'));
  assert.notStrictEqual(normalizeMerchant('SPOTIFY'), normalizeMerchant('TIDAL MUSIC'));
});

// ----------------------------------------------------------------- cadences
test('classifyCadence maps intervals to the right bucket and calls the rest irregular', () => {
  assert.strictEqual(classifyCadence(7).label, 'weekly');
  assert.strictEqual(classifyCadence(14).label, 'biweekly');
  assert.strictEqual(classifyCadence(30).label, 'monthly');
  assert.strictEqual(classifyCadence(91).label, 'quarterly');
  assert.strictEqual(classifyCadence(182).label, 'semiannual');
  assert.strictEqual(classifyCadence(365).label, 'annual');
  assert.strictEqual(classifyCadence(52).label, 'irregular');
});

// ---------------------------------------------------------------- detection
test('detection finds the seeded cadences in the sample file', () => {
  const r = analyze(SAMPLE);
  const byKey = Object.fromEntries(r.detection.recurring.map((x) => [x.merchantKey, x]));
  assert.ok(byKey['NETFLIX'], 'netflix detected');
  assert.strictEqual(byKey['NETFLIX'].cadence, 'monthly');
  assert.strictEqual(byKey['NETFLIX'].occurrences, 6);
  assert.strictEqual(byKey['BLUE BOTTLE SUBSCRIPTION'].cadence, 'weekly');
  assert.strictEqual(byKey['DROPBOX PLUS'].cadence, 'quarterly');
  assert.strictEqual(byKey['NAMECHEAP RENEWAL'].cadence, 'annual');
});

test('one-off purchases are NOT reported as recurring', () => {
  const r = analyze(SAMPLE);
  const keys = r.detection.recurring.map((x) => x.merchantKey);
  assert.ok(!keys.includes('HOME DEPOT AUSTIN'));
  assert.ok(!keys.includes('DELTA AIR LINES'));
  assert.ok(r.detection.oneOff.some((o) => o.merchantKey === 'DELTA AIR LINES'));
});

test('annualized cost equals typical amount x observed periods per year', () => {
  const r = analyze(SAMPLE);
  const dropbox = r.detection.recurring.find((x) => x.merchantKey === 'DROPBOX PLUS');
  assert.strictEqual(dropbox.typicalAmount, 35.88);
  assert.strictEqual(dropbox.annualizedAmount, 143.52); // 35.88 x 4
  const spotify = r.detection.recurring.find((x) => x.merchantKey === 'SPOTIFY USA INC');
  assert.strictEqual(spotify.annualizedAmount, 143.88); // 11.99 x 12
});

test('a mid-file price increase is reported factually, not as a judgement', () => {
  const r = analyze(SAMPLE);
  const nf = r.detection.recurring.find((x) => x.merchantKey === 'NETFLIX');
  assert.strictEqual(nf.amountChanged, true);
  assert.ok(nf.amountChangePct > 15 && nf.amountChangePct < 17);
  const note = r.summary.notes.find((n) => n.includes('higher than the first observed charge'));
  assert.ok(note, 'the change is described as an observation');
  assert.ok(!/should|recommend|cancel/i.test(note));
});

test('a pattern that stopped charging is flagged as dormant against its own cadence', () => {
  const r = analyze(SAMPLE);
  const gym = r.detection.recurring.find((x) => x.merchantKey === 'PLANET FITNESS AUSTIN');
  assert.strictEqual(gym.noChargeSinceExpected, true);
  const nf = r.detection.recurring.find((x) => x.merchantKey === 'NETFLIX');
  assert.strictEqual(nf.noChargeSinceExpected, false);
});

test('refunds / opposite-sign rows are excluded from recurrence detection', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(r.detection.creditCount, 1);
  const nf = r.detection.recurring.find((x) => x.merchantKey === 'NETFLIX');
  assert.strictEqual(nf.occurrences, 6, 'the refund row is not counted as a charge');
});

test('overlap tags are reported only when 2+ distinct merchants share a tag', () => {
  const r = analyze(SAMPLE);
  const tags = r.detection.overlaps.map((o) => o.tag);
  assert.ok(tags.includes('music streaming'), 'spotify + tidal');
  assert.ok(!tags.includes('cloud storage'), 'dropbox is alone');
});

test('a file where every amount is negative still detects charges (dominant sign)', () => {
  const r = analyze(UK);
  assert.ok(r.detection.recurring.length >= 2);
  assert.strictEqual(r.detection.chargeSign, -1);
  assert.ok(r.detection.recurring.every((x) => x.typicalAmount > 0), 'amounts reported as magnitudes');
});

test('confidence downgrades when the interval is erratic', () => {
  const csv = 'Date,Description,Amount\n2026-01-01,WOBBLY LABS,10.00\n2026-01-29,WOBBLY LABS,10.00\n2026-03-20,WOBBLY LABS,10.00\n2026-04-01,WOBBLY LABS,10.00\n';
  const r = analyze(csv);
  const w = r.detection.recurring.find((x) => x.merchantKey === 'WOBBLY LABS');
  assert.ok(w, 'still surfaced because amounts are identical across 4 charges');
  assert.notStrictEqual(w.confidence, 'high');
});

// ------------------------------------------------------------ advice linter
test('advice linter catches banned recommendation language', () => {
  const v = lintStrings(['We recommend you cancel this subscription.']);
  assert.ok(v.length > 0);
  assert.throws(() => assertNoAdvice(['you should cancel that one']), (e) => e.code === 'ADVICE_LINTER_FAILED');
});

test('advice linter allowlists the mandatory disclaimer (no self-trip)', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(lintStrings([r.disclaimer]).length, 0);
});

test('advice linter FAILS CLOSED: a poisoned merchant name withholds the whole report', () => {
  const csv = 'Date,Description,Amount\n' +
    '2026-01-01,"ACME (we recommend you cancel this)",10.00\n' +
    '2026-02-01,"ACME (we recommend you cancel this)",10.00\n' +
    '2026-03-01,"ACME (we recommend you cancel this)",10.00\n';
  assert.throws(() => analyze(csv), (e) => e.code === 'ADVICE_LINTER_FAILED');
  assert.throws(() => buildReport(csv), (e) => e.code === 'ADVICE_LINTER_FAILED', 'no artifact bytes are produced');
});

// ---------------------------------------------------------------- renderers
test('renderXlsx produces a real, well-formed xlsx package', () => {
  const r = analyze(SAMPLE);
  const buf = renderXlsx(r);
  assert.ok(Buffer.isBuffer(buf) && buf.length > 2000);
  assert.strictEqual(buf.slice(0, 2).toString(), 'PK', 'zip magic');
  // walk the central directory and inflate every entry
  const eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  assert.ok(eocd > 0, 'end-of-central-directory present');
  const count = buf.readUInt16LE(eocd + 10);
  let off = buf.readUInt32LE(eocd + 16);
  const names = [];
  for (let i = 0; i < count; i++) {
    assert.strictEqual(buf.readUInt32LE(off), 0x02014b50, 'central header signature');
    const method = buf.readUInt16LE(off + 10);
    const csize = buf.readUInt32LE(off + 20);
    const usize = buf.readUInt32LE(off + 24);
    const nlen = buf.readUInt16LE(off + 28);
    const lho = buf.readUInt32LE(off + 42);
    const name = buf.slice(off + 46, off + 46 + nlen).toString('utf8');
    names.push(name);
    const lnlen = buf.readUInt16LE(lho + 26);
    const lelen = buf.readUInt16LE(lho + 28);
    const dataStart = lho + 30 + lnlen + lelen;
    const raw = buf.slice(dataStart, dataStart + csize);
    const out = method === 8 ? zlib.inflateRawSync(raw) : raw;
    assert.strictEqual(out.length, usize, name + ' inflates to its declared size');
    if (name.endsWith('.xml')) assert.ok(out.toString('utf8').startsWith('<?xml'), name + ' is xml');
    off += 46 + nlen + buf.readUInt16LE(off + 30) + buf.readUInt16LE(off + 32);
  }
  for (const need of ['[Content_Types].xml', 'xl/workbook.xml', 'xl/styles.xml', 'xl/worksheets/sheet1.xml', 'xl/worksheets/sheet4.xml']) {
    assert.ok(names.includes(need), 'package contains ' + need);
  }
});

test('xlsx escapes hostile merchant text so the sheet XML stays well-formed', () => {
  // The quote is doubled per RFC4180 so the CSV field itself is well-formed;
  // what must survive is the ENGINE output landing in the sheet XML.
  const field = '"<script>&""ACME"';
  const csv = `Date,Description,Amount\n2026-01-01,${field},10.00\n2026-02-01,${field},10.00\n2026-03-01,${field},10.00\n`;
  const r = analyze(csv);
  const buf = renderXlsx(r);
  const parts = readZip(buf);
  const sheet = parts['xl/worksheets/sheet2.xml'].toString('utf8');
  assert.ok(sheet.includes('&lt;script&gt;'), 'markup is entity-escaped');
  assert.ok(!sheet.includes('<script>'), 'raw markup never lands in the sheet');
  assert.ok(sheet.includes('&amp;') && sheet.includes('&quot;'), 'ampersand and quote escaped');
  assert.ok(sheet.endsWith('</worksheet>'), 'sheet XML is complete');
});

test('renderPdf produces a valid single-page PDF with an xref and the disclaimer', () => {
  const r = analyze(SAMPLE);
  const buf = renderPdf(r);
  const s = buf.toString('latin1');
  assert.ok(s.startsWith('%PDF-1.4'));
  assert.ok(s.trimEnd().endsWith('%%EOF'));
  assert.ok(s.includes('/Type /Catalog') && s.includes('/Type /Pages') && s.includes('/Type /Page '));
  assert.ok(/\/Count 1\b/.test(s), 'one page');
  assert.ok(s.includes('xref') && s.includes('startxref'));
  assert.ok(s.includes('organizational tooling only'), 'disclaimer is rendered on the page');
});

test('renderPdf offsets in the xref table point at real object headers', () => {
  const buf = renderPdf(analyze(SAMPLE));
  const s = buf.toString('latin1');
  const start = Number(s.slice(s.lastIndexOf('startxref') + 9).trim().split(/\s/)[0]);
  assert.ok(s.slice(start, start + 4) === 'xref');
  const table = s.slice(start).split('\n').slice(3);
  for (let i = 0; i < 6; i++) {
    const off = Number(table[i].slice(0, 10));
    assert.ok(s.slice(off).startsWith(`${i + 1} 0 obj`), `object ${i + 1} offset is correct`);
  }
});

test('renderers are byte-deterministic for the same input', () => {
  const a = buildReport(SAMPLE);
  const b = buildReport(SAMPLE);
  assert.ok(a.xlsx.equals(b.xlsx), 'xlsx bytes stable');
  assert.ok(a.pdf.equals(b.pdf), 'pdf bytes stable');
});

// -------------------------------------------------------------- end-to-end
test('buildReport returns a report plus both artifacts', () => {
  const { report, xlsx, pdf } = buildReport(SAMPLE);
  assert.strictEqual(report.product, 'hff-recurring-charges');
  assert.ok(report.summary.totals.annualized > 0);
  assert.ok(report.summary.disclaimer.includes('not financial, tax, or legal advice'));
  assert.ok(xlsx.length > 2000 && pdf.length > 1000);
});

test('empty-but-valid file with no repeats returns an honest zero report, not a crash', () => {
  const csv = 'Date,Description,Amount\n2026-01-01,ONE OFF SHOP,10.00\n2026-02-11,ANOTHER SHOP,20.00\n';
  const { report } = buildReport(csv);
  assert.strictEqual(report.summary.counts.recurringPatterns, 0);
  assert.strictEqual(report.summary.totals.annualized, 0);
  assert.ok(report.summary.headline[0].startsWith('0 recurring charge pattern'));
});
