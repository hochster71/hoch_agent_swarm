// engine/validate.js
//
// Stage 4: Internal-consistency validation. Runs BEFORE any file is released. If any check
// fails, the engine withholds the report (fail-closed) rather than emit a wrong artifact.

'use strict';

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// runValidation(report) -> { ok, checks:[{name, pass, detail}] }
function runValidation(report) {
  const checks = [];
  const add = (name, pass, detail) => checks.push({ name, pass: !!pass, detail: detail || '' });

  const { aging, byCustomer } = report;

  // 1. Bucket balances sum to total outstanding.
  const bucketSum = round2(aging.buckets.reduce((s, b) => s + b.balance, 0));
  add('bucket balances reconcile to total outstanding',
    Math.abs(bucketSum - aging.totalOutstanding) < 0.05,
    `bucketSum=${bucketSum} total=${aging.totalOutstanding}`);

  // 2. Customer outstanding totals sum to total outstanding.
  const custSum = round2(byCustomer.reduce((s, c) => s + c.outstanding, 0));
  add('customer totals reconcile to total outstanding',
    Math.abs(custSum - aging.totalOutstanding) < 0.05,
    `custSum=${custSum} total=${aging.totalOutstanding}`);

  // 3. Bucket counts sum to outstanding invoice count.
  const bucketCount = aging.buckets.reduce((s, b) => s + b.count, 0);
  add('bucket counts reconcile to outstanding invoice count',
    bucketCount === aging.outstandingCount,
    `bucketCount=${bucketCount} outstanding=${aging.outstandingCount}`);

  // 4. Bucket percentages are within [0,100] and sum to ~100 (when anything outstanding).
  let pctSum = 0;
  let pctInRange = true;
  for (const b of aging.buckets) {
    if (b.pctOfOutstanding < 0 || b.pctOfOutstanding > 100) pctInRange = false;
    pctSum += b.pctOfOutstanding;
  }
  add('bucket percentages in range and sum ~100',
    pctInRange && (aging.totalOutstanding <= 0 || (pctSum >= 99.5 && pctSum <= 100.5)),
    `pctSum=${round2(pctSum)}`);

  // 5. No negative outstanding balances.
  add('no negative outstanding balances',
    aging.aged.every((i) => i.balance >= 0) && aging.totalOutstanding >= 0);

  // 6. Non-advice banner present.
  add('non-advice banner present',
    /not financial, collections, or legal advice/i.test(report.disclaimer));

  const ok = checks.every((c) => c.pass);
  return { ok, checks };
}

module.exports = { runValidation };
