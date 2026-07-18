// engine/summary.js
//
// HFF — Recurring Charge Finder — factual summary assembly.
//
// Every string produced here is passed through the advice linter before any
// artifact is released. Language is deliberately observational: "observed",
// "in this file", "at the observed cadence" — never "you should".
'use strict';

const { DISCLAIMER } = require('./constants');
const { round2 } = require('./recurring');

function money(n) {
  const v = Number(n) || 0;
  return (v < 0 ? '-' : '') + '$' + Math.abs(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function buildSummary(detection, meta) {
  const rec = detection.recurring;
  const totalAnnualized = round2(rec.reduce((s, r) => s + r.annualizedAmount, 0));
  const totalMonthly = round2(rec.reduce((s, r) => s + r.monthlyEquivalent, 0));

  const byCadence = {};
  for (const r of rec) {
    byCadence[r.cadence] = byCadence[r.cadence] || { count: 0, annualized: 0 };
    byCadence[r.cadence].count += 1;
    byCadence[r.cadence].annualized = round2(byCadence[r.cadence].annualized + r.annualizedAmount);
  }

  const byConfidence = { high: 0, medium: 0, low: 0 };
  for (const r of rec) byConfidence[r.confidence] += 1;

  const changed = rec.filter((r) => r.amountChanged);
  const dormant = rec.filter((r) => r.noChargeSinceExpected);

  const headline = [
    `${rec.length} recurring charge pattern(s) observed across ${detection.chargeCount} charge row(s).`,
    `Observed window: ${detection.windowStart || 'n/a'} to ${detection.windowEnd || 'n/a'}.`,
    `Combined cost at the observed cadence: ${money(totalMonthly)} per month / ${money(totalAnnualized)} per year.`,
  ];

  const notes = [];
  if (byConfidence.low > 0) {
    notes.push(`${byConfidence.low} pattern(s) are marked low confidence — the interval or amount varied enough that the cadence is uncertain.`);
  }
  for (const r of changed) {
    const dir = r.amountChangePct > 0 ? 'higher' : 'lower';
    notes.push(`${r.label}: latest charge ${money(r.latestAmount)} is ${Math.abs(r.amountChangePct).toFixed(1)}% ${dir} than the first observed charge ${money(r.firstAmount)}.`);
  }
  for (const r of dormant) {
    notes.push(`${r.label}: last observed ${r.lastSeen}, which is ${r.daysSinceLastSeen} day(s) ago — longer than the observed ${r.cadence} cadence of about ${r.medianIntervalDays} day(s).`);
  }
  for (const o of detection.overlaps) {
    notes.push(`Observation: ${o.count} distinct merchants in this file carry the "${o.tag}" tag (${o.merchants.join(', ')}), totalling ${money(o.combinedAnnualized)} per year at the observed cadence.`);
  }
  if ((meta && meta.skippedCount) > 0) {
    notes.push(`${meta.skippedCount} row(s) could not be read and are listed on the "Flagged Rows" sheet. They were not counted anywhere in this report.`);
  }
  if (detection.creditCount > 0) {
    notes.push(`${detection.creditCount} row(s) had the opposite sign to the file's dominant charge direction (refunds or credits) and were excluded from recurrence detection.`);
  }

  return {
    generated: true,
    counts: {
      recurringPatterns: rec.length,
      oneOffMerchants: detection.oneOff.length,
      chargeRows: detection.chargeCount,
      creditRows: detection.creditCount,
      skippedRows: (meta && meta.skippedCount) || 0,
    },
    totals: { monthlyEquivalent: totalMonthly, annualized: totalAnnualized },
    byCadence,
    byConfidence,
    amountChanges: changed.length,
    dormantPatterns: dormant.length,
    overlaps: detection.overlaps,
    window: { start: detection.windowStart, end: detection.windowEnd },
    headline,
    notes,
    disclaimer: DISCLAIMER,
  };
}

// Every user-visible string, flattened, for the advice linter.
function summaryStrings(summary, detection) {
  const out = [];
  out.push(...summary.headline, ...summary.notes, summary.disclaimer);
  for (const r of detection.recurring) out.push(r.label, r.cadence, r.confidence);
  for (const o of detection.oneOff) out.push(o.label);
  return out;
}

module.exports = { buildSummary, summaryStrings, money };
