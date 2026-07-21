// engine/summary.js
//
// HFF — Vendor Spend Rollup — factual summary assembly.
//
// Every sentence produced here is observational: "observed", "in this file",
// "recorded". The engine states what the payments in the file arithmetically
// produce; it never says a vendor is expensive or cheap, never calls spend
// wasteful, and never tells the reader what to cut or renegotiate.
//
// LINTING DESIGN (inherited from hff-client-concentration / hff-hourly-rate):
// notes that embed a vendor's name carry a parallel LINT-SAFE string in which
// the name is replaced by the token "<vendor>". The advice linter runs against
// those lint-safe strings, so the engine's own wording is fully guarded while a
// buyer whose vendor is literally named e.g. "Cut Costs Consulting" does not
// have their paid report withheld by a false positive on their own data.
'use strict';

const { DISCLAIMER, DORMANCY_MULTIPLE } = require('./constants');
const { round2 } = require('./spend');

function money(n) {
  const v = Number(n) || 0;
  return (v < 0 ? '-' : '') + '$' + Math.abs(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function pct(n) {
  return `${(Number(n) || 0).toFixed(1)}%`;
}

function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}

function noteBuilder() {
  const display = [];
  const lint = [];
  return {
    add(text, lintSafe) {
      display.push(text);
      lint.push(lintSafe === undefined ? text : lintSafe);
    },
    get display() { return display; },
    get lint() { return lint; },
  };
}

function buildSummary(analysis, opts) {
  const options = opts || {};
  const { totals, window, concentration, flags, vendors, monthly, categories } = analysis;
  const notes = noteBuilder();

  // --- coverage of the window
  notes.add(
    `This file records ${plural(totals.paymentCount, 'payment', 'payments')} to ` +
    `${plural(concentration.vendorCount, 'vendor', 'vendors')} between ${window.start} and ${window.end} ` +
    `(${plural(window.monthsObserved, 'calendar month', 'calendar months')}).`
  );

  // --- refunds disclosed, never silently netted
  if (totals.refundCount > 0) {
    notes.add(
      `${plural(totals.refundCount, 'row', 'rows')} carried a negative amount totalling ` +
      `${money(totals.refundTotal)}. Those are counted as credits against the vendor, so gross paid ` +
      `(${money(totals.grossPaid)}) and net (${money(totals.net)}) differ by exactly that figure.`
    );
  } else {
    notes.add(`No negative amounts appeared in this file, so gross paid and net are the same figure: ${money(totals.net)}.`);
  }

  // --- top vendor
  if (vendors.length) {
    const top = vendors[0];
    notes.add(
      `The largest single vendor bucket in this file is ${top.label} at ${money(top.net)} net, ` +
      `${pct(top.netSharePct)} of everything recorded, across ${plural(top.paymentCount, 'payment', 'payments')}.`,
      `The largest single vendor bucket in this file is <vendor> at ${money(top.net)} net, ` +
      `${pct(top.netSharePct)} of everything recorded, across ${plural(top.paymentCount, 'payment', 'payments')}.`
    );
  }

  // --- concentration, stated without judgement
  notes.add(
    `The first ${plural(concentration.vendorsForHalfOfSpend, 'vendor accounts', 'vendors account')} for the first ` +
    `50% of net spend, and ${plural(concentration.vendorsForEightyPctOfSpend, 'vendor accounts', 'vendors account')} ` +
    `for the first 80%. HHI on the 0-10,000 scale comes out to ${concentration.hhi}, ` +
    `an effective vendor count of ${concentration.effectiveVendorCount}. These are arithmetic descriptions of the ` +
    `distribution in this file, with no threshold applied.`
  );

  // --- cadence
  if (flags.recurringVendorCount > 0) {
    notes.add(
      `${plural(flags.recurringVendorCount, 'vendor was', 'vendors were')} paid at least three times, so a median ` +
      `gap between payments could be measured for ${flags.recurringVendorCount === 1 ? 'it' : 'them'}. ` +
      `That gap is reported per vendor on the Vendors sheet.`
    );
  } else {
    notes.add('No vendor was paid three or more times in this file, so no payment cadence could be measured.');
  }

  // --- dormancy against own rhythm
  if (flags.quietVendorCount > 0) {
    const quiet = vendors.filter((v) => v.quietVsOwnRhythm).slice(0, 3);
    const names = quiet.map((v) => v.label).join(', ');
    notes.add(
      `${plural(flags.quietVendorCount, 'vendor has', 'vendors have')} gone at least ` +
      `${DORMANCY_MULTIPLE}x their own median gap since their last payment in this file` +
      `${names ? ` (for example: ${names})` : ''}. That is a statement about the pattern in this file only — ` +
      `the file may simply end before the next payment.`,
      `${plural(flags.quietVendorCount, 'vendor has', 'vendors have')} gone at least ` +
      `${DORMANCY_MULTIPLE}x their own median gap since their last payment in this file (for example: <vendor>). ` +
      `That is a statement about the pattern in this file only — the file may simply end before the next payment.`
    );
  }

  // --- amount drift, arithmetic only
  const drifters = vendors
    .filter((v) => v.driftPct !== null && Math.abs(v.driftPct) >= 10 && v.paymentCount >= 2)
    .sort((a, b) => Math.abs(b.driftPct) - Math.abs(a.driftPct))
    .slice(0, 3);
  if (drifters.length) {
    const d = drifters[0];
    notes.add(
      `For ${plural(drifters.length, 'vendor', 'vendors')} the last recorded payment differs from the first by ` +
      `10% or more. The largest is ${d.label}: ${money(d.rows.filter((r) => !r.isRefund)[0].amount)} first, ` +
      `${money(d.rows.filter((r) => !r.isRefund).slice(-1)[0].amount)} last (${d.driftPct > 0 ? '+' : ''}${d.driftPct}%). ` +
      `This is the arithmetic difference between two rows, not a price analysis.`,
      `For ${plural(drifters.length, 'vendor', 'vendors')} the last recorded payment differs from the first by ` +
      `10% or more. The largest is <vendor>. This is the arithmetic difference between two rows, not a price analysis.`
    );
  }

  // --- categories
  if (flags.hasCategory && categories.length) {
    const topCat = categories[0];
    notes.add(
      `The file carries a category column. The largest category by net spend is "${topCat.category}" at ` +
      `${money(topCat.net)} (${pct(topCat.netSharePct)}), across ${plural(categories.length, 'category', 'categories')} in total. ` +
      `Categories are reproduced exactly as the file labelled them.`,
      `The file carries a category column. The largest category by net spend is <vendor> at ` +
      `${money(topCat.net)} (${pct(topCat.netSharePct)}), across ${plural(categories.length, 'category', 'categories')} in total. ` +
      `Categories are reproduced exactly as the file labelled them.`
    );
  } else {
    notes.add('This file has no category column, so no category rollup could be produced.');
  }

  // --- monthly shape
  if (monthly.length >= 2) {
    const sorted = monthly.slice().sort((a, b) => b.net - a.net);
    const hi = sorted[0];
    const lo = sorted[sorted.length - 1];
    notes.add(
      `Monthly net spend ranges from ${money(lo.net)} in ${lo.month} to ${money(hi.net)} in ${hi.month}, ` +
      `averaging ${money(totals.averagePerMonth)} across the ${window.monthsObserved} months observed.`
    );
  }

  // --- grouping transparency
  if (flags.mergedVendorCount > 0) {
    notes.add(
      `${plural(flags.mergedVendorCount, 'vendor bucket', 'vendor buckets')} merged more than one spelling from the ` +
      `file (for example a corporate suffix or a card-processor prefix). Every merged spelling is listed on the ` +
      `Vendors sheet so you can confirm the grouping. This is string matching only — there is no vendor database behind it.`
    );
  }

  if (flags.vendorFromDescription) {
    notes.add(
      'This file had no dedicated vendor column, so the description column was read as the vendor name. ' +
      'Bank-style descriptions often carry processor prefixes and store numbers; those are stripped from the ' +
      'grouping key only, and the label always shows what the file said.'
    );
  }

  if (flags.amountMode === 'debit_credit') {
    notes.add(
      'This file used separate debit and credit columns rather than one signed amount column. ' +
      'Debits were read as money paid out and credits as money returned.'
    );
  }

  if (flags.currencies.length > 1) {
    notes.add(
      `The currency column names more than one currency (${flags.currencies.join(', ')}). ` +
      `The engine does NOT convert currencies — every total here is a plain sum of the numbers as written, ` +
      `so mixed-currency totals are not meaningful. Filter to one currency before relying on any total.`
    );
  }

  const skippedCount = options.skippedCount || 0;
  if (skippedCount > 0) {
    notes.add(
      `${plural(skippedCount, 'row was', 'rows were')} flagged as unreadable and left out of every figure above. ` +
      `Each one is listed with its CSV line number and the reason on the Flagged Rows sheet.`
    );
  } else {
    notes.add('Every data row in the file was read successfully; nothing was left out.');
  }

  return {
    counts: {
      vendors: concentration.vendorCount,
      payments: totals.paymentCount,
      refunds: totals.refundCount,
      monthsObserved: window.monthsObserved,
      categories: categories.length,
      skippedRows: skippedCount,
      mergedVendors: flags.mergedVendorCount,
      quietVendors: flags.quietVendorCount,
      recurringVendors: flags.recurringVendorCount,
    },
    spend: {
      grossPaid: totals.grossPaid,
      refundTotal: totals.refundTotal,
      net: totals.net,
      averagePerMonth: totals.averagePerMonth,
      averagePayment: totals.averagePayment,
    },
    concentration: {
      hhi: concentration.hhi,
      hhiScale: concentration.hhiScale,
      effectiveVendorCount: concentration.effectiveVendorCount,
      top1SharePct: concentration.top1.sharePct,
      top3SharePct: concentration.top3.sharePct,
      top5SharePct: concentration.top5.sharePct,
      top10SharePct: concentration.top10.sharePct,
      vendorsForHalfOfSpend: concentration.vendorsForHalfOfSpend,
      vendorsForEightyPctOfSpend: concentration.vendorsForEightyPctOfSpend,
    },
    window,
    topVendor: vendors.length
      ? { label: vendors[0].label, net: vendors[0].net, sharePct: vendors[0].netSharePct }
      : null,
    currencies: flags.currencies,
    notes: notes.display,
    lintNotes: notes.lint,
    disclaimer: DISCLAIMER,
  };
}

// Strings handed to the advice linter. Vendor-name-bearing notes are replaced
// by their lint-safe twins so buyer data cannot trip the guardrail.
function summaryStrings(summary) {
  return [].concat(summary.lintNotes, [summary.disclaimer]);
}

module.exports = { buildSummary, summaryStrings, money, pct, plural, round2 };
