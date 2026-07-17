// engine/summary.js
//
// Stage 3: "Who owes what" — roll the aged invoices up by customer, with each customer's
// outstanding total, invoice count, oldest days-past-due, and per-bucket split.
// Deterministic; sorted by outstanding balance descending.

'use strict';

const { AGING_BUCKETS } = require('./constants');

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// summarizeByCustomer(aged) -> [{ customer, outstanding, count, oldestDaysPastDue, buckets:{key->balance} }]
function summarizeByCustomer(aged) {
  const byCust = new Map();
  for (const inv of aged) {
    if (!byCust.has(inv.customer)) {
      const buckets = {};
      for (const b of AGING_BUCKETS) buckets[b.key] = 0;
      byCust.set(inv.customer, {
        customer: inv.customer,
        outstanding: 0,
        count: 0,
        oldestDaysPastDue: -Infinity,
        buckets,
      });
    }
    const c = byCust.get(inv.customer);
    c.outstanding = round2(c.outstanding + inv.balance);
    c.count += 1;
    c.oldestDaysPastDue = Math.max(c.oldestDaysPastDue, inv.daysPastDue);
    c.buckets[inv.bucketKey] = round2(c.buckets[inv.bucketKey] + inv.balance);
  }
  const list = Array.from(byCust.values()).map((c) => ({
    customer: c.customer,
    outstanding: c.outstanding,
    count: c.count,
    oldestDaysPastDue: c.oldestDaysPastDue === -Infinity ? 0 : c.oldestDaysPastDue,
    buckets: c.buckets,
  }));
  list.sort((a, b) => b.outstanding - a.outstanding || b.oldestDaysPastDue - a.oldestDaysPastDue);
  return list;
}

module.exports = { summarizeByCustomer };
