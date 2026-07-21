// test/engine.test.js
//
// HFF — Vendor Spend Rollup — engine tests. Zero dependencies: `node test/engine.test.js`.
// Every assertion checks REAL engine output. Nothing is mocked.
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const {
  ingestCsv, splitCsv, parseDate, parseAmount, detectDateOrder, vendorKey, mapHeaders,
} = require('../engine/ingest');
const { analyzeSpend, median, shareOf } = require('../engine/spend');
const { buildSummary, summaryStrings, money, pct } = require('../engine/summary');
const { lintStrings, assertNoAdvice, BANNED_PHRASES } = require('../engine/advice_linter');
const { validateCsvInput } = require('../engine/validate');
const { renderXlsx } = require('../engine/render_xlsx');
const { renderPdf } = require('../engine/render_pdf');
const { analyze, buildReport } = require('../engine');

let passed = 0;
let failed = 0;
function t(name, fn) {
  try { fn(); passed += 1; console.log('  ok   ' + name); }
  catch (e) { failed += 1; console.error('  FAIL ' + name + '\n       ' + e.message); }
}

const SAMPLE = fs.readFileSync(path.join(__dirname, '..', 'engine', 'sample', 'sample_expenses.csv'), 'utf8');

const MINI = [
  'date,vendor,amount',
  '2026-01-10,Acme LLC,100.00',
  '2026-02-10,Acme LLC,100.00',
  '2026-03-10,Acme LLC,150.00',
  '2026-01-15,Beta Corp,500.00',
].join('\n');

console.log('\n=== CSV parsing ===');

t('splitCsv handles quoted commas', () => {
  const g = splitCsv('a,b\n"x, y",2');
  assert.deepStrictEqual(g[1], ['x, y', '2']);
});

t('splitCsv handles escaped double quotes', () => {
  const g = splitCsv('a\n"say ""hi"""');
  assert.strictEqual(g[1][0], 'say "hi"');
});

t('splitCsv handles CRLF', () => {
  const g = splitCsv('a,b\r\n1,2\r\n');
  assert.strictEqual(g.length, 2);
  assert.deepStrictEqual(g[1], ['1', '2']);
});

t('splitCsv strips a UTF-8 BOM', () => {
  const g = splitCsv('﻿date,vendor\n2026-01-01,X');
  assert.strictEqual(g[0][0], 'date');
});

t('splitCsv drops trailing blank rows', () => {
  const g = splitCsv('a\n1\n\n\n');
  assert.strictEqual(g.length, 2);
});

console.log('\n=== header mapping ===');

t('maps common vendor aliases', () => {
  assert.strictEqual(mapHeaders(['Date', 'Payee', 'Amount']).vendor, 1);
  assert.strictEqual(mapHeaders(['Date', 'Merchant', 'Amount']).vendor, 1);
  assert.strictEqual(mapHeaders(['Date', 'Supplier Name', 'Amount']).vendor, 1);
});

t('prefers a real vendor column over an ambiguous description column', () => {
  const m = mapHeaders(['Date', 'Description', 'Vendor', 'Amount']);
  assert.strictEqual(m.vendor, 2, 'Vendor column should win over Description');
  assert.strictEqual(m._vendorFromDescription, undefined);
});

t('falls back to description as vendor when nothing better exists', () => {
  const m = mapHeaders(['Date', 'Description', 'Amount']);
  assert.strictEqual(m.vendor, 1);
  assert.strictEqual(m._vendorFromDescription, true);
});

t('description-as-vendor is not also used as the memo', () => {
  const m = mapHeaders(['Date', 'Description', 'Amount']);
  assert.strictEqual(m.memo, undefined);
});

t('detects a debit/credit pair as the amount source', () => {
  const m = mapHeaders(['Date', 'Payee', 'Debit', 'Credit']);
  assert.strictEqual(m._amountMode, 'debit_credit');
});

console.log('\n=== dates ===');

t('parses ISO dates', () => {
  assert.deepStrictEqual(parseDate('2026-03-09', 'us'), { y: 2026, m: 3, d: 9 });
});

t('parses US order by default', () => {
  assert.deepStrictEqual(parseDate('03/09/2026', 'us'), { y: 2026, m: 3, d: 9 });
});

t('parses UK order when detected', () => {
  assert.deepStrictEqual(parseDate('09/03/2026', 'uk'), { y: 2026, m: 3, d: 9 });
});

t('auto-detects UK order from a day>12 in the first field', () => {
  assert.strictEqual(detectDateOrder(['13/01/2026', '02/02/2026']), 'uk');
});

t('defaults to US order when ambiguous', () => {
  assert.strictEqual(detectDateOrder(['01/02/2026', '03/04/2026']), 'us');
});

t('rejects an impossible calendar date', () => {
  assert.strictEqual(parseDate('2026-02-30', 'us'), null);
});

t('accepts Feb 29 in a leap year and rejects it otherwise', () => {
  assert.ok(parseDate('2024-02-29', 'us'));
  assert.strictEqual(parseDate('2026-02-29', 'us'), null);
});

t('expands a 2-digit year', () => {
  assert.deepStrictEqual(parseDate('01/02/26', 'us'), { y: 2026, m: 1, d: 2 });
});

console.log('\n=== amounts ===');

t('strips currency symbols', () => {
  assert.strictEqual(parseAmount('$1,234.56'), 1234.56);
  assert.strictEqual(parseAmount('£99.00'), 99);
});

t('reads parenthesised negatives', () => {
  assert.strictEqual(parseAmount('(45.00)'), -45);
});

t('reads trailing-minus negatives', () => {
  assert.strictEqual(parseAmount('45.00-'), -45);
});

t('reads EU decimal commas', () => {
  assert.strictEqual(parseAmount('1.234,56'), 1234.56);
  assert.strictEqual(parseAmount('99,50'), 99.5);
});

t('returns null for unreadable amounts', () => {
  assert.strictEqual(parseAmount('n/a'), null);
  assert.strictEqual(parseAmount(''), null);
});

console.log('\n=== vendor grouping ===');

t('strips corporate suffixes', () => {
  assert.strictEqual(vendorKey('Acme LLC'), vendorKey('Acme Inc'));
  assert.strictEqual(vendorKey('Acme Ltd'), 'ACME');
});

t('strips a leading "The"', () => {
  assert.strictEqual(vendorKey('The Northwind Company'), 'NORTHWIND');
});

t('strips card-processor prefixes', () => {
  assert.strictEqual(vendorKey('SQ *CORNER CAFE'), 'CORNER CAFE');
  assert.strictEqual(vendorKey('PAYPAL *VELLUM'), 'VELLUM');
});

t('strips a trailing store number', () => {
  assert.strictEqual(vendorKey('STARBUCKS 00412'), 'STARBUCKS');
});

t('normalises ampersands', () => {
  assert.strictEqual(vendorKey('Vellum & Co'), vendorKey('Vellum and Company'));
});

t('a bare suffix does not collapse to an empty key', () => {
  assert.strictEqual(vendorKey('LLC'), 'LLC');
});

console.log('\n=== ingest ===');

t('ingests the shipped sample', () => {
  const r = ingestCsv(SAMPLE);
  assert.ok(r.payments.length > 15, 'expected many payments, got ' + r.payments.length);
  assert.strictEqual(r.hasCategory, true);
});

t('flags the unreadable-date row with its line number and reason', () => {
  const r = ingestCsv(SAMPLE);
  const bad = r.skipped.find((s) => s.reason === 'unreadable_date');
  assert.ok(bad, 'expected an unreadable_date flag');
  assert.strictEqual(typeof bad.line, 'number');
  assert.strictEqual(bad.value, 'not a date');
});

t('flags the missing-amount row', () => {
  const r = ingestCsv(SAMPLE);
  assert.ok(r.skipped.some((s) => s.reason === 'unreadable_amount'));
});

t('no row is both accepted and skipped', () => {
  const r = ingestCsv(SAMPLE);
  const accepted = new Set(r.payments.map((p) => p.line));
  for (const s of r.skipped) assert.ok(!accepted.has(s.line), 'line ' + s.line + ' double-counted');
});

t('accepted + skipped never exceeds the data-row count', () => {
  const r = ingestCsv(SAMPLE);
  assert.ok(r.payments.length + r.skipped.length <= r.totalDataRows);
});

t('records the negative amount as a refund, not a payment', () => {
  const r = ingestCsv(SAMPLE);
  assert.strictEqual(r.refundCount, 1);
  assert.strictEqual(r.refundTotal, 45);
  const refund = r.payments.find((p) => p.isRefund);
  assert.ok(refund.amount < 0);
});

t('sorts payments by date', () => {
  const r = ingestCsv(SAMPLE);
  for (let i = 1; i < r.payments.length; i++) {
    assert.ok(r.payments[i].day >= r.payments[i - 1].day);
  }
});

t('reads a debit/credit pair', () => {
  const csv = ['date,payee,debit,credit', '2026-01-05,Acme,120.00,', '2026-01-09,Acme,,20.00'].join('\n');
  const r = ingestCsv(csv);
  assert.strictEqual(r.amountMode, 'debit_credit');
  assert.strictEqual(r.payments[0].amount, 120);
  assert.strictEqual(r.payments[1].amount, -20);
  assert.strictEqual(r.refundCount, 1);
});

t('throws MISSING_COLUMNS naming what it could not find', () => {
  assert.throws(() => ingestCsv('foo,bar\n1,2'), (e) => {
    assert.strictEqual(e.code, 'MISSING_COLUMNS');
    assert.ok(e.missing.includes('date'));
    assert.ok(e.missing.includes('amount'));
    return true;
  });
});

t('throws EMPTY_FILE on blank input', () => {
  assert.throws(() => ingestCsv('   '), (e) => e.code === 'EMPTY_FILE');
});

t('throws NO_ROWS on a header-only file', () => {
  assert.throws(() => ingestCsv('date,vendor,amount'), (e) => e.code === 'NO_ROWS');
});

t('throws NO_VALID_ROWS when nothing parses, carrying the skip list', () => {
  assert.throws(() => ingestCsv('date,vendor,amount\nnope,,x'), (e) => {
    assert.strictEqual(e.code, 'NO_VALID_ROWS');
    assert.ok(e.skipped.length >= 1);
    return true;
  });
});

t('flags a zero-amount row rather than counting it', () => {
  const r = ingestCsv('date,vendor,amount\n2026-01-01,Acme,0\n2026-01-02,Acme,10');
  assert.strictEqual(r.payments.length, 1);
  assert.ok(r.skipped.some((s) => s.reason === 'zero_amount'));
});

t('flags an implausible amount', () => {
  const r = ingestCsv('date,vendor,amount\n2026-01-01,Acme,999999999999\n2026-01-02,Acme,10');
  assert.ok(r.skipped.some((s) => s.reason === 'implausible_amount'));
});

console.log('\n=== spend analysis ===');

const MINI_ANALYSIS = (() => {
  const r = ingestCsv(MINI);
  return analyzeSpend(r.payments, { hasCategory: r.hasCategory, amountMode: r.amountMode, currencies: r.currencies });
})();

t('median works on odd and even lengths', () => {
  assert.strictEqual(median([1, 2, 3]), 2);
  assert.strictEqual(median([1, 2, 3, 4]), 2.5);
});

t('shareOf guards against a zero denominator', () => {
  assert.strictEqual(shareOf(5, 0), 0);
});

t('groups the two Acme rows into one bucket', () => {
  const acme = MINI_ANALYSIS.vendors.find((v) => v.vendorKey === 'ACME');
  assert.strictEqual(acme.paymentCount, 3);
  assert.strictEqual(acme.net, 350);
});

t('ranks vendors by net spend descending', () => {
  for (let i = 1; i < MINI_ANALYSIS.vendors.length; i++) {
    assert.ok(MINI_ANALYSIS.vendors[i - 1].net >= MINI_ANALYSIS.vendors[i].net);
  }
  assert.strictEqual(MINI_ANALYSIS.vendors[0].rank, 1);
});

t('vendor shares sum to about 100%', () => {
  const sum = MINI_ANALYSIS.vendors.reduce((s, v) => s + v.netSharePct, 0);
  assert.ok(Math.abs(sum - 100) < 0.5, 'shares summed to ' + sum);
});

t('gross minus refunds equals net', () => {
  const a = analyze(SAMPLE).analysis;
  assert.strictEqual(a.totals.net, Math.round((a.totals.grossPaid - a.totals.refundTotal) * 100) / 100);
});

t('per-vendor net sums to the total net', () => {
  const a = analyze(SAMPLE).analysis;
  const sum = Math.round(a.vendors.reduce((s, v) => s + v.net, 0) * 100) / 100;
  assert.strictEqual(sum, a.totals.net);
});

t('monthly net sums to the total net', () => {
  const a = analyze(SAMPLE).analysis;
  const sum = Math.round(a.monthly.reduce((s, m) => s + m.net, 0) * 100) / 100;
  assert.strictEqual(sum, a.totals.net);
});

t('category net sums to the total net', () => {
  const a = analyze(SAMPLE).analysis;
  const sum = Math.round(a.categories.reduce((s, c) => s + c.net, 0) * 100) / 100;
  assert.strictEqual(sum, a.totals.net);
});

t('min <= median <= max payment per vendor', () => {
  const a = analyze(SAMPLE).analysis;
  for (const v of a.vendors) {
    if (!v.paymentCount) continue;
    assert.ok(v.minPayment <= v.medianPayment, v.label + ' min>median');
    assert.ok(v.medianPayment <= v.maxPayment, v.label + ' median>max');
  }
});

t('cadence needs at least three payments', () => {
  const a = MINI_ANALYSIS;
  const acme = a.vendors.find((v) => v.vendorKey === 'ACME');
  const beta = a.vendors.find((v) => v.vendorKey === 'BETA');
  assert.strictEqual(acme.cadenceKnown, true);
  assert.ok(acme.medianGapDays > 25 && acme.medianGapDays < 35, 'monthly gap expected, got ' + acme.medianGapDays);
  assert.strictEqual(beta.cadenceKnown, false);
  assert.strictEqual(beta.medianGapDays, null);
});

t('drift is the arithmetic first-to-last difference', () => {
  const acme = MINI_ANALYSIS.vendors.find((v) => v.vendorKey === 'ACME');
  assert.strictEqual(acme.driftAmount, 50);
  assert.strictEqual(acme.driftPct, 50);
});

t('a single-payment vendor has no drift', () => {
  const beta = MINI_ANALYSIS.vendors.find((v) => v.vendorKey === 'BETA');
  assert.strictEqual(beta.driftAmount, null);
  assert.strictEqual(beta.driftPct, null);
});

t('HHI sits on the 0-10,000 scale', () => {
  const c = analyze(SAMPLE).analysis.concentration;
  assert.ok(c.hhi > 0 && c.hhi <= 10000, 'hhi=' + c.hhi);
  assert.ok(c.hhiScale.includes('0-10,000'));
});

t('a single-vendor file gives HHI 10000 and effective count 1', () => {
  const a = analyze('date,vendor,amount\n2026-01-01,Solo,100\n2026-02-01,Solo,100').analysis;
  assert.strictEqual(a.concentration.hhi, 10000);
  assert.strictEqual(a.concentration.effectiveVendorCount, 1);
  assert.strictEqual(a.concentration.top1.sharePct, 100);
});

t('top-N shares are monotonically non-decreasing', () => {
  const c = analyze(SAMPLE).analysis.concentration;
  assert.ok(c.top1.sharePct <= c.top3.sharePct);
  assert.ok(c.top3.sharePct <= c.top5.sharePct);
  assert.ok(c.top5.sharePct <= c.top10.sharePct);
});

t('vendors-for-50% is never more than vendors-for-80%', () => {
  const c = analyze(SAMPLE).analysis.concentration;
  assert.ok(c.vendorsForHalfOfSpend <= c.vendorsForEightyPctOfSpend);
});

t('dormancy is measured against the vendor\'s own median gap', () => {
  // Acme is paid monthly, then the file continues for six more months via Beta.
  const csv = [
    'date,vendor,amount',
    '2026-01-10,Acme,100', '2026-02-10,Acme,100', '2026-03-10,Acme,100',
    '2026-04-01,Beta,10', '2026-09-01,Beta,10',
  ].join('\n');
  const a = analyze(csv).analysis;
  const acme = a.vendors.find((v) => v.vendorKey === 'ACME');
  assert.strictEqual(acme.quietVsOwnRhythm, true, 'acme should read as quiet vs its own monthly rhythm');
});

t('a vendor without a measurable cadence is never marked quiet', () => {
  const beta = MINI_ANALYSIS.vendors.find((v) => v.vendorKey === 'BETA');
  assert.strictEqual(beta.quietVsOwnRhythm, false);
  assert.strictEqual(beta.dormancyRatio, null);
});

t('monthly rows are date-sorted and cover every observed month', () => {
  const a = analyze(SAMPLE).analysis;
  const keys = a.monthly.map((m) => m.month);
  assert.deepStrictEqual(keys, keys.slice().sort());
  assert.strictEqual(a.monthly.length, a.window.monthsObserved);
});

t('merged spellings are disclosed on the vendor bucket', () => {
  const a = analyze(SAMPLE).analysis;
  const merged = a.vendors.filter((v) => v.spellingCount > 1);
  assert.ok(merged.length >= 1, 'sample should merge at least one vendor spelling');
  assert.ok(merged[0].spellings.length > 1);
});

t('analysis is deterministic across runs', () => {
  const a = JSON.stringify(analyze(SAMPLE).analysis);
  const b = JSON.stringify(analyze(SAMPLE).analysis);
  assert.strictEqual(a, b);
});

console.log('\n=== summary ===');

t('money and pct format as expected', () => {
  assert.strictEqual(money(1234.5), '$1,234.50');
  assert.strictEqual(money(-45), '-$45.00');
  assert.strictEqual(pct(38.66), '38.7%');
});

t('summary counts match the analysis', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(r.summary.counts.vendors, r.analysis.concentration.vendorCount);
  assert.strictEqual(r.summary.spend.net, r.analysis.totals.net);
});

t('summary always carries the disclaimer and notes', () => {
  const r = analyze(SAMPLE);
  assert.ok(r.summary.disclaimer.includes('organizational tooling only'));
  assert.ok(r.summary.notes.length >= 5);
});

t('lint-safe notes exist and are the same length as display notes', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(r.summary.lintNotes.length, r.summary.notes.length);
});

t('refunds are explicitly disclosed in the notes', () => {
  const r = analyze(SAMPLE);
  assert.ok(r.summary.notes.some((n) => n.includes('negative amount')));
});

t('a file with no category column says so instead of inventing one', () => {
  const r = analyze(MINI);
  assert.strictEqual(r.analysis.categories.length, 0);
  assert.ok(r.summary.notes.some((n) => n.includes('no category column')));
});

t('mixed currencies produce an explicit no-conversion warning', () => {
  const csv = [
    'date,vendor,amount,currency',
    '2026-01-01,Acme,100,USD',
    '2026-01-02,Beta,100,EUR',
  ].join('\n');
  const r = analyze(csv);
  assert.ok(r.summary.notes.some((n) => n.includes('does NOT convert currencies')));
});

t('a clean file says nothing was left out', () => {
  const r = analyze(MINI);
  assert.ok(r.summary.notes.some((n) => n.includes('read successfully')));
});

console.log('\n=== advice linter (HARD GUARDRAIL) ===');

t('the real summary passes the linter', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(assertNoAdvice(summaryStrings(r.summary)), true);
});

t('every banned phrase is actually caught', () => {
  for (const phrase of BANNED_PHRASES) {
    const v = lintStrings(['Some sentence that says ' + phrase + ' right here.']);
    assert.ok(v.length > 0, 'linter missed: ' + phrase);
  }
});

t('assertNoAdvice throws with a machine-readable code', () => {
  assert.throws(() => assertNoAdvice(['we recommend you cancel this vendor']), (e) => {
    assert.strictEqual(e.code, 'ADVICE_LINTER_FAILED');
    assert.ok(e.violations.length > 0);
    return true;
  });
});

t('the disclaimer does not trip its own linter', () => {
  const { DISCLAIMER } = require('../engine/constants');
  assert.strictEqual(assertNoAdvice([DISCLAIMER]), true);
});

t('buyer data cannot trip the linter via a vendor name', () => {
  // A real vendor literally named with a banned phrase must not withhold the report.
  const csv = [
    'date,vendor,amount',
    '2026-01-01,Cut Costs Consulting LLC,5000',
    '2026-02-01,Cut Costs Consulting LLC,5000',
    '2026-03-01,Market Rate Advisors,100',
  ].join('\n');
  const r = analyze(csv);
  assert.ok(r.summary.notes.some((n) => n.includes('Cut Costs Consulting')), 'vendor name should appear in the display notes');
  assert.strictEqual(assertNoAdvice(summaryStrings(r.summary)), true);
});

t('the linter runs before any artifact bytes are produced', () => {
  // Poison the summary path and confirm buildReport refuses rather than rendering.
  const summaryMod = require('../engine/summary');
  const original = summaryMod.buildSummary;
  summaryMod.buildSummary = function (a, o) {
    const s = original(a, o);
    s.lintNotes = s.lintNotes.concat(['we recommend you cancel this vendor']);
    return s;
  };
  try {
    delete require.cache[require.resolve('../engine/index.js')];
    const fresh = require('../engine/index.js');
    assert.throws(() => fresh.buildReport(MINI), (e) => e.code === 'ADVICE_LINTER_FAILED');
  } finally {
    summaryMod.buildSummary = original;
    delete require.cache[require.resolve('../engine/index.js')];
    require('../engine/index.js');
  }
});

console.log('\n=== validation gate ===');

t('rejects a non-string input', () => {
  assert.throws(() => validateCsvInput(42), (e) => e.code === 'BAD_INPUT_TYPE');
});

t('rejects an empty file', () => {
  assert.throws(() => validateCsvInput('  '), (e) => e.code === 'EMPTY_FILE');
});

t('rejects an oversized file', () => {
  assert.throws(() => validateCsvInput('x'.repeat(9 * 1024 * 1024)), (e) => e.code === 'FILE_TOO_LARGE');
});

t('rejects a file with too many rows', () => {
  assert.throws(() => validateCsvInput('a\n'.repeat(50001)), (e) => e.code === 'TOO_MANY_ROWS');
});

console.log('\n=== artifacts ===');

t('renderXlsx produces a real ZIP container', () => {
  const buf = renderXlsx(analyze(SAMPLE));
  assert.ok(Buffer.isBuffer(buf));
  assert.strictEqual(buf.slice(0, 2).toString('latin1'), 'PK');
  assert.ok(buf.length > 3000, 'xlsx suspiciously small: ' + buf.length);
});

// Minimal ZIP reader so the tests inspect the DECOMPRESSED parts rather than
// searching raw (deflated) bytes, which would pass vacuously.
function unzip(buf) {
  const zlib = require('zlib');
  const out = {};
  let i = 0;
  while (i + 30 <= buf.length && buf.readUInt32LE(i) === 0x04034b50) {
    const method = buf.readUInt16LE(i + 8);
    const csize = buf.readUInt32LE(i + 18);
    const nameLen = buf.readUInt16LE(i + 26);
    const extraLen = buf.readUInt16LE(i + 28);
    const name = buf.slice(i + 30, i + 30 + nameLen).toString('utf8');
    const start = i + 30 + nameLen + extraLen;
    const body = buf.slice(start, start + csize);
    out[name] = method === 8 ? zlib.inflateRawSync(body) : body;
    i = start + csize;
  }
  return out;
}

t('the workbook unzips into the expected parts', () => {
  const parts = unzip(renderXlsx(analyze(SAMPLE)));
  for (const p of ['[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/styles.xml', 'xl/worksheets/sheet1.xml']) {
    assert.ok(parts[p], 'missing package part: ' + p);
  }
});

t('the workbook declares all six sheets (decompressed)', () => {
  const wb = unzip(renderXlsx(analyze(SAMPLE)))['xl/workbook.xml'].toString('utf8');
  for (const name of ['Summary', 'Vendors', 'Monthly', 'Categories', 'All Payments', 'Flagged Rows']) {
    assert.ok(wb.includes(`name="${name}"`), 'missing sheet name: ' + name);
  }
});

t('every declared sheet has a matching worksheet part', () => {
  const parts = unzip(renderXlsx(analyze(SAMPLE)));
  for (let n = 1; n <= 6; n++) {
    assert.ok(parts[`xl/worksheets/sheet${n}.xml`], 'missing worksheet ' + n);
  }
});

t('the Vendors sheet carries a real vendor label', () => {
  const r = analyze(SAMPLE);
  const parts = unzip(renderXlsx(r));
  const sheet = parts['xl/worksheets/sheet2.xml'].toString('utf8');
  assert.ok(sheet.includes(r.analysis.vendors[0].label), 'top vendor label missing from the Vendors sheet');
});

t('renderPdf produces a real PDF with an EOF marker', () => {
  const buf = renderPdf(analyze(SAMPLE));
  assert.ok(Buffer.isBuffer(buf));
  assert.strictEqual(buf.slice(0, 5).toString('latin1'), '%PDF-');
  assert.ok(buf.slice(-6).toString('latin1').includes('%%EOF'));
});

t('the PDF carries the disclaimer text', () => {
  const raw = renderPdf(analyze(SAMPLE)).toString('latin1');
  assert.ok(raw.includes('organizational tooling only'));
});

t('artifacts are byte-deterministic', () => {
  const a = buildReport(SAMPLE);
  const b = buildReport(SAMPLE);
  assert.ok(a.xlsx.equals(b.xlsx), 'xlsx not deterministic');
  assert.ok(a.pdf.equals(b.pdf), 'pdf not deterministic');
});

t('buildReport returns report + both artifacts', () => {
  const { report, xlsx, pdf } = buildReport(SAMPLE);
  assert.ok(report.summary && report.analysis);
  assert.ok(xlsx.length > 0 && pdf.length > 0);
  assert.strictEqual(report.product, 'hff-vendor-spend');
});

t('the engine survives a one-row file', () => {
  const { report, xlsx, pdf } = buildReport('date,vendor,amount\n2026-01-01,Solo,10');
  assert.strictEqual(report.summary.counts.payments, 1);
  assert.ok(xlsx.length > 0 && pdf.length > 0);
});

t('XML-hostile vendor names are escaped, not injected', () => {
  const csv = 'date,vendor,amount\n2026-01-01,"A & B <tag> ""quoted""",100';
  const parts = unzip(renderXlsx(analyze(csv)));
  const sheet = parts['xl/worksheets/sheet2.xml'].toString('utf8');
  assert.ok(!sheet.includes('<tag>'), 'raw tag leaked into the sheet XML');
  assert.ok(sheet.includes('&lt;tag&gt;'), 'expected the escaped form');
  assert.ok(sheet.includes('&amp;'), 'ampersand should be escaped');
});

console.log('\n' + '='.repeat(52));
console.log(`engine tests: ${passed} passed, ${failed} failed`);
console.log('='.repeat(52) + '\n');
process.exit(failed === 0 ? 0 : 1);
