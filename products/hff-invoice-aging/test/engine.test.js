// test/engine.test.js
//
// Runs the HFF Invoice Aging engine on 3 differently-shaped sample CSVs and asserts the
// outputs are correctly SHAPED and internally consistent. Zero-dependency runner (plain
// Node assertions) so it runs with `node test/engine.test.js`.
//
// Checks: engine produces files; validation passes; buckets & customer totals reconcile
// to the CSV; days-past-due bucketing is correct; advice linter finds zero phrases;
// XLSX/PDF byte signatures are correct. Also asserts the advice linter FAILS CLOSED on a
// deliberately advice-laden string.

'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const { generateAgingReport } = require('../engine');
const { lintStrings, assertNoAdvice } = require('../engine/advice_linter');
const { ingest } = require('../engine/ingest');
const { AGING_BUCKETS } = require('../engine/constants');

const SAMPLE_DIR = path.join(__dirname, '..', 'engine', 'sample');
const FIXED_STAMP = '2026-07-16T00:00:00.000Z';

let passed = 0, failed = 0;
function ok(name, fn) {
  try { fn(); passed++; console.log('  PASS  ' + name); }
  catch (e) { failed++; console.log('  FAIL  ' + name + '  ->  ' + e.message); }
}
function round2(n) { return Math.round((n + Number.EPSILON) * 100) / 100; }

async function runSample(file, profile) {
  const csv = fs.readFileSync(path.join(SAMPLE_DIR, file), 'utf8');
  const result = await generateAgingReport({ csv, profile, generatedAt: FIXED_STAMP });
  return { csv, result };
}

(async function main() {
  console.log('HFF Invoice Aging engine — validation suite\n');

  const cases = [
    { file: 'sample_invoices.csv', profile: {} },
    { file: 'sample_balance_status.csv', profile: {} },
    { file: 'sample_currency_badrow.csv', profile: {} },
  ];

  for (const c of cases) {
    console.log(`\n[${c.file}]`);
    const { csv, result } = await runSample(c.file, c.profile);
    const { report, validation, files } = result;
    const ag = report.aging;

    ok('validation.ok is true', () => assert.strictEqual(validation.ok, true, JSON.stringify(validation.checks.filter((x) => !x.pass))));

    ok('every validation check passes', () => {
      const bad = validation.checks.filter((x) => !x.pass);
      assert.strictEqual(bad.length, 0, 'failing: ' + bad.map((b) => b.name).join(','));
    });

    ok('produces non-empty XLSX with correct signature', () => {
      assert.ok(files.xlsx.length > 1000, 'xlsx too small');
      assert.strictEqual(files.xlsx.slice(0, 2).toString('latin1'), 'PK');
      assert.ok(/^invoice_aging_.*\.xlsx$/.test(files.xlsxName));
    });

    ok('produces valid one-page PDF', () => {
      assert.ok(files.pdf.length > 500, 'pdf too small');
      assert.strictEqual(files.pdf.slice(0, 5).toString('latin1'), '%PDF-');
      assert.ok(files.pdf.slice(-6).toString('latin1').includes('EOF'));
    });

    ok('bucket balances reconcile to total outstanding', () => {
      const bucketSum = round2(ag.buckets.reduce((s, b) => s + b.balance, 0));
      assert.ok(Math.abs(bucketSum - ag.totalOutstanding) < 0.05, `bucketSum ${bucketSum} vs total ${ag.totalOutstanding}`);
    });

    ok('customer totals reconcile to total outstanding', () => {
      const custSum = round2(report.byCustomer.reduce((s, c) => s + c.outstanding, 0));
      assert.ok(Math.abs(custSum - ag.totalOutstanding) < 0.05, `custSum ${custSum} vs total ${ag.totalOutstanding}`);
    });

    ok('total outstanding matches sum of positive balances from ingest', () => {
      const parsed = ingest(csv);
      const owed = round2(parsed.invoices.reduce((s, i) => s + Math.max(0, i.balance), 0));
      assert.ok(Math.abs(owed - ag.totalOutstanding) < 0.05, `ingest owed ${owed} vs report ${ag.totalOutstanding}`);
    });

    ok('bucket percentages within [0,100] and sum ~100', () => {
      let sum = 0;
      for (const b of ag.buckets) { assert.ok(b.pctOfOutstanding >= 0 && b.pctOfOutstanding <= 100, `pct ${b.pctOfOutstanding}`); sum += b.pctOfOutstanding; }
      if (ag.totalOutstanding > 0) assert.ok(sum >= 99.5 && sum <= 100.5, `pct sum ${round2(sum)}`);
    });

    ok('every aged invoice is in the correct bucket for its days-past-due', () => {
      for (const inv of ag.aged) {
        const b = AGING_BUCKETS.find((x) => x.key === inv.bucketKey);
        assert.ok(inv.daysPastDue >= b.lower && inv.daysPastDue <= b.upper, `${inv.invoice} dpd ${inv.daysPastDue} not in ${inv.bucketKey}`);
      }
    });

    ok('no negative outstanding balances', () => {
      assert.ok(ag.aged.every((i) => i.balance >= 0));
      assert.ok(ag.totalOutstanding >= 0);
    });

    ok('advice linter finds zero advice phrases in rendered strings', () => {
      const strings = [report.disclaimer, ...ag.aged.map((i) => i.customer), ...report.byCustomer.map((c) => c.customer), ...ag.buckets.map((b) => b.label)];
      const v = lintStrings(strings);
      assert.strictEqual(v.length, 0, 'violations: ' + JSON.stringify(v));
    });

    ok('non-advice banner present', () => {
      assert.ok(/not financial, collections, or legal advice/i.test(report.disclaimer));
    });
  }

  // Targeted assertions on known numbers.
  console.log('\n[targeted assertions]');

  const s1 = await runSample('sample_invoices.csv', {});
  ok('sample_invoices: as-of is latest due date 2026-08-01', () => assert.strictEqual(s1.result.report.aging.asOf, '2026-08-01'));
  ok('sample_invoices: total outstanding = 19200', () => assert.strictEqual(round2(s1.result.report.aging.totalOutstanding), 19200));
  ok('sample_invoices: 90+ bucket = 14500 across 3 invoices', () => {
    const b = s1.result.report.aging.buckets.find((x) => x.key === 'd90_plus');
    assert.strictEqual(round2(b.balance), 14500); assert.strictEqual(b.count, 3);
  });
  ok('sample_invoices: fully-paid INV-1002 is excluded (paidCount=1)', () => {
    assert.strictEqual(s1.result.report.aging.paidCount, 1);
    assert.ok(!s1.result.report.aging.aged.some((i) => i.invoice === 'INV-1002'));
  });
  ok('sample_invoices: Brightline LLC is top debtor at 7750', () => {
    const top = s1.result.report.byCustomer[0];
    assert.strictEqual(top.customer, 'Brightline LLC');
    assert.strictEqual(round2(top.outstanding), 7750);
  });
  ok('sample_invoices: Current bucket holds only the not-yet-due invoice', () => {
    const cur = s1.result.report.aging.aged.filter((i) => i.bucketKey === 'current');
    assert.strictEqual(cur.length, 1);
    assert.ok(cur[0].daysPastDue <= 0);
  });

  const s2 = await runSample('sample_balance_status.csv', {});
  ok('status=Paid/Void invoices are excluded (paidCount=2)', () => assert.strictEqual(s2.result.report.aging.paidCount, 2));
  ok('balance-column CSV: uses Balance Due directly (Contoso=15400)', () => {
    const c = s2.result.report.byCustomer.find((x) => x.customer === 'Contoso Ltd');
    assert.strictEqual(round2(c.outstanding), 15400);
  });

  const s3 = await runSample('sample_currency_badrow.csv', {});
  ok('flags the unparseable BADROW rather than dropping it', () => {
    assert.ok(s3.result.report.rejected.length >= 1, 'expected a rejected row');
    assert.ok(s3.result.report.rejected.some((r) => /BADROW|missing|unparseable/.test(r.raw + r.reason)));
  });
  ok('parses £ currency + DD-Mon-YYYY dates (Thames Digital = 7640)', () => {
    const c = s3.result.report.byCustomer.find((x) => x.customer === 'Thames Digital');
    assert.ok(c, 'Thames Digital not found');
    assert.strictEqual(round2(c.outstanding), 7640);
  });

  // as_of override changes bucketing deterministically.
  const s1b = await runSample('sample_invoices.csv', { as_of: '2026-04-15' });
  ok('as_of override re-buckets by the given report date', () => {
    assert.strictEqual(s1b.result.report.aging.asOf, '2026-04-15');
    // INV-1008 Evergreen (due 2026-08-01) is now far in the future -> Current.
    const ev = s1b.result.report.aging.aged.find((i) => i.invoice === 'INV-1008');
    assert.ok(ev && ev.bucketKey === 'current', 'future invoice should be Current');
  });

  // Fail-closed proof: linter throws on advice language.
  ok('advice linter FAILS CLOSED on advice language', () => {
    let threw = false;
    try { assertNoAdvice(['You should send to collections and take legal action.']); }
    catch (e) { threw = e.code === 'ADVICE_LINTER_FAILED'; }
    assert.strictEqual(threw, true, 'linter did not fail closed');
  });

  console.log(`\n==== RESULT: ${passed} passed, ${failed} failed ====`);
  process.exit(failed === 0 ? 0 : 1);
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
