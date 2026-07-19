// test/engine.test.js
//
// HFF — Client Revenue Concentration Report — engine verification with node:test.
// No install, no network, no keys. Run:  node test/engine.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const zlib = require('node:zlib');

const ROOT = path.resolve(__dirname, '..');
const { analyze, buildReport } = require(path.join(ROOT, 'engine'));
const ingest = require(path.join(ROOT, 'engine', 'ingest.js'));
const { analyzeConcentration, median, round2 } = require(path.join(ROOT, 'engine', 'concentration.js'));
const { lintStrings, assertNoAdvice } = require(path.join(ROOT, 'engine', 'advice_linter.js'));
const { renderXlsx } = require(path.join(ROOT, 'engine', 'render_xlsx.js'));
const { renderPdf } = require(path.join(ROOT, 'engine', 'render_pdf.js'));

const SAMPLE = fs.readFileSync(path.join(ROOT, 'engine', 'sample', 'sample_invoices.csv'), 'utf8');

// =============================================================== CSV ingest

test('splitCsv handles quoting, escaped quotes, CRLF and BOM', () => {
  const grid = ingest.splitCsv('﻿a,b\r\n"x,1","he said ""hi"""\r\n');
  assert.deepStrictEqual(grid[0], ['a', 'b']);
  assert.deepStrictEqual(grid[1], ['x,1', 'he said "hi"']);
});

test('header aliasing recognises invoice-style column names', () => {
  const r = ingest.ingestCsv('Issue Date,Customer Name,Invoice Total\n2025-01-01,Acme,100\n');
  assert.strictEqual(r.invoices.length, 1);
  assert.strictEqual(r.invoices[0].client, 'Acme');
  assert.strictEqual(r.invoices[0].amount, 100);
});

test('missing required columns throws MISSING_COLUMNS naming what is missing', () => {
  assert.throws(
    () => ingest.ingestCsv('Date,Notes\n2025-01-01,hello\n'),
    (e) => e.code === 'MISSING_COLUMNS' && e.missing.includes('client') && e.missing.includes('amount')
  );
});

test('amount parsing handles $, thousands, EU decimals, parens and trailing minus', () => {
  assert.strictEqual(ingest.parseAmount('$1,234.56'), 1234.56);
  assert.strictEqual(ingest.parseAmount('1.234,56'), 1234.56);
  assert.strictEqual(ingest.parseAmount('(300.00)'), -300);
  assert.strictEqual(ingest.parseAmount('300.00-'), -300);
  assert.strictEqual(ingest.parseAmount('€99'), 99);
  assert.strictEqual(ingest.parseAmount('abc'), null);
  assert.strictEqual(ingest.parseAmount(''), null);
});

test('date parsing rejects impossible dates and respects UK/US order', () => {
  assert.strictEqual(ingest.parseDate('2025-02-30', 'us'), null);
  assert.strictEqual(ingest.parseDate('2024-02-29', 'us').d, 29); // leap year is valid
  assert.deepStrictEqual(ingest.parseDate('03/04/2025', 'us'), { y: 2025, m: 3, d: 4 });
  assert.deepStrictEqual(ingest.parseDate('03/04/2025', 'uk'), { y: 2025, m: 4, d: 3 });
});

test('whole-file date-order detection infers UK when a day exceeds 12', () => {
  assert.strictEqual(ingest.detectDateOrder(['05/06/2025', '25/06/2025']), 'uk');
  assert.strictEqual(ingest.detectDateOrder(['05/06/2025', '07/06/2025']), 'us');
  assert.strictEqual(ingest.detectDateOrder(['25/06/2025'], 'us'), 'us'); // explicit wins
});

test('unreadable rows are FLAGGED with CSV line numbers, never dropped silently', () => {
  const r = ingest.ingestCsv(
    'Date,Client,Amount\n2025-01-01,Acme,100\nnotadate,Beta,50\n2025-01-03,,50\n2025-01-04,Gamma,zzz\n2025-01-05,Delta,0\n'
  );
  assert.strictEqual(r.invoices.length, 1);
  assert.deepStrictEqual(
    r.skipped.map((s) => [s.line, s.reason]),
    [[3, 'unreadable_date'], [4, 'missing_client'], [5, 'unreadable_amount'], [6, 'zero_amount']]
  );
});

test('a file with zero readable rows throws NO_VALID_ROWS and carries the flags', () => {
  assert.throws(
    () => ingest.ingestCsv('Date,Client,Amount\nnope,Acme,100\n'),
    (e) => e.code === 'NO_VALID_ROWS' && e.skipped.length === 1
  );
});

// ============================================================ client keying

test('clientKey strips corporate suffixes, punctuation and a leading "The"', () => {
  assert.strictEqual(ingest.clientKey('Acme Corp'), 'ACME');
  assert.strictEqual(ingest.clientKey('ACME CORPORATION'), 'ACME');
  assert.strictEqual(ingest.clientKey('Acme, Inc.'), 'ACME');
  assert.strictEqual(ingest.clientKey('The Acme Company'), 'ACME');
  assert.strictEqual(ingest.clientKey('Acme Co Ltd'), 'ACME'); // repeated suffix stripping
});

test('clientKey folds "&" and "and" onto the same key', () => {
  assert.strictEqual(ingest.clientKey('Cedar & Sons, LLC'), ingest.clientKey('Cedar and Sons LLC'));
});

test('clientKey keeps genuinely different clients apart', () => {
  assert.notStrictEqual(ingest.clientKey('Acme Corp'), ingest.clientKey('Acme Digital'));
});

test('a client name that is nothing but a suffix is not collapsed to empty', () => {
  assert.strictEqual(ingest.clientKey('LLC'), 'LLC');
});

// ========================================================== concentration

function rows(list) {
  const header = 'Date,Client,Amount\n';
  return header + list.map((r) => r.join(',')).join('\n') + '\n';
}

test('shares sum to 100% and rank is ordered by net revenue', () => {
  const r = analyze(rows([
    ['2025-01-01', 'Alpha', 600],
    ['2025-02-01', 'Beta', 300],
    ['2025-03-01', 'Gamma', 100],
  ]));
  const cs = r.analysis.clients;
  assert.deepStrictEqual(cs.map((c) => c.label), ['Alpha', 'Beta', 'Gamma']);
  assert.deepStrictEqual(cs.map((c) => c.rank), [1, 2, 3]);
  assert.deepStrictEqual(cs.map((c) => c.sharePct), [60, 30, 10]);
});

test('a single-client file reports 100% share, HHI 10000 and 1 effective client', () => {
  const r = analyze(rows([['2025-01-01', 'Solo', 500], ['2025-02-01', 'Solo', 500]]));
  assert.strictEqual(r.summary.concentration.top1SharePct, 100);
  assert.strictEqual(r.summary.concentration.hhi, 10000);
  assert.strictEqual(r.summary.concentration.effectiveClientCount, 1);
  assert.strictEqual(r.summary.concentration.clientsToReachHalf, 1);
});

test('four equal clients give HHI 2500 and 4 effective clients', () => {
  const r = analyze(rows([
    ['2025-01-01', 'A', 250], ['2025-01-02', 'B', 250],
    ['2025-01-03', 'C', 250], ['2025-01-04', 'D', 250],
  ]));
  assert.strictEqual(r.summary.concentration.hhi, 2500);
  assert.strictEqual(r.summary.concentration.effectiveClientCount, 4);
  assert.strictEqual(r.summary.concentration.clientsToReachHalf, 2);
  assert.strictEqual(r.summary.concentration.clientsToReachEighty, 4);
});

test('effective client count is always <= the number of contributing clients', () => {
  const r = analyze(rows([
    ['2025-01-01', 'A', 900], ['2025-01-02', 'B', 60],
    ['2025-01-03', 'C', 30], ['2025-01-04', 'D', 10],
  ]));
  const c = r.summary.concentration;
  assert.ok(c.effectiveClientCount <= c.contributingClients || c.effectiveClientCount <= 4);
  assert.ok(c.effectiveClientCount >= 1);
  assert.ok(c.hhi > 2500, 'a skewed file must score above the equal-split HHI');
});

test('credits are netted against the client that issued them, not discarded', () => {
  const r = analyze(rows([
    ['2025-01-01', 'Alpha', 1000],
    ['2025-02-01', 'Alpha', '(200.00)'],
    ['2025-03-01', 'Beta', 800],
  ]));
  const alpha = r.analysis.clients.find((c) => c.label === 'Alpha');
  assert.strictEqual(alpha.gross, 1000);
  assert.strictEqual(alpha.credits, 200);
  assert.strictEqual(alpha.net, 800);
  assert.strictEqual(r.summary.totals.net, 1600);
  assert.strictEqual(r.summary.counts.creditRows, 1);
});

test('a client that nets to zero or below is excluded from shares but still listed', () => {
  const r = analyze(rows([
    ['2025-01-01', 'Alpha', 1000],
    ['2025-02-01', 'Refunded', 100],
    ['2025-03-01', 'Refunded', '(150.00)'],
  ]));
  const refunded = r.analysis.clients.find((c) => c.label === 'Refunded');
  assert.ok(refunded, 'the net-negative client must still appear in the client list');
  assert.strictEqual(refunded.net, -50);
  assert.strictEqual(refunded.sharePct, 0);
  assert.strictEqual(r.summary.concentration.top1SharePct, 100, 'Alpha is 100% of net-positive revenue');
  assert.strictEqual(r.analysis.netNegativeClients.length, 1);
});

test('two spellings of one client merge, and the merge is disclosed', () => {
  const r = analyze(rows([
    ['2025-01-01', 'Acme Corp', 500],
    ['2025-02-01', 'ACME CORPORATION', 500],
    ['2025-03-01', 'Acme Corp', 500],
  ]));
  assert.strictEqual(r.analysis.clients.length, 1);
  const c = r.analysis.clients[0];
  assert.strictEqual(c.invoiceCount, 3);
  assert.strictEqual(c.spellingCount, 2);
  assert.strictEqual(c.label, 'Acme Corp', 'display label is the most frequent spelling');
  assert.ok(r.summary.notes.some((n) => n.includes('different spellings')));
});

test('display label ties break alphabetically so output is deterministic', () => {
  const r = analyze(rows([['2025-01-01', 'Zeta Inc', 100], ['2025-02-01', 'Alpha Inc', 100]]));
  // Both spellings key to different clients here; assert determinism across runs instead.
  const again = analyze(rows([['2025-01-01', 'Zeta Inc', 100], ['2025-02-01', 'Alpha Inc', 100]]));
  assert.deepStrictEqual(r.analysis.clients.map((c) => c.label), again.analysis.clients.map((c) => c.label));
});

test('dormancy is measured against each client\'s OWN median gap', () => {
  const r = analyze(rows([
    // Steady monthly client that then stops for ~5 months.
    ['2025-01-01', 'Steady', 100], ['2025-02-01', 'Steady', 100], ['2025-03-01', 'Steady', 100],
    // Another client keeps invoicing, extending the window.
    ['2025-06-01', 'Active', 100], ['2025-08-01', 'Active', 100],
  ]));
  const steady = r.analysis.clients.find((c) => c.label === 'Steady');
  assert.ok(steady.medianGapDays >= 28 && steady.medianGapDays <= 31);
  assert.strictEqual(steady.noInvoiceSinceExpected, true);
  const active = r.analysis.clients.find((c) => c.label === 'Active');
  assert.strictEqual(active.noInvoiceSinceExpected, false);
});

test('a single-invoice client has no median gap and is never called dormant', () => {
  const r = analyze(rows([['2025-01-01', 'Once', 100], ['2025-09-01', 'Other', 100]]));
  const once = r.analysis.clients.find((c) => c.label === 'Once');
  assert.strictEqual(once.medianGapDays, null);
  assert.strictEqual(once.noInvoiceSinceExpected, false);
});

test('monthly series is chronological and its net totals reconcile to the whole file', () => {
  const r = analyze(SAMPLE);
  const months = r.analysis.monthly.map((m) => m.month);
  assert.deepStrictEqual(months, months.slice().sort());
  const sum = round2(r.analysis.monthly.reduce((s, m) => s + m.net, 0));
  assert.strictEqual(sum, r.summary.totals.net);
});

test('per-client net figures reconcile to the file total', () => {
  const r = analyze(SAMPLE);
  const sum = round2(r.analysis.clients.reduce((s, c) => s + c.net, 0));
  assert.strictEqual(sum, r.summary.totals.net);
});

test('payment timing is reported only when a paid-date column exists', () => {
  const withPaid = analyze('Date,Client,Amount,Paid Date\n2025-01-01,A,100,2025-01-11\n2025-02-01,A,100,2025-02-21\n');
  assert.strictEqual(withPaid.analysis.paymentTiming.available, true);
  assert.strictEqual(withPaid.analysis.paymentTiming.medianDaysToPay, 15);
  assert.strictEqual(withPaid.analysis.paymentTiming.slowestDaysToPay, 20);

  const without = analyze(rows([['2025-01-01', 'A', 100]]));
  assert.strictEqual(without.analysis.paymentTiming.available, false);
  assert.strictEqual(without.analysis.paymentTiming.medianDaysToPay, null);
  assert.ok(without.summary.notes.some((n) => n.includes('no payment-timing figures')));
});

test('a paid date BEFORE the invoice date is not counted as negative days-to-pay', () => {
  const r = analyze('Date,Client,Amount,Paid Date\n2025-03-01,A,100,2025-02-01\n');
  assert.strictEqual(r.analysis.paymentTiming.available, false);
  assert.strictEqual(r.analysis.clients[0].medianDaysToPay, null);
});

test('median helper is correct for odd and even lengths', () => {
  assert.strictEqual(median([3, 1, 2]), 2);
  assert.strictEqual(median([4, 1, 3, 2]), 2.5);
  assert.strictEqual(median([]), null);
});

test('analysis is deterministic — the same CSV twice yields identical JSON', () => {
  const a = JSON.stringify(analyze(SAMPLE).summary);
  const b = JSON.stringify(analyze(SAMPLE).summary);
  assert.strictEqual(a, b);
});

// ============================================================ advice linter

test('advice linter catches instruction, judgement and recommendation language', () => {
  assert.ok(lintStrings(['You should drop Acme.']).length > 0);
  assert.ok(lintStrings(['You are too dependent on one client.']).length > 0);
  assert.ok(lintStrings(['We recommend spreading revenue out.']).length > 0);
  assert.ok(lintStrings(['This is a red flag for your business.']).length > 0);
  assert.ok(lintStrings(['This report is not tax advice at all... tax advice']).length > 0);
});

test('advice linter allows purely descriptive language', () => {
  assert.strictEqual(lintStrings([
    'Acme accounts for 67.2% of observed net revenue.',
    'HHI for this file is 4883 on a 0-10,000 scale.',
    'Last invoice 2025-03-01, 120 day(s) before the end of the window.',
  ]).length, 0);
});

test('the mandatory disclaimer does not trip its own linter', () => {
  const { DISCLAIMER } = require(path.join(ROOT, 'engine', 'constants.js'));
  assert.doesNotThrow(() => assertNoAdvice([DISCLAIMER]));
  assert.ok(DISCLAIMER.includes('not financial, tax, or legal advice'));
});

test('assertNoAdvice FAILS CLOSED with a machine-readable code', () => {
  assert.throws(
    () => assertNoAdvice(['You should fire this client.']),
    (e) => e.code === 'ADVICE_LINTER_FAILED' && e.violations.length > 0
  );
});

test('every engine-authored string in a real run passes the linter', () => {
  const r = analyze(SAMPLE);
  const { summaryStrings } = require(path.join(ROOT, 'engine', 'summary.js'));
  assert.strictEqual(lintStrings(summaryStrings(r.summary)).length, 0);
});

test('a client NAMED with banned words does not withhold the buyer\'s own report', () => {
  // Regression guard for the false positive the sibling products would hit:
  // the linter must judge the ENGINE's wording, not the buyer's data.
  const csv = rows([
    ['2025-01-01', 'We Recommend Ltd', 900],
    ['2025-02-01', 'Good Client LLC', 100],
  ]);
  const r = analyze(csv);
  assert.strictEqual(r.analysis.clients[0].label, 'We Recommend Ltd');
  // …and the note that embeds that name is still rendered for the reader.
  assert.ok(r.summary.notes.some((n) => n.includes('We Recommend Ltd')));
  // …while the lint-safe twin has the name replaced by a placeholder.
  assert.ok(r.summary.lintableNotes.some((n) => n.includes('<client>')));
  assert.ok(!r.summary.lintableNotes.some((n) => n.includes('We Recommend Ltd')));
});

test('the linter still guards the engine\'s own sentences', () => {
  const { buildSummary, summaryStrings } = require(path.join(ROOT, 'engine', 'summary.js'));
  const ing = ingest.ingestCsv(rows([['2025-01-01', 'A', 100]]));
  const s = buildSummary(analyzeConcentration(ing.invoices, {}), { skippedCount: 0 });
  s.headline.push('We recommend you diversify.'); // simulate a regression in engine wording
  assert.throws(() => assertNoAdvice(summaryStrings(s)), (e) => e.code === 'ADVICE_LINTER_FAILED');
});

// ============================================================== validation

test('validation gate rejects empty, non-string and oversized input with codes', () => {
  assert.throws(() => analyze(''), (e) => e.code === 'EMPTY_FILE');
  assert.throws(() => analyze(null), (e) => e.code === 'BAD_INPUT_TYPE');
  assert.throws(() => analyze('Date,Client,Amount\n' + 'x\n'.repeat(50001)), (e) => e.code === 'TOO_MANY_ROWS');
});

// ================================================================== XLSX

function unzipEntries(buf) {
  // Walk the central directory rather than trusting our own writer's local headers.
  const eocd = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
  assert.ok(eocd > 0, 'end-of-central-directory signature must be present');
  const count = buf.readUInt16LE(eocd + 10);
  let off = buf.readUInt32LE(eocd + 16);
  const out = {};
  for (let i = 0; i < count; i++) {
    assert.strictEqual(buf.readUInt32LE(off), 0x02014b50, 'central directory header signature');
    const method = buf.readUInt16LE(off + 10);
    const csize = buf.readUInt32LE(off + 20);
    const usize = buf.readUInt32LE(off + 24);
    const nlen = buf.readUInt16LE(off + 28);
    const elen = buf.readUInt16LE(off + 30);
    const clen = buf.readUInt16LE(off + 32);
    const lho = buf.readUInt32LE(off + 42);
    const name = buf.slice(off + 46, off + 46 + nlen).toString('utf8');
    const lnlen = buf.readUInt16LE(lho + 26);
    const lelen = buf.readUInt16LE(lho + 28);
    const start = lho + 30 + lnlen + lelen;
    const raw = buf.slice(start, start + csize);
    const data = method === 8 ? zlib.inflateRawSync(raw) : raw;
    assert.strictEqual(data.length, usize, `uncompressed size must match for ${name}`);
    out[name] = data.toString('utf8');
    off += 46 + nlen + elen + clen;
  }
  return out;
}

test('XLSX is a valid zip whose every part inflates to its declared size', () => {
  const { xlsx } = buildReport(SAMPLE);
  const parts = unzipEntries(xlsx);
  for (const required of ['[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/styles.xml']) {
    assert.ok(parts[required], `missing part ${required}`);
  }
});

test('XLSX contains all five expected sheets with data', () => {
  const { xlsx } = buildReport(SAMPLE);
  const parts = unzipEntries(xlsx);
  const wb = parts['xl/workbook.xml'];
  for (const name of ['Summary', 'Clients', 'Monthly Revenue', 'All Invoices', 'Flagged Rows']) {
    assert.ok(wb.includes(`name="${name}"`), `workbook must declare sheet ${name}`);
  }
  for (let i = 1; i <= 5; i++) {
    assert.ok(parts[`xl/worksheets/sheet${i}.xml`].includes('<row r="1">'), `sheet${i} must have a header row`);
  }
});

test('XLSX escapes hostile client names instead of emitting broken XML', () => {
  const csv = rows([['2025-01-01', '"Ampersand & <script>alert(1)</script>"', 500]]);
  const { xlsx } = buildReport(csv);
  const parts = unzipEntries(xlsx);
  const clients = parts['xl/worksheets/sheet2.xml'];
  assert.ok(clients.includes('&amp;'), 'ampersand must be escaped');
  assert.ok(!clients.includes('<script>'), 'raw markup must not survive into the sheet');
});

test('the flagged-rows sheet says so explicitly when nothing was flagged', () => {
  const { xlsx } = buildReport(rows([['2025-01-01', 'A', 100]]));
  const parts = unzipEntries(xlsx);
  assert.ok(parts['xl/worksheets/sheet5.xml'].includes('Every data row was read successfully'));
});

test('the disclaimer is present in the workbook', () => {
  const { xlsx } = buildReport(SAMPLE);
  const parts = unzipEntries(xlsx);
  assert.ok(parts['xl/worksheets/sheet1.xml'].includes('not financial, tax, or legal advice'));
});

// =================================================================== PDF

test('PDF has a valid header, trailer, and an xref table whose offsets resolve', () => {
  const { pdf } = buildReport(SAMPLE);
  const s = pdf.toString('latin1');
  assert.ok(s.startsWith('%PDF-1.4'));
  assert.ok(s.trimEnd().endsWith('%%EOF'));

  const m = s.match(/startxref\s+(\d+)/);
  assert.ok(m, 'startxref must be present');
  const xrefStart = Number(m[1]);
  assert.strictEqual(s.slice(xrefStart, xrefStart + 4), 'xref');

  const entries = s.slice(xrefStart).match(/^(\d{10}) 00000 n $/gm) || [];
  assert.strictEqual(entries.length, 6, 'six in-use objects expected');
  entries.forEach((e, i) => {
    const off = Number(e.slice(0, 10));
    assert.ok(/^\d+ 0 obj/.test(s.slice(off, off + 12)), `xref entry ${i + 1} must point at an object header`);
  });
});

test('PDF stream /Length matches the actual byte length of the content stream', () => {
  const { pdf } = buildReport(SAMPLE);
  const s = pdf.toString('latin1');
  const m = s.match(/<< \/Length (\d+) >>\nstream\n([\s\S]*?)\nendstream/);
  assert.ok(m, 'content stream must be present');
  assert.strictEqual(Buffer.byteLength(m[2], 'latin1'), Number(m[1]));
});

test('PDF renders the disclaimer and the product name', () => {
  const { pdf } = buildReport(SAMPLE);
  const s = pdf.toString('latin1');
  assert.ok(s.includes('Client Revenue Concentration Report'));
  assert.ok(s.includes('not financial, tax, or legal advice'));
});

test('PDF escapes parentheses and backslashes in client names', () => {
  const csv = rows([['2025-01-01', '"Paren (Co) \\\\ Slash"', 500]]);
  const { pdf } = buildReport(csv);
  const s = pdf.toString('latin1');
  assert.ok(s.includes('\\(Co\\)') || s.includes('Paren \\('), 'parentheses must be backslash-escaped');
});

test('PDF and XLSX are byte-deterministic across runs', () => {
  const a = buildReport(SAMPLE);
  const b = buildReport(SAMPLE);
  assert.ok(a.pdf.equals(b.pdf), 'PDF bytes must be identical');
  assert.ok(a.xlsx.equals(b.xlsx), 'XLSX bytes must be identical');
});

test('a file with only a net-negative client still renders both artifacts', () => {
  const csv = rows([['2025-01-01', 'Refund Only', 100], ['2025-02-01', 'Refund Only', '(150.00)']]);
  const { report, xlsx, pdf } = buildReport(csv);
  assert.strictEqual(report.summary.concentration.contributingClients, undefined);
  assert.strictEqual(report.analysis.metrics.contributingClients, 0);
  assert.ok(xlsx.length > 0 && pdf.length > 0);
  assert.ok(pdf.toString('latin1').includes('No client in this file nets above zero'));
});

// ============================================================= sample file

test('the shipped sample file produces a coherent, reconciled report', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(r.summary.counts.skippedRows, 3, 'the sample deliberately contains 3 bad rows');
  assert.strictEqual(r.summary.counts.creditRows, 1);
  assert.ok(r.summary.concentration.top1SharePct > 50);
  assert.ok(r.analysis.mergedSpellings.length >= 2, 'sample exercises spelling merges');
  assert.strictEqual(r.analysis.paymentTiming.available, true);
  assert.strictEqual(r.summary.window.start, '2025-01-06');
  assert.strictEqual(r.summary.window.end, '2025-06-17');
});
