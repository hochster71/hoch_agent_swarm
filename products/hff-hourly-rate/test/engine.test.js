// test/engine.test.js
//
// HFF — Effective Hourly Rate Report — engine verification with node:test.
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
const { analyzeRates, weekdayIndex, median, round2 } = require(path.join(ROOT, 'engine', 'rates.js'));
const { lintStrings, assertNoAdvice } = require(path.join(ROOT, 'engine', 'advice_linter.js'));

const SAMPLE = fs.readFileSync(path.join(ROOT, 'engine', 'sample', 'sample_timesheet.csv'), 'utf8');

// =============================================================== CSV ingest

test('splitCsv handles quoting, escaped quotes, CRLF and BOM', () => {
  const grid = ingest.splitCsv('﻿a,b\r\n"x,1","he said ""hi"""\r\n');
  assert.deepStrictEqual(grid[0], ['a', 'b']);
  assert.deepStrictEqual(grid[1], ['x,1', 'he said "hi"']);
});

test('header aliasing recognises time-tracking column names', () => {
  const r = ingest.ingestCsv('Start Date,Customer Name,Time Spent\n2025-01-01,Acme,3.5\n');
  assert.strictEqual(r.entries.length, 1);
  assert.strictEqual(r.entries[0].client, 'Acme');
  assert.strictEqual(r.entries[0].hours, 3.5);
});

test('a minutes-unit column satisfies the duration requirement and converts', () => {
  const r = ingest.ingestCsv('Date,Client,Minutes\n2025-01-01,Acme,90\n');
  assert.strictEqual(r.durationUnit, 'minutes');
  assert.strictEqual(r.entries[0].hours, 1.5);
});

test('missing required columns throws MISSING_COLUMNS naming what is missing', () => {
  assert.throws(
    () => ingest.ingestCsv('Date,Notes\n2025-01-01,hello\n'),
    (e) => e.code === 'MISSING_COLUMNS' && e.missing.includes('client') && e.missing.includes('duration')
  );
});

// ============================================================== durations

test('parseDuration reads clock form, h/m words, decimals and EU commas', () => {
  assert.strictEqual(ingest.parseDuration('3:30'), 3.5);
  assert.strictEqual(ingest.parseDuration('3:30:00'), 3.5);
  assert.strictEqual(ingest.parseDuration('0:45'), 0.75);
  assert.strictEqual(ingest.parseDuration('2:07:30'), 2.125);
  assert.strictEqual(ingest.parseDuration('7h 30m'), 7.5);
  assert.strictEqual(ingest.parseDuration('7h30m'), 7.5);
  assert.strictEqual(ingest.parseDuration('7h'), 7);
  assert.strictEqual(ingest.parseDuration('45m'), 0.75);
  assert.strictEqual(ingest.parseDuration('45 min'), 0.75);
  assert.strictEqual(ingest.parseDuration('90 mins'), 1.5);
  assert.strictEqual(ingest.parseDuration('1.5'), 1.5);
  assert.strictEqual(ingest.parseDuration('1,5'), 1.5);
  assert.strictEqual(ingest.parseDuration('90', 'minutes'), 1.5);
  assert.strictEqual(ingest.parseDuration('lots'), null);
  assert.strictEqual(ingest.parseDuration(''), null);
});

test('zero and implausible durations are flagged, 24h exactly is allowed', () => {
  const r = ingest.ingestCsv(
    'Date,Client,Hours\n2025-01-01,A,0\n2025-01-02,A,25\n2025-01-03,A,24\n'
  );
  assert.strictEqual(r.entries.length, 1);
  assert.strictEqual(r.entries[0].hours, 24);
  assert.deepStrictEqual(
    r.skipped.map((s) => [s.line, s.reason]),
    [[2, 'zero_duration'], [3, 'implausible_duration']]
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
    'Date,Client,Hours\n2025-01-01,Acme,2\nnotadate,Beta,3\n2025-01-03,,4\n2025-01-04,Gamma,zzz\n'
  );
  assert.strictEqual(r.entries.length, 1);
  assert.deepStrictEqual(
    r.skipped.map((s) => [s.line, s.reason]),
    [[3, 'unreadable_date'], [4, 'missing_client'], [5, 'unreadable_duration']]
  );
});

test('a file with zero readable rows throws NO_VALID_ROWS and carries the flags', () => {
  assert.throws(
    () => ingest.ingestCsv('Date,Client,Hours\nnope,Acme,2\n'),
    (e) => e.code === 'NO_VALID_ROWS' && e.skipped.length === 1
  );
});

// ============================================================ billable flags

test('parseBillable reads the common spellings and returns null for the rest', () => {
  assert.strictEqual(ingest.parseBillable('yes'), true);
  assert.strictEqual(ingest.parseBillable('Billable'), true);
  assert.strictEqual(ingest.parseBillable('1'), true);
  assert.strictEqual(ingest.parseBillable('no'), false);
  assert.strictEqual(ingest.parseBillable('Non-billable'), false);
  assert.strictEqual(ingest.parseBillable('0'), false);
  assert.strictEqual(ingest.parseBillable('maybe'), null);
  assert.strictEqual(ingest.parseBillable(''), null);
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

// ================================================================== rates

function rows(header, list) {
  return header + '\n' + list.map((r) => r.join(',')).join('\n') + '\n';
}

test('effective rate on covered hours and blended rate are both plain arithmetic', () => {
  const r = analyze(rows('Date,Client,Hours,Amount', [
    ['2025-01-01', 'Alpha', 2, 200],
    ['2025-01-02', 'Alpha', 3, 250],
    ['2025-01-03', 'Beta', 4, ''],
  ]));
  const t = r.analysis.totals;
  assert.strictEqual(t.hours, 9);
  assert.strictEqual(t.revenue, 450);
  assert.strictEqual(t.coveredHours, 5);
  assert.strictEqual(r.analysis.rates.effectiveRateCovered, 90);   // 450 / 5
  assert.strictEqual(r.analysis.rates.blendedRateAllHours, 50);    // 450 / 9
  assert.strictEqual(r.analysis.rates.coveragePctOfHours, 55.56);  // 5/9
  const alpha = r.analysis.clients.find((c) => c.label === 'Alpha');
  assert.strictEqual(alpha.effectiveRateCovered, 90);
  assert.strictEqual(alpha.blendedRateAllHours, 90);
  const beta = r.analysis.clients.find((c) => c.label === 'Beta');
  assert.strictEqual(beta.effectiveRateCovered, null, 'no billing figures -> no rate, never zero');
  assert.strictEqual(beta.revenue, 0);
});

test('when only a rate column exists, figures are derived as rate x hours and disclosed', () => {
  const r = analyze(rows('Date,Client,Hours,Rate', [
    ['2025-01-01', 'Solo', 2, 100],
    ['2025-01-02', 'Solo', '1:30', 100],
  ]));
  const t = r.analysis.totals;
  assert.strictEqual(t.hours, 3.5);
  assert.strictEqual(t.revenue, 350);
  assert.strictEqual(t.derivedFromRateCount, 2);
  assert.strictEqual(r.analysis.rates.effectiveRateCovered, 100);
  assert.ok(r.summary.notes.some((n) => n.includes('rate x hours')));
});

test('an amount column wins over a rate column for the same entry', () => {
  const r = analyze(rows('Date,Client,Hours,Rate,Amount', [
    ['2025-01-01', 'Solo', 2, 100, 300],
  ]));
  assert.strictEqual(r.analysis.totals.revenue, 300);
  assert.strictEqual(r.analysis.totals.derivedFromRateCount, 0);
  assert.strictEqual(r.analysis.rates.effectiveRateCovered, 150);
});

test('a file with no billing figures reports hours only, rates stay null', () => {
  const r = analyze(rows('Date,Client,Hours', [
    ['2025-01-01', 'A', 3],
    ['2025-01-02', 'B', 2],
  ]));
  assert.strictEqual(r.analysis.rates.available, false);
  assert.strictEqual(r.analysis.rates.effectiveRateCovered, null);
  assert.strictEqual(r.analysis.rates.blendedRateAllHours, null);
  assert.ok(r.summary.headline.some((h) => h.includes('no rate figures')));
});

test('negative billed amounts are excluded from revenue, hours still counted, and disclosed', () => {
  const r = analyze(rows('Date,Client,Hours,Amount', [
    ['2025-01-01', 'A', 2, '(50.00)'],
    ['2025-01-02', 'A', 3, 300],
  ]));
  assert.strictEqual(r.analysis.totals.hours, 5, 'the hours of the negative-amount row must count');
  assert.strictEqual(r.analysis.totals.revenue, 300, 'the negative figure must not reduce revenue');
  assert.strictEqual(r.analysis.meta.negativeAmountsIgnored, 1);
  assert.ok(r.summary.notes.some((n) => n.includes('negative billed amount')));
});

test('billable share is computed over hours with a READABLE flag only', () => {
  const r = analyze(rows('Date,Client,Hours,Billable', [
    ['2025-01-01', 'A', 3, 'yes'],
    ['2025-01-02', 'A', 1, 'no'],
    ['2025-01-03', 'A', 2, 'maybe'],
  ]));
  const t = r.analysis.totals;
  assert.strictEqual(t.billableHours, 3);
  assert.strictEqual(t.nonBillableHours, 1);
  assert.strictEqual(t.unknownBillableHours, 2);
  assert.strictEqual(r.analysis.billableShare.billableSharePct, 75); // 3 of 4 known
  assert.ok(r.summary.notes.some((n) => n.includes('could not read')));
});

test('with no billable column the report says so instead of inventing a share', () => {
  const r = analyze(rows('Date,Client,Hours', [['2025-01-01', 'A', 3]]));
  assert.strictEqual(r.analysis.billableShare.available, false);
  assert.ok(r.summary.notes.some((n) => n.includes('No billable column was found')));
});

test('hours share, rank and ordering follow tracked hours', () => {
  const r = analyze(rows('Date,Client,Hours', [
    ['2025-01-01', 'Big', 6],
    ['2025-01-02', 'Mid', 3],
    ['2025-01-03', 'Small', 1],
  ]));
  const cs = r.analysis.clients;
  assert.deepStrictEqual(cs.map((c) => c.label), ['Big', 'Mid', 'Small']);
  assert.deepStrictEqual(cs.map((c) => c.rank), [1, 2, 3]);
  assert.deepStrictEqual(cs.map((c) => c.hoursSharePct), [60, 30, 10]);
});

test('two spellings of one client merge, and the merge is disclosed', () => {
  const r = analyze(rows('Date,Client,Hours', [
    ['2025-01-01', 'Acme Corp', 2],
    ['2025-02-01', 'ACME CORPORATION', 2],
    ['2025-03-01', 'Acme Corp', 2],
  ]));
  assert.strictEqual(r.analysis.clients.length, 1);
  const c = r.analysis.clients[0];
  assert.strictEqual(c.entryCount, 3);
  assert.strictEqual(c.spellingCount, 2);
  assert.strictEqual(c.label, 'Acme Corp', 'display label is the most frequent spelling');
  assert.ok(r.summary.notes.some((n) => n.includes('different spellings')));
});

test('weekday attribution is correct (2025-01-06 was a Monday)', () => {
  const r = analyze(rows('Date,Client,Hours', [['2025-01-06', 'A', 3.5]]));
  const monday = r.analysis.weekdays.find((w) => w.weekday === 'Monday');
  assert.strictEqual(monday.hours, 3.5);
  const others = r.analysis.weekdays.filter((w) => w.weekday !== 'Monday');
  assert.ok(others.every((w) => w.hours === 0));
});

test('weekdayIndex maps epoch day 0 (a Thursday) correctly', () => {
  assert.strictEqual(weekdayIndex(0), 4); // 1970-01-01 -> Thursday, index 4 with 0=Sunday
});

test('monthly series is chronological and reconciles to the file totals', () => {
  const r = analyze(SAMPLE);
  const months = r.analysis.monthly.map((m) => m.month);
  assert.deepStrictEqual(months, months.slice().sort());
  const hourSum = round2(r.analysis.monthly.reduce((s, m) => s + m.hours, 0));
  assert.strictEqual(hourSum, r.analysis.totals.hours);
  const revSum = round2(r.analysis.monthly.reduce((s, m) => s + m.revenue, 0));
  assert.strictEqual(revSum, r.analysis.totals.revenue);
});

test('per-client hours and revenue reconcile to the file totals', () => {
  const r = analyze(SAMPLE);
  const hourSum = round2(r.analysis.clients.reduce((s, c) => s + c.hours, 0));
  assert.strictEqual(hourSum, r.analysis.totals.hours);
  const revSum = round2(r.analysis.clients.reduce((s, c) => s + c.revenue, 0));
  assert.strictEqual(revSum, r.analysis.totals.revenue);
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
  assert.ok(lintStrings(['You should raise your prices.']).length > 0);
  assert.ok(lintStrings(['Raise your rate with Acme.']).length > 0);
  assert.ok(lintStrings(['You are undercharging for this work.']).length > 0);
  assert.ok(lintStrings(['This rate is too low.']).length > 0);
  assert.ok(lintStrings(['That is below market for your skills.']).length > 0);
  assert.ok(lintStrings(['We recommend dropping this client.']).length > 0);
  assert.ok(lintStrings(['This report is not tax advice at all... tax advice']).length > 0);
});

test('advice linter allows purely descriptive language', () => {
  assert.strictEqual(lintStrings([
    'Acme accounts for 42.0% of tracked hours in this file.',
    'Observed per-covered-hour rates span $60.00 to $150.00.',
    'Billing figures are present on 12 entries covering 40 hour(s).',
  ]).length, 0);
});

test('the mandatory disclaimer does not trip its own linter', () => {
  const { DISCLAIMER } = require(path.join(ROOT, 'engine', 'constants.js'));
  assert.doesNotThrow(() => assertNoAdvice([DISCLAIMER]));
  assert.ok(DISCLAIMER.includes('not financial, tax, or legal advice'));
});

test('assertNoAdvice FAILS CLOSED with a machine-readable code', () => {
  assert.throws(
    () => assertNoAdvice(['You should charge every client double.']),
    (e) => e.code === 'ADVICE_LINTER_FAILED' && e.violations.length > 0
  );
});

test('every engine-authored string in a real run passes the linter', () => {
  const r = analyze(SAMPLE);
  const { summaryStrings } = require(path.join(ROOT, 'engine', 'summary.js'));
  assert.strictEqual(lintStrings(summaryStrings(r.summary)).length, 0);
});

test('a client NAMED with banned words does not withhold the buyer\'s own report', () => {
  // The linter judges the ENGINE's wording, not the buyer's data.
  const csv = rows('Date,Client,Hours,Amount', [
    ['2025-01-01', 'Charge More LLC', 5, 500],
    ['2025-02-01', 'We Recommend Ltd', 1, 100],
  ]);
  const r = analyze(csv);
  assert.strictEqual(r.analysis.clients[0].label, 'Charge More LLC');
  // …and the note that embeds that name is still rendered for the reader.
  assert.ok(r.summary.notes.some((n) => n.includes('Charge More LLC')));
  // …while the lint-safe twin has the name replaced by a placeholder.
  assert.ok(r.summary.lintableNotes.some((n) => n.includes('<client>')));
  assert.ok(!r.summary.lintableNotes.some((n) => n.includes('Charge More LLC')));
});

test('the linter still guards the engine\'s own sentences', () => {
  const { buildSummary, summaryStrings } = require(path.join(ROOT, 'engine', 'summary.js'));
  const ing = ingest.ingestCsv(rows('Date,Client,Hours', [['2025-01-01', 'A', 2]]));
  const s = buildSummary(analyzeRates(ing.entries, {}), { skippedCount: 0 });
  s.headline.push('We recommend you raise your rate.'); // simulate a regression in engine wording
  assert.throws(() => assertNoAdvice(summaryStrings(s)), (e) => e.code === 'ADVICE_LINTER_FAILED');
});

// ============================================================== validation

test('validation gate rejects empty, non-string and oversized input with codes', () => {
  assert.throws(() => analyze(''), (e) => e.code === 'EMPTY_FILE');
  assert.throws(() => analyze(null), (e) => e.code === 'BAD_INPUT_TYPE');
  assert.throws(() => analyze('Date,Client,Hours\n' + 'x\n'.repeat(50001)), (e) => e.code === 'TOO_MANY_ROWS');
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
  for (const name of ['Summary', 'Clients', 'Monthly', 'All Entries', 'Flagged Rows']) {
    assert.ok(wb.includes(`name="${name}"`), `workbook must declare sheet ${name}`);
  }
  for (let i = 1; i <= 5; i++) {
    assert.ok(parts[`xl/worksheets/sheet${i}.xml`].includes('<row r="1">'), `sheet${i} must have a header row`);
  }
});

test('XLSX escapes hostile client names instead of emitting broken XML', () => {
  const csv = rows('Date,Client,Hours', [['2025-01-01', '"Ampersand & <script>alert(1)</script>"', 2]]);
  const { xlsx } = buildReport(csv);
  const parts = unzipEntries(xlsx);
  const clients = parts['xl/worksheets/sheet2.xml'];
  assert.ok(clients.includes('&amp;'), 'ampersand must be escaped');
  assert.ok(!clients.includes('<script>'), 'raw markup must not survive into the sheet');
});

test('the flagged-rows sheet says so explicitly when nothing was flagged', () => {
  const { xlsx } = buildReport(rows('Date,Client,Hours', [['2025-01-01', 'A', 2]]));
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
  assert.ok(s.includes('Effective Hourly Rate Report'));
  assert.ok(s.includes('not financial, tax, or legal advice'));
});

test('PDF escapes parentheses and backslashes in client names', () => {
  const csv = rows('Date,Client,Hours', [['2025-01-01', '"Paren (Co) \\\\ Slash"', 2]]);
  const { pdf } = buildReport(csv);
  const s = pdf.toString('latin1');
  assert.ok(s.includes('\\(Co\\)') || s.includes('Paren \\('), 'parentheses must be backslash-escaped');
});

test('PDF shows n/a instead of inventing a rate when no billing figures exist', () => {
  const { pdf } = buildReport(rows('Date,Client,Hours', [['2025-01-01', 'A', 2]]));
  const s = pdf.toString('latin1');
  assert.ok(s.includes('n/a'));
  assert.ok(s.includes('hour figures only'));
});

test('PDF and XLSX are byte-deterministic across runs', () => {
  const a = buildReport(SAMPLE);
  const b = buildReport(SAMPLE);
  assert.ok(a.pdf.equals(b.pdf), 'PDF bytes must be identical');
  assert.ok(a.xlsx.equals(b.xlsx), 'XLSX bytes must be identical');
});

// ============================================================= sample file

test('the shipped sample file produces a coherent, reconciled report', () => {
  const r = analyze(SAMPLE);
  assert.strictEqual(r.summary.counts.skippedRows, 3, 'the sample deliberately contains 3 bad rows');
  assert.strictEqual(r.summary.counts.clients, 5);
  assert.ok(r.analysis.mergedSpellings.length >= 2, 'sample exercises spelling merges (Acme + Meridian)');
  assert.strictEqual(r.analysis.meta.negativeAmountsIgnored, 1, 'the sample has one negative-amount row');
  assert.strictEqual(r.analysis.rates.available, true);
  assert.ok(r.analysis.rates.coveragePctOfHours < 100, 'one entry deliberately lacks an amount');
  assert.strictEqual(r.analysis.billableShare.available, true);
  assert.ok(r.analysis.billableShare.billableSharePct > 0 && r.analysis.billableShare.billableSharePct < 100);
  assert.strictEqual(r.summary.window.start, '2025-01-06');
  assert.strictEqual(r.summary.window.end, '2025-06-20');
  assert.strictEqual(r.summary.counts.monthsObserved, 6);
  const internal = r.analysis.clients.find((c) => c.label === 'Internal');
  assert.ok(internal, 'the sample tracks non-billable internal time');
  assert.strictEqual(internal.nonBillableHours, internal.hours, 'internal time is all non-billable');
  assert.strictEqual(internal.effectiveRateCovered, null, 'internal time has no billing figures');
});
