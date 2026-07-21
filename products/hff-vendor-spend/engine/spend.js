// engine/spend.js
//
// HFF — Vendor Spend Rollup — deterministic spend analysis.
//
// Everything here is arithmetic over the rows the ingest accepted. No external
// data, no vendor database, no benchmarks, no randomness. Given the same file
// the numbers are byte-identical.
//
// Produces:
//   vendors[]   per-vendor gross paid, refunds, net, share, payment count,
//               first/last payment, month span, min/median/max payment,
//               observed cadence (median gap in days), dormancy against that
//               vendor's OWN median gap, amount drift (first vs last), the
//               spellings merged into the bucket, and category mix.
//   monthly[]   per-month net spend, payment count, active vendors, top vendor.
//   categories[] per-category net spend and share (only when the file has a
//               category column).
//   concentration  top-1/3/5/10 share, HHI (0-10,000), effective vendor count,
//               and how few vendors make up the first 50% / 80% of net spend.
'use strict';

const { DORMANCY_MULTIPLE, MIN_PAYMENTS_FOR_CADENCE } = require('./constants');

function round2(n) {
  return Math.round((Number(n) + Number.EPSILON) * 100) / 100;
}
function round1(n) {
  return Math.round((Number(n) + Number.EPSILON) * 10) / 10;
}

function median(sorted) {
  if (!sorted.length) return 0;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function shareOf(part, whole) {
  if (!whole) return 0;
  return round1((part / whole) * 100);
}

// ------------------------------------------------------------------ vendors

function buildVendors(payments) {
  const buckets = new Map();
  for (const p of payments) {
    if (!buckets.has(p.vendorKey)) {
      buckets.set(p.vendorKey, { vendorKey: p.vendorKey, rows: [], spellings: new Map() });
    }
    const b = buckets.get(p.vendorKey);
    b.rows.push(p);
    b.spellings.set(p.vendor, (b.spellings.get(p.vendor) || 0) + 1);
  }

  const vendors = [];
  for (const b of buckets.values()) {
    const rows = b.rows.slice().sort((a, x) => (a.day - x.day) || (a.line - x.line));
    const outflows = rows.filter((r) => !r.isRefund);
    const refunds = rows.filter((r) => r.isRefund);

    const grossPaid = round2(outflows.reduce((s, r) => s + r.amount, 0));
    const refundTotal = round2(refunds.reduce((s, r) => s + Math.abs(r.amount), 0));
    const net = round2(grossPaid - refundTotal);

    const amounts = outflows.map((r) => r.amount).sort((a, x) => a - x);
    const minPayment = amounts.length ? round2(amounts[0]) : 0;
    const maxPayment = amounts.length ? round2(amounts[amounts.length - 1]) : 0;
    const medianPayment = amounts.length ? round2(median(amounts)) : 0;

    // Gaps between consecutive OUTFLOW dates — the vendor's own rhythm.
    const outflowDays = outflows.map((r) => r.day);
    const gaps = [];
    for (let i = 1; i < outflowDays.length; i++) {
      const g = outflowDays[i] - outflowDays[i - 1];
      if (g > 0) gaps.push(g);
    }
    const gapsSorted = gaps.slice().sort((a, x) => a - x);
    const medianGapDays = gaps.length ? Math.round(median(gapsSorted)) : null;
    const cadenceKnown = outflows.length >= MIN_PAYMENTS_FOR_CADENCE && medianGapDays !== null && medianGapDays > 0;

    // Drift: first vs last outflow amount. Stated as arithmetic only.
    let driftAmount = null;
    let driftPct = null;
    if (outflows.length >= 2) {
      const first = outflows[0].amount;
      const last = outflows[outflows.length - 1].amount;
      driftAmount = round2(last - first);
      driftPct = first !== 0 ? round1(((last - first) / first) * 100) : null;
    }

    const months = new Set(rows.map((r) => r.month));
    const spellings = Array.from(b.spellings.entries())
      .sort((a, x) => (x[1] - a[1]) || a[0].localeCompare(x[0]))
      .map((e) => e[0]);

    const catCounts = new Map();
    for (const r of rows) {
      const c = r.category || '';
      if (!c) continue;
      catCounts.set(c, round2((catCounts.get(c) || 0) + Math.max(0, r.amount)));
    }
    const categories = Array.from(catCounts.entries())
      .sort((a, x) => (x[1] - a[1]) || a[0].localeCompare(x[0]))
      .map((e) => e[0]);

    vendors.push({
      vendorKey: b.vendorKey,
      label: spellings[0],
      spellings,
      spellingCount: spellings.length,
      paymentCount: outflows.length,
      refundCount: refunds.length,
      grossPaid,
      refundTotal,
      net,
      minPayment,
      medianPayment,
      maxPayment,
      firstPayment: rows[0].date,
      lastPayment: rows[rows.length - 1].date,
      lastPaymentDay: rows[rows.length - 1].day,
      monthsActive: months.size,
      medianGapDays: cadenceKnown ? medianGapDays : null,
      cadenceKnown,
      driftAmount,
      driftPct,
      categories,
      categoryCount: categories.length,
      rows,
    });
  }

  const totalNet = round2(vendors.reduce((s, v) => s + v.net, 0));
  vendors.sort((a, b) => (b.net - a.net) || a.label.localeCompare(b.label));
  vendors.forEach((v, i) => {
    v.rank = i + 1;
    v.netSharePct = shareOf(v.net, totalNet);
  });

  return { vendors, totalNet };
}

// ------------------------------------------------------------- dormancy pass

// A vendor is "quiet relative to its own rhythm" when the gap since its last
// payment exceeds DORMANCY_MULTIPLE x its own median gap. This is a statement
// about that vendor's observed pattern in this file — nothing more.
function markDormancy(vendors, lastDayInFile) {
  for (const v of vendors) {
    const daysSince = lastDayInFile - v.lastPaymentDay;
    v.daysSinceLastPayment = daysSince;
    if (!v.cadenceKnown) { v.quietVsOwnRhythm = false; v.dormancyRatio = null; continue; }
    const ratio = v.medianGapDays > 0 ? daysSince / v.medianGapDays : 0;
    v.dormancyRatio = round1(ratio);
    v.quietVsOwnRhythm = ratio >= DORMANCY_MULTIPLE;
  }
  return vendors;
}

// ------------------------------------------------------------------- monthly

function buildMonthly(payments, vendors) {
  const byMonth = new Map();
  for (const p of payments) {
    if (!byMonth.has(p.month)) byMonth.set(p.month, []);
    byMonth.get(p.month).push(p);
  }
  const keyToLabel = new Map(vendors.map((v) => [v.vendorKey, v.label]));

  const months = Array.from(byMonth.keys()).sort();
  return months.map((m) => {
    const rows = byMonth.get(m);
    const outflows = rows.filter((r) => !r.isRefund);
    const refunds = rows.filter((r) => r.isRefund);
    const gross = round2(outflows.reduce((s, r) => s + r.amount, 0));
    const refunded = round2(refunds.reduce((s, r) => s + Math.abs(r.amount), 0));

    const perVendor = new Map();
    for (const r of rows) {
      perVendor.set(r.vendorKey, round2((perVendor.get(r.vendorKey) || 0) + r.amount));
    }
    let topKey = null;
    let topVal = -Infinity;
    for (const [k, val] of Array.from(perVendor.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
      if (val > topVal) { topVal = val; topKey = k; }
    }

    return {
      month: m,
      grossPaid: gross,
      refunds: refunded,
      net: round2(gross - refunded),
      paymentCount: outflows.length,
      activeVendors: perVendor.size,
      topVendor: topKey ? keyToLabel.get(topKey) || topKey : '',
      topVendorNet: topKey ? round2(topVal) : 0,
    };
  });
}

// ---------------------------------------------------------------- categories

function buildCategories(payments, totalNet) {
  const byCat = new Map();
  let uncategorized = 0;
  for (const p of payments) {
    const c = (p.category || '').trim();
    if (!c) { uncategorized = round2(uncategorized + p.amount); continue; }
    byCat.set(c, round2((byCat.get(c) || 0) + p.amount));
  }
  const out = Array.from(byCat.entries())
    .map(([category, net]) => ({ category, net: round2(net), netSharePct: shareOf(net, totalNet) }))
    .sort((a, b) => (b.net - a.net) || a.category.localeCompare(b.category));
  if (uncategorized !== 0) {
    out.push({
      category: '(no category given)',
      net: round2(uncategorized),
      netSharePct: shareOf(uncategorized, totalNet),
    });
  }
  return out;
}

// ------------------------------------------------------------- concentration

// HHI on the standard 0-10,000 scale: the sum of squared percentage shares.
// Reported as a number with its scale stated. No threshold is applied and no
// judgement is attached to the value.
function buildConcentration(vendors, totalNet) {
  const positive = vendors.filter((v) => v.net > 0);
  const shares = positive.map((v) => (totalNet > 0 ? v.net / totalNet : 0));

  const hhi = round1(shares.reduce((s, x) => s + x * x, 0) * 10000);
  const effectiveVendorCount = hhi > 0 ? round1(10000 / hhi) : 0;

  const topShare = (n) => {
    const slice = positive.slice(0, n);
    return {
      vendors: slice.length,
      net: round2(slice.reduce((s, v) => s + v.net, 0)),
      sharePct: shareOf(slice.reduce((s, v) => s + v.net, 0), totalNet),
    };
  };

  const vendorsToReach = (target) => {
    let acc = 0;
    for (let i = 0; i < positive.length; i++) {
      acc += positive[i].net;
      if (totalNet > 0 && acc / totalNet >= target) return i + 1;
    }
    return positive.length;
  };

  return {
    vendorCount: vendors.length,
    payingVendorCount: positive.length,
    hhi,
    hhiScale: '0-10,000 (sum of squared percentage shares)',
    effectiveVendorCount,
    top1: topShare(1),
    top3: topShare(3),
    top5: topShare(5),
    top10: topShare(10),
    vendorsForHalfOfSpend: vendorsToReach(0.5),
    vendorsForEightyPctOfSpend: vendorsToReach(0.8),
  };
}

// ------------------------------------------------------------------ analyze

function analyzeSpend(payments, meta) {
  const info = meta || {};
  const { vendors, totalNet } = buildVendors(payments);
  const lastDay = payments.length ? payments[payments.length - 1].day : 0;
  markDormancy(vendors, lastDay);

  const grossPaid = round2(payments.filter((p) => !p.isRefund).reduce((s, p) => s + p.amount, 0));
  const refundTotal = round2(payments.filter((p) => p.isRefund).reduce((s, p) => s + Math.abs(p.amount), 0));

  const monthly = buildMonthly(payments, vendors);
  const categories = info.hasCategory ? buildCategories(payments, totalNet) : [];
  const concentration = buildConcentration(vendors, totalNet);

  const months = monthly.length;
  const spanDays = payments.length ? (payments[payments.length - 1].day - payments[0].day) + 1 : 0;

  const mergedVendors = vendors.filter((v) => v.spellingCount > 1);
  const quietVendors = vendors.filter((v) => v.quietVsOwnRhythm);
  const recurringVendors = vendors.filter((v) => v.cadenceKnown);

  return {
    vendors,
    monthly,
    categories,
    concentration,
    totals: {
      grossPaid,
      refundTotal,
      net: totalNet,
      paymentCount: payments.filter((p) => !p.isRefund).length,
      refundCount: payments.filter((p) => p.isRefund).length,
      rowCount: payments.length,
      averagePerMonth: months ? round2(totalNet / months) : 0,
      averagePayment: payments.filter((p) => !p.isRefund).length
        ? round2(grossPaid / payments.filter((p) => !p.isRefund).length)
        : 0,
    },
    window: {
      start: payments.length ? payments[0].date : null,
      end: payments.length ? payments[payments.length - 1].date : null,
      monthsObserved: months,
      spanDays,
    },
    flags: {
      mergedVendorCount: mergedVendors.length,
      quietVendorCount: quietVendors.length,
      recurringVendorCount: recurringVendors.length,
      hasCategory: !!info.hasCategory,
      vendorFromDescription: !!info.vendorFromDescription,
      amountMode: info.amountMode || 'single',
      currencies: info.currencies || [],
    },
  };
}

module.exports = {
  analyzeSpend, buildVendors, buildMonthly, buildCategories, buildConcentration,
  markDormancy, round2, round1, median, shareOf,
};
