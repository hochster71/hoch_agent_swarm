// engine/aging.js
//
// Stage 2: Compute days-past-due and bucket every OUTSTANDING invoice into the aging
// buckets (Current / 1–30 / 31–60 / 61–90 / 90+). Deterministic; measured from each
// invoice's due date to the report "as of" date.
//
// Paid/zero-balance invoices are excluded from the aging (they owe nothing) but counted
// separately so totals reconcile.

'use strict';

const { AGING_BUCKETS, PAID_EPSILON } = require('./constants');

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

function daysBetween(aIso, bIso) {
  const a = Date.parse(aIso + 'T00:00:00Z');
  const b = Date.parse(bIso + 'T00:00:00Z');
  return Math.round((b - a) / 86400000);
}

function bucketFor(daysPastDue) {
  for (const b of AGING_BUCKETS) {
    if (daysPastDue >= b.lower && daysPastDue <= b.upper) return b;
  }
  return AGING_BUCKETS[AGING_BUCKETS.length - 1];
}

// Choose the report as-of date: profile.as_of, else the latest due date in the file,
// else today is NOT used (determinism) — we fall back to the latest issue/due date.
function resolveAsOf(invoices, profile) {
  if (profile && profile.as_of) {
    const p = String(profile.as_of).match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (p) return `${p[1]}-${String(+p[2]).padStart(2, '0')}-${String(+p[3]).padStart(2, '0')}`;
  }
  const dates = invoices.map((i) => i.dueDate).filter(Boolean).sort();
  return dates.length ? dates[dates.length - 1] : null;
}

// aging(invoices, profile) -> {
//   asOf, aged:[invoice+daysPastDue+bucket...], buckets:[{key,label,balance,count}],
//   totalOutstanding, paidCount, paidBalanceExcluded
// }
function aging(invoices, profile) {
  const asOf = resolveAsOf(invoices, profile);

  const buckets = AGING_BUCKETS.map((b) => ({ key: b.key, label: b.label, balance: 0, count: 0 }));
  const bucketIndex = new Map(AGING_BUCKETS.map((b, i) => [b.key, i]));

  const aged = [];
  let totalOutstanding = 0;
  let paidCount = 0;

  for (const inv of invoices) {
    if (inv.balance <= PAID_EPSILON) { paidCount += 1; continue; }
    const daysPastDue = asOf ? daysBetween(inv.dueDate, asOf) : 0;
    const b = bucketFor(daysPastDue);
    const bi = bucketIndex.get(b.key);
    buckets[bi].balance = round2(buckets[bi].balance + inv.balance);
    buckets[bi].count += 1;
    totalOutstanding = round2(totalOutstanding + inv.balance);
    aged.push(Object.assign({}, inv, { daysPastDue, bucketKey: b.key, bucketLabel: b.label }));
  }

  // Percent of outstanding per bucket.
  for (const bk of buckets) {
    bk.pctOfOutstanding = totalOutstanding > 0 ? round2((bk.balance / totalOutstanding) * 100) : 0;
  }

  // Sort aged rows by most overdue first.
  aged.sort((a, b) => b.daysPastDue - a.daysPastDue || b.balance - a.balance);

  return {
    asOf,
    aged,
    buckets,
    totalOutstanding,
    paidCount,
    outstandingCount: aged.length,
  };
}

module.exports = { aging, bucketFor, daysBetween, resolveAsOf };
