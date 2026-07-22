// test/engine.test.js
//
// HFF — Getting-Paid Speed Report — engine tests. Zero dependencies:
// `node test/engine.test.js`. Every assertion checks REAL engine output.
// Nothing is mocked.
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const {
  ingestCsv, splitCsv, parseDate, parseAmount, parseTerms, detectDateOrder, clientKey, mapHeaders,
} = require('../engine/ingest');
const { analyzeTiming, median, mean, shareOf } = require('../engine/timing');
const { buildSummary, summaryStrings, money, pct, days } = require('../engine/summary');
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

const SAMPLE = fs.readFileSync(path.join(__dirname, '..', 'engine', 'sample', 'sample_invoices.csv'), 'utf8');

// A small, fully hand-computed file used for exact-value assertions.
const MINI = [
  'issued date,client,amount,paid date,terms',
  '2026-01-01,Acme LLC,100,2026-01-11,Net 30',      // dtp 10, on time
  '2026-02-01,Acme Company,200,2026-03-15,Net 30',  // dtp 42, after due (merges with Acme LLC)
  '2026-01-05,Beta Co,500,,Net 15',                 // open, overdue
  '2026-03-01,Beta Co,300,2026-03-02,Due on receipt', // dtp 1, after due (net-0)
].join('\n');

function miniAnalysis() {
  const ing = ingestCsv(MINI);
  return analyzeTiming(ing.invoices, {
    hasDueColumn: ing.hasDueColumn, hasTermsColumn: ing.hasTermsColumn,
    clientFromName: ing.clientFromName, creditNoteCount: ing.creditNoteCount,
    creditNoteTotal: ing.creditNoteTotal, currencies: ing.currencies,
  });
}

// tiny zip reader (no data descriptors; matches our writer)
function readZip(buf) {
  const out = {};
  let i = 0;
  while (i + 4 <= buf.length && buf.readUInt32LE(i) === 0x04034b50) {
    const method = buf.readUInt16LE(i + 8);
    const csize = buf.readUInt32LE(i + 18);
    const nameLen = buf.readUInt16LE(i + 26);
    const extraLen = buf.readUInt16LE(i + 28);
    const name = buf.slice(i + 30, i + 30 + nameLen).toString('utf8');
    const dataStart = i + 30 + nameLen + extraLen;
    const raw = buf.slice(dataStart, dataStart + csize);
    out[name] = method === 8 ? zlib.inflateRawSync(raw) : raw;
    i = dataStart + csize;
  }
  return out;
}

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
  const g = splitCsv('﻿date,client\n2026-01-01,X');
  assert.strictEqual(g[0][0], 'date');
});

console.log('\n=== header mapping ===');

t('maps issued/client/amount/paid aliases', () => {
  const m = mapHeaders(['Invoice Date', 'Customer', 'Invoice Amount', 'Paid Date']);
  assert.strictEqual(m.issued, 0);
  assert.strictEqual(m.client, 1);
  assert.strictEqual(m.amount, 2);
  assert.strictEqual(m.paid, 3);
});
t('maps due/terms/status/currency/reference when present', () => {
  const m = mapHeaders(['Date', 'Client', 'Amount', 'Payment Date', 'Due Date', 'Terms', 'Status', 'Currency', 'Invoice #']);
  assert.strictEqual(m.due, 4);
  assert.strictEqual(m.terms, 5);
  assert.strictEqual(m.status, 6);
  assert.strictEqual(m.currency, 7);
  assert.strictEqual(m.reference, 8);
});
t('falls back to a name column as the client only when nothing stronger exists', () => {
  const m = mapHeaders(['Date', 'Name', 'Amount', 'Paid Date']);
  assert.strictEqual(m.client, 1);
  assert.strictEqual(m._clientFromName, true);
});
t('prefers a real client column over a name column', () => {
  const m = mapHeaders(['Date', 'Name', 'Client', 'Amount', 'Paid Date']);
  assert.strictEqual(m.client, 2);
  assert.strictEqual(m._clientFromName, undefined);
});

console.log('\n=== dates, amounts, terms ===');

t('parseDate reads ISO', () => {
  assert.deepStrictEqual(parseDate('2026-03-09'), { y: 2026, m: 3, d: 9 });
});
t('parseDate honours US vs UK order', () => {
  assert.deepStrictEqual(parseDate('03/04/2026', 'us'), { y: 2026, m: 3, d: 4 });
  assert.deepStrictEqual(parseDate('03/04/2026', 'uk'), { y: 2026, m: 4, d: 3 });
});
t('parseDate rejects impossible dates', () => {
  assert.strictEqual(parseDate('2026-13-01'), null);
  assert.strictEqual(parseDate('not-a-date'), null);
});
t('detectDateOrder infers UK when first field exceeds 12', () => {
  assert.strictEqual(detectDateOrder(['25/01/2026']), 'uk');
  assert.strictEqual(detectDateOrder(['01/25/2026']), 'us');
});
t('parseAmount strips currency, commas, parentheses', () => {
  assert.strictEqual(parseAmount('$1,200.50'), 1200.5);
  assert.strictEqual(parseAmount('(300)'), -300);
  assert.strictEqual(parseAmount('1.234,56'), 1234.56); // EU
  assert.strictEqual(parseAmount(''), null);
});
t('parseTerms reads Net-N, plain N, N days, and due-on-receipt', () => {
  assert.strictEqual(parseTerms('Net 30'), 30);
  assert.strictEqual(parseTerms('net15'), 15);
  assert.strictEqual(parseTerms('45'), 45);
  assert.strictEqual(parseTerms('30 days'), 30);
  assert.strictEqual(parseTerms('Due on receipt'), 0);
  assert.strictEqual(parseTerms('COD'), 0);
  assert.strictEqual(parseTerms('whenever'), null);
  assert.strictEqual(parseTerms(''), null);
});

console.log('\n=== client keys ===');

t('clientKey strips corporate suffixes so spellings merge', () => {
  assert.strictEqual(clientKey('Acme LLC'), 'ACME');
  assert.strictEqual(clientKey('Acme Company'), 'ACME');
  assert.strictEqual(clientKey('Acme, Inc.'), 'ACME');
});
t('clientKey drops a leading THE and folds &', () => {
  assert.strictEqual(clientKey('The Beta Co'), 'BETA');
  assert.strictEqual(clientKey('Gamma & Sons'), 'GAMMA AND SONS');
});

console.log('\n=== ingest gates ===');

t('MISSING_COLUMNS when the paid-date column is absent', () => {
  try { ingestCsv('date,client,amount\n2026-01-01,X,100'); assert.fail('should throw'); }
  catch (e) { assert.strictEqual(e.code, 'MISSING_COLUMNS'); assert.ok(e.missing.includes('paid date')); }
});
t('MISSING_COLUMNS lists every missing required column', () => {
  try { ingestCsv('foo,bar\n1,2'); assert.fail('should throw'); }
  catch (e) {
    assert.strictEqual(e.code, 'MISSING_COLUMNS');
    assert.deepStrictEqual(e.missing.sort(), ['amount', 'client', 'issued date', 'paid date'].sort());
  }
});
t('EMPTY_FILE and NO_ROWS gates fire', () => {
  try { ingestCsv(''); assert.fail(); } catch (e) { assert.strictEqual(e.code, 'EMPTY_FILE'); }
  try { ingestCsv('date,client,amount,paid date'); assert.fail(); } catch (e) { assert.strictEqual(e.code, 'NO_ROWS'); }
});
t('blank paid date means the invoice is open, not an error', () => {
  const ing = ingestCsv('date,client,amount,paid date\n2026-01-01,X,100,');
  assert.strictEqual(ing.invoices.length, 1);
  assert.strictEqual(ing.invoices[0].isPaid, false);
  assert.strictEqual(ing.invoices[0].paidDate, null);
});
t('an unreadable issue date is flagged, not dropped', () => {
  const ing = ingestCsv('date,client,amount,paid date\nnope,X,100,\n2026-01-02,Y,200,');
  assert.strictEqual(ing.invoices.length, 1);
  assert.strictEqual(ing.skipped[0].reason, 'unreadable_issue_date');
  assert.strictEqual(ing.skipped[0].line, 2);
});
t('paid-before-issued is flagged with its line number', () => {
  const ing = ingestCsv('date,client,amount,paid date\n2026-02-01,X,100,2026-01-01\n2026-03-01,Y,200,2026-03-05');
  assert.strictEqual(ing.invoices.length, 1);
  assert.strictEqual(ing.skipped[0].reason, 'paid_before_issued');
});
t('a negative amount is treated as a credit note and disclosed', () => {
  const ing = ingestCsv('date,client,amount,paid date\n2026-01-01,X,100,2026-01-05\n2026-01-02,X,-30,2026-01-03');
  assert.strictEqual(ing.invoices.length, 1);
  assert.strictEqual(ing.creditNoteCount, 1);
  assert.strictEqual(ing.creditNoteTotal, 30);
  assert.strictEqual(ing.skipped[0].reason, 'credit_note');
});
t('NO_VALID_ROWS when nothing survives', () => {
  try { ingestCsv('date,client,amount,paid date\nbad,X,100,'); assert.fail(); }
  catch (e) { assert.strictEqual(e.code, 'NO_VALID_ROWS'); }
});

console.log('\n=== due basis ===');

t('explicit due-date column wins over terms', () => {
  const ing = ingestCsv('date,client,amount,paid date,due date,terms\n2026-01-01,X,100,,2026-01-20,Net 30');
  assert.strictEqual(ing.invoices[0].dueBasis, 'due_column');
  assert.strictEqual(ing.invoices[0].dueDate, '2026-01-20');
});
t('parseable terms set the due day when no due column', () => {
  const ing = ingestCsv('date,client,amount,paid date,terms\n2026-01-01,X,100,,Net 15');
  assert.strictEqual(ing.invoices[0].dueBasis, 'terms');
  assert.strictEqual(ing.invoices[0].dueDay - ing.invoices[0].issuedDay, 15);
});
t('assumed net-30 fallback when neither due nor terms exist', () => {
  const ing = ingestCsv('date,customer,amount,payment date\n2026-01-01,Solo Inc,1000,2026-02-15');
  assert.strictEqual(ing.invoices[0].dueBasis, 'assumed_net_30');
  assert.strictEqual(ing.invoices[0].dueDay - ing.invoices[0].issuedDay, 30);
});

console.log('\n=== timing arithmetic (hand-computed MINI) ===');

t('days-to-pay is paid minus issued', () => {
  const a = miniAnalysis();
  const acme = a.clients.find((c) => c.clientKey === 'ACME');
  assert.deepStrictEqual(acme.rows.map((r) => r.daysToPay), [10, 42]);
});
t('two spellings of Acme merge into one client', () => {
  const a = miniAnalysis();
  const acme = a.clients.find((c) => c.clientKey === 'ACME');
  assert.strictEqual(acme.spellingCount, 2);
  assert.strictEqual(acme.invoiceCount, 2);
  assert.strictEqual(acme.billed, 300);
});
t('per-client median / mean / fastest / slowest days-to-pay', () => {
  const a = miniAnalysis();
  const acme = a.clients.find((c) => c.clientKey === 'ACME');
  assert.strictEqual(acme.medianDaysToPay, 26);
  assert.strictEqual(acme.meanDaysToPay, 26);
  assert.strictEqual(acme.fastestDaysToPay, 10);
  assert.strictEqual(acme.slowestDaysToPay, 42);
});
t('per-client on-time vs late against each invoice due basis', () => {
  const a = miniAnalysis();
  const acme = a.clients.find((c) => c.clientKey === 'ACME');
  assert.strictEqual(acme.onTimeCount, 1);
  assert.strictEqual(acme.lateCount, 1);
  assert.strictEqual(acme.onTimePct, 50);
});
t('a same-day payment can still be after a due-on-receipt due date', () => {
  const a = miniAnalysis();
  const beta = a.clients.find((c) => c.clientKey === 'BETA');
  const paidRow = beta.rows.find((r) => r.isPaid);
  assert.strictEqual(paidRow.daysToPay, 1);
  assert.strictEqual(paidRow.onTime, false); // paid day 1 > due day 0
});
t('open invoices are counted, aged, and marked overdue', () => {
  const a = miniAnalysis();
  const beta = a.clients.find((c) => c.clientKey === 'BETA');
  assert.strictEqual(beta.openCount, 1);
  assert.strictEqual(beta.outstanding, 500);
  assert.strictEqual(beta.overdueOpenCount, 1);
  assert.strictEqual(beta.oldestOpenAgeDays, 69);
});
t('overall totals reconcile', () => {
  const a = miniAnalysis().totals;
  assert.strictEqual(a.invoiceCount, 4);
  assert.strictEqual(a.clientCount, 2);
  assert.strictEqual(a.billed, 1100);
  assert.strictEqual(a.paidCount, 3);
  assert.strictEqual(a.openCount, 1);
  assert.strictEqual(a.paidBilled, 600);
  assert.strictEqual(a.outstanding, 500);
  assert.strictEqual(a.medianDaysToPay, 10);
  assert.strictEqual(a.meanDaysToPay, 17.7);
  assert.strictEqual(a.fastestDaysToPay, 1);
  assert.strictEqual(a.slowestDaysToPay, 42);
  assert.strictEqual(a.onTimePct, 33.3);
  assert.strictEqual(a.pctPaidByCount, 75);
  assert.strictEqual(a.pctPaidByValue, 54.5);
  assert.strictEqual(a.overdueOpenCount, 1);
  assert.strictEqual(a.overdueOpenTotal, 500);
  assert.strictEqual(a.oldestOpenAgeDays, 69);
});
t('clients rank by amount billed, largest first', () => {
  const a = miniAnalysis();
  assert.strictEqual(a.clients[0].clientKey, 'BETA');
  assert.strictEqual(a.clients[0].billedSharePct, 72.7);
  assert.strictEqual(a.clients[1].clientKey, 'ACME');
  assert.strictEqual(a.clients[1].billedSharePct, 27.3);
});
t('concentration HHI and effective client count', () => {
  const c = miniAnalysis().concentration;
  assert.strictEqual(c.hhi, 6033.1);
  assert.strictEqual(c.effectiveClientCount, 1.7);
  assert.strictEqual(c.top1.sharePct, 72.7);
  assert.strictEqual(c.top3.clients, 2);
  assert.strictEqual(c.top3.sharePct, 100);
});
t('due-basis mix is counted per invoice', () => {
  const mix = miniAnalysis().dueBasisMix;
  assert.deepStrictEqual(mix, { due_column: 0, terms: 4, assumed_net_30: 0 });
});
t('window start/end/asOf come from the data', () => {
  const w = miniAnalysis().window;
  assert.strictEqual(w.start, '2026-01-01');
  assert.strictEqual(w.end, '2026-03-01');
  assert.strictEqual(w.asOf, '2026-03-15');
  assert.strictEqual(w.monthsObserved, 3);
});
t('monthly series reconciles to the file', () => {
  const m = miniAnalysis().monthly;
  const total = m.reduce((s, x) => s + x.billed, 0);
  assert.strictEqual(Math.round(total * 100) / 100, 1100);
  assert.strictEqual(m.reduce((s, x) => s + x.invoices, 0), 4);
});

console.log('\n=== helpers ===');

t('median / mean helpers', () => {
  assert.strictEqual(median([1, 2, 3]), 2);
  assert.strictEqual(median([1, 2, 3, 4]), 2.5);
  assert.strictEqual(mean([2, 4]), 3);
});
t('shareOf rounds to one decimal', () => {
  assert.strictEqual(shareOf(1, 3), 33.3);
  assert.strictEqual(shareOf(0, 0), 0);
});
t('money / pct / days formatting', () => {
  assert.strictEqual(money(1200.5), '$1,200.50');
  assert.strictEqual(pct(33.33), '33.3%');
  assert.strictEqual(pct(null), 'n/a');
  assert.strictEqual(days(1), '1 day');
  assert.strictEqual(days(10), '10 days');
  assert.strictEqual(days(null), 'n/a');
});

console.log('\n=== advice linter (HARD GUARDRAIL) ===');

t('clean strings pass', () => {
  assert.strictEqual(assertNoAdvice(['This file records 3 invoices to 2 clients.']), true);
});
t('a collections instruction is caught and withholds', () => {
  try { assertNoAdvice(['You should chase the client for payment.']); assert.fail(); }
  catch (e) { assert.strictEqual(e.code, 'ADVICE_LINTER_FAILED'); }
});
t('a judgement about a client is caught', () => {
  const v = lintStrings(['They are a deadbeat client.']);
  assert.ok(v.length >= 1);
});
t('neutral factual descriptors are NOT banned', () => {
  assert.strictEqual(assertNoAdvice([
    'Three invoices are still open and past the due date; two were paid late.',
  ]), true);
});
t('BANNED_PHRASES is a non-empty list of lowercase phrases', () => {
  assert.ok(BANNED_PHRASES.length > 20);
  assert.ok(BANNED_PHRASES.every((p) => p === p.toLowerCase()));
});
t('a client literally named with a banned phrase does NOT withhold a paid report', () => {
  const csv = [
    'date,client,amount,paid date,terms',
    '2026-01-01,Chase Them Consulting,5000,2026-01-10,Net 30',
    '2026-01-05,Small Co,100,,Net 30',
  ].join('\n');
  // Must not throw — the lint-safe twin replaces the client name.
  const rep = analyze(csv);
  const displayHasName = rep.summary.notes.some((n) => n.includes('Chase Them Consulting'));
  const lintHasToken = rep.summary.lintNotes.some((n) => n.includes('<client>'));
  assert.ok(displayHasName, 'display note should keep the real client name');
  assert.ok(lintHasToken, 'lint-safe twin should carry the <client> token');
  assert.ok(summaryStrings(rep.summary).every((s) => !/chase them/i.test(s)),
    'no linted string may contain the banned phrase');
});
t('the disclaimer itself passes its own linter', () => {
  const rep = analyze(MINI);
  assert.strictEqual(assertNoAdvice([rep.disclaimer]), true);
});

console.log('\n=== validation gate ===');

t('validateCsvInput rejects non-string and empty', () => {
  try { validateCsvInput(42); assert.fail(); } catch (e) { assert.strictEqual(e.code, 'BAD_INPUT_TYPE'); }
  try { validateCsvInput('   '); assert.fail(); } catch (e) { assert.strictEqual(e.code, 'EMPTY_FILE'); }
});

console.log('\n=== full report: XLSX ===');

t('renderXlsx produces a valid zip with the five expected sheets', () => {
  const { xlsx } = buildReport(MINI);
  assert.ok(Buffer.isBuffer(xlsx));
  assert.strictEqual(xlsx[0], 0x50); assert.strictEqual(xlsx[1], 0x4b); // "PK"
  const files = readZip(xlsx);
  assert.ok(files['[Content_Types].xml']);
  for (let i = 1; i <= 5; i++) assert.ok(files[`xl/worksheets/sheet${i}.xml`], `sheet${i} present`);
  const s1 = files['xl/worksheets/sheet1.xml'].toString('utf8');
  assert.ok(s1.includes('Getting-Paid Speed Report'));
});
t('XLSX inflates cleanly and every worksheet is well-formed XML', () => {
  const { xlsx } = buildReport(SAMPLE);
  const files = readZip(xlsx);
  for (const [name, buf] of Object.entries(files)) {
    if (/worksheets\/sheet\d+\.xml$/.test(name)) {
      const xml = buf.toString('utf8');
      assert.ok(xml.startsWith('<?xml'));
      assert.ok(xml.includes('<worksheet'));
      assert.ok(xml.includes('</worksheet>'));
    }
  }
});

console.log('\n=== full report: PDF ===');

t('renderPdf emits a one-page PDF with a matching /Length', () => {
  const { pdf } = buildReport(MINI);
  const s = pdf.toString('latin1');
  assert.ok(s.startsWith('%PDF-1.'));
  assert.ok(s.trimEnd().endsWith('%%EOF'));
  const m = s.match(/<< \/Length (\d+) >>\nstream\n([\s\S]*?)\nendstream/);
  assert.ok(m, 'content stream present');
  const declared = Number(m[1]);
  const actual = Buffer.byteLength(m[2], 'latin1');
  assert.strictEqual(actual, declared, 'declared /Length matches real stream bytes');
});
t('PDF headline reflects the report (median days, outstanding)', () => {
  const { pdf } = buildReport(MINI);
  const s = pdf.toString('latin1');
  assert.ok(s.includes('Median days to pay'));
  assert.ok(s.includes('Outstanding'));
});

console.log('\n=== determinism ===');

t('same input yields byte-identical XLSX and PDF', () => {
  const a = buildReport(MINI);
  const b = buildReport(MINI);
  assert.ok(a.xlsx.equals(b.xlsx));
  assert.ok(a.pdf.equals(b.pdf));
});

console.log('\n=== sample file smoke ===');

t('the shipped sample parses, flags its bad row, and renders', () => {
  const rep = analyze(SAMPLE);
  assert.ok(rep.analysis.totals.invoiceCount >= 15);
  // one unreadable issue date + one credit note flagged
  const reasons = rep.skipped.map((s) => s.reason);
  assert.ok(reasons.includes('unreadable_issue_date'));
  assert.ok(reasons.includes('credit_note'));
  const { xlsx, pdf } = buildReport(SAMPLE);
  assert.ok(xlsx.length > 800 && pdf.length > 800);
});
t('sample merges the two Acme spellings', () => {
  const rep = analyze(SAMPLE);
  const acme = rep.analysis.clients.find((c) => c.clientKey === 'ACME');
  assert.ok(acme && acme.spellingCount >= 2);
});
t('summary counts reconcile with analysis on the sample', () => {
  const rep = analyze(SAMPLE);
  assert.strictEqual(rep.summary.counts.invoices, rep.analysis.totals.invoiceCount);
  assert.strictEqual(rep.summary.counts.paid, rep.analysis.totals.paidCount);
  assert.strictEqual(rep.summary.counts.open, rep.analysis.totals.openCount);
});

console.log(`\n${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
