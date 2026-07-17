// test/engine.test.js
//
// Runs the HFF Runway engine on 3 differently-shaped sample CSVs and asserts the
// outputs are correctly SHAPED and internally consistent. Zero-dependency runner
// (plain Node assertions) so it runs with `node test/engine.test.js`.
//
// Checks: engine produces files; validation passes; totals reconcile to the CSV;
// est-tax arithmetic verifies; 1099 >$600 rule holds; advice linter finds zero phrases;
// XLSX/PDF byte signatures are correct. Also asserts the advice linter FAILS CLOSED
// on a deliberately advice-laden string.

'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const { generateRunwayPacket } = require('../engine');
const { lintStrings, assertNoAdvice } = require('../engine/advice_linter');
const { ingest } = require('../engine/ingest');

const SAMPLE_DIR = path.join(__dirname, '..', 'engine', 'sample');
const FIXED_STAMP = '2026-07-16T00:00:00.000Z';

let passed = 0;
let failed = 0;
function ok(name, fn) {
  try {
    fn();
    passed++;
    console.log('  PASS  ' + name);
  } catch (e) {
    failed++;
    console.log('  FAIL  ' + name + '  ->  ' + e.message);
  }
}

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

async function runSample(file, profile) {
  const csv = fs.readFileSync(path.join(SAMPLE_DIR, file), 'utf8');
  const result = await generateRunwayPacket({ csv, profile, generatedAt: FIXED_STAMP });
  return { csv, result };
}

(async function main() {
  console.log('HFF Runway engine — validation suite\n');

  const cases = [
    { file: 'sample_transactions.csv', profile: { filing_type: 'single', cash_on_hand: 25000 } },
    { file: 'sample_debit_credit.csv', profile: { filing_type: 'married_joint', cash_on_hand: 18000 } },
    { file: 'sample_with_category.csv', profile: { filing_type: 'single', cash_on_hand: 30000, w9_on_file: ['Contractor Bob Writer'] } },
  ];

  for (const c of cases) {
    console.log(`\n[${c.file}]`);
    const { csv, result } = await runSample(c.file, c.profile);
    const { packet, validation, files } = result;

    ok('validation.ok is true', () => assert.strictEqual(validation.ok, true, JSON.stringify(validation.checks.filter((x) => !x.pass))));

    ok('every validation check passes', () => {
      const bad = validation.checks.filter((x) => !x.pass);
      assert.strictEqual(bad.length, 0, 'failing: ' + bad.map((b) => b.name).join(','));
    });

    ok('produces non-empty XLSX with correct signature', () => {
      assert.ok(files.xlsx.length > 1000, 'xlsx too small');
      // XLSX is a ZIP -> starts with PK\x03\x04
      assert.strictEqual(files.xlsx.slice(0, 2).toString('latin1'), 'PK');
      assert.ok(/^runway_packet_.*\.xlsx$/.test(files.xlsxName));
    });

    ok('produces valid one-page PDF', () => {
      assert.ok(files.pdf.length > 500, 'pdf too small');
      assert.strictEqual(files.pdf.slice(0, 5).toString('latin1'), '%PDF-');
      assert.ok(files.pdf.slice(-6).toString('latin1').includes('EOF'));
    });

    ok('totals reconcile to the raw CSV', () => {
      const parsed = ingest(csv);
      const csvNet = round2(parsed.transactions.reduce((s, t) => s + t.amount, 0));
      const packetNet = round2(packet.transactions.reduce((s, t) => s + t.amount, 0));
      assert.ok(Math.abs(csvNet - packetNet) < 0.05, `csv ${csvNet} vs packet ${packetNet}`);
      const rollupNet = round2(packet.rollup.reduce((s, r) => s + r.net, 0));
      assert.ok(Math.abs(rollupNet - packetNet) < 0.05, `rollup ${rollupNet} vs packet ${packetNet}`);
    });

    ok('category percentages are within [0,100] and sum ~100', () => {
      let sum = 0;
      for (const r of packet.rollup) {
        assert.ok(r.pctOfOutflow >= 0 && r.pctOfOutflow <= 100, `pct ${r.pctOfOutflow}`);
        sum += r.pctOfOutflow;
      }
      if (packet.rollup.some((r) => r.outflow > 0)) {
        assert.ok(sum >= 99.5 && sum <= 100.5, `pct sum ${round2(sum)}`);
      }
    });

    ok('est-tax arithmetic checks (SE, total, quarterly)', () => {
      const et = packet.estTax;
      assert.ok(Math.abs(et.seTax - round2(et.ssPortion + et.medicarePortion)) < 0.01, 'seTax');
      assert.ok(Math.abs(et.totalAnnualTax - round2(et.seTax + et.incomeTax)) < 0.01, 'total');
      assert.ok(Math.abs(round2(et.quarterlyPayment * 4) - et.totalAnnualTax) < 0.05, 'quarterly*4');
      assert.ok(et.totalAnnualTax >= 0 && et.quarterlyPayment >= 0, 'non-negative');
      assert.ok(Math.abs(et.halfSeDeduction - round2(et.seTax / 2)) < 0.01, 'half SE');
    });

    ok('1099 list obeys the >$600 rule exactly', () => {
      for (const cnd of packet.list1099) {
        assert.strictEqual(cnd.isCandidate, cnd.totalPaid > 600, `${cnd.payee} ${cnd.totalPaid}`);
      }
    });

    ok('advice linter finds zero advice phrases in rendered strings', () => {
      const strings = [packet.disclaimer, ...packet.estTax.lines.map((l) => l.label), ...packet.transactions.map((t) => t.description), ...packet.list1099.map((c) => c.payee)];
      const v = lintStrings(strings);
      assert.strictEqual(v.length, 0, 'violations: ' + JSON.stringify(v));
    });

    ok('non-advice banner present', () => {
      assert.ok(/not financial or tax advice/i.test(packet.disclaimer));
    });
  }

  // Cross-cutting assertions on specific expected numbers.
  console.log('\n[targeted assertions]');

  const s3 = await runSample('sample_with_category.csv', { filing_type: 'single', w9_on_file: ['Contractor Bob Writer'] });
  ok('flags the unparseable BADROW rather than dropping it', () => {
    assert.ok(s3.result.packet.rejected.length >= 1, 'expected at least one rejected row');
    assert.ok(s3.result.packet.rejected.some((r) => /BADROW|unparseable/.test(r.raw + r.reason)));
  });

  ok('Bob Writer is a 1099 candidate (1650 > 600) with W-9 on file => not missing', () => {
    const bob = s3.result.packet.list1099.find((c) => /Bob Writer/.test(c.payee));
    assert.ok(bob, 'Bob not found');
    assert.strictEqual(bob.isCandidate, true);
    assert.strictEqual(round2(bob.totalPaid), 1650);
    assert.strictEqual(bob.missingW9, false); // W-9 provided in profile
  });

  const s2 = await runSample('sample_debit_credit.csv', { filing_type: 'single' });
  ok('debit/credit CSV: credits become inflows, debits outflows', () => {
    const income = s2.result.packet.rollup.find((r) => r.category === 'Income');
    assert.ok(income && income.inflow > 0, 'income inflow missing');
    const contractors = s2.result.packet.list1099;
    assert.ok(contractors.some((c) => c.totalPaid > 600), 'expected a >600 contractor');
  });

  // Fail-closed proof: linter throws on advice language.
  ok('advice linter FAILS CLOSED on advice language', () => {
    let threw = false;
    try {
      assertNoAdvice(['We recommend you buy this stock for a guaranteed return.']);
    } catch (e) {
      threw = e.code === 'ADVICE_LINTER_FAILED';
    }
    assert.strictEqual(threw, true, 'linter did not fail closed');
  });

  console.log(`\n==== RESULT: ${passed} passed, ${failed} failed ====`);
  process.exit(failed === 0 ? 0 : 1);
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
