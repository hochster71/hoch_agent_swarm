// engine/summary.js
//
// HFF — Effective Hourly Rate Report — factual summary assembly.
//
// Every sentence produced here is observational: "observed", "in this file",
// "come out to". The engine states what the hours and billing figures in the
// file arithmetically produce; it never says whether a rate is good or bad,
// never compares it to a market, and never tells the reader what to charge.
//
// LINTING DESIGN (inherited from hff-client-concentration): notes that embed a
// client's name carry a parallel LINT-SAFE string in which the name is replaced
// by the token "<client>". The advice linter runs against those lint-safe
// strings, so the engine's own wording is fully guarded while a buyer whose
// client is literally named e.g. "Charge More LLC" does not have their paid
// report withheld by a false positive on their own data.
'use strict';

const { DISCLAIMER } = require('./constants');
const { round2 } = require('./rates');

function money(n) {
  const v = Number(n) || 0;
  return (v < 0 ? '-' : '') + '$' + Math.abs(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function pct(n) {
  return `${(Number(n) || 0).toFixed(1)}%`;
}

function hrs(n) {
  return `${(Number(n) || 0).toFixed(2).replace(/\.00$/, '')} hour(s)`;
}

function noteBuilder() {
  const display = [];
  const lint = [];
  return {
    add(text, lintSafe) {
      display.push(text);
      lint.push(lintSafe === undefined ? text : lintSafe);
    },
    display,
    lint,
  };
}

function buildSummary(analysis, extra) {
  const { totals, rates, billableShare, window, clients, monthly, weekdays, meta } = analysis;

  const headline = [
    `${hrs(totals.hours)} across ${analysis.clientCount} named client(s) and ${totals.entries} time ` +
    `entr${totals.entries === 1 ? 'y' : 'ies'} are observed in this file, spread over ${totals.trackedDays} tracked day(s).`,
    `Observed window: ${window.start} to ${window.end} (${window.months} calendar month(s)).`,
  ];

  if (rates.available) {
    headline.push(
      `Billing figures are present on ${totals.pricedEntries} entr${totals.pricedEntries === 1 ? 'y' : 'ies'} ` +
      `covering ${hrs(totals.coveredHours)} (${pct(rates.coveragePctOfHours)} of tracked hours). Those figures total ` +
      `${money(totals.revenue)} — an observed ${money(rates.effectiveRateCovered)} per covered hour, and ` +
      `${money(rates.blendedRateAllHours)} blended across every tracked hour in the file.`
    );
  } else {
    headline.push(
      'No positive billing figures (amount or rate columns) were found, so this report contains hour ' +
      'figures only and no rate figures.'
    );
  }

  const nb = noteBuilder();

  if (clients.length) {
    const t = clients[0];
    nb.add(
      `${t.label} accounts for the most tracked time in this file: ${hrs(t.hours)} (${pct(t.hoursSharePct)} of all ` +
      `tracked hours) across ${t.entryCount} entr${t.entryCount === 1 ? 'y' : 'ies'}, first seen ${t.firstEntry}, ` +
      `last seen ${t.lastEntry}.`,
      `<client> accounts for the most tracked time in this file: ${hrs(t.hours)} (${pct(t.hoursSharePct)} of all ` +
      `tracked hours) across ${t.entryCount} entr${t.entryCount === 1 ? 'y' : 'ies'}, first seen ${t.firstEntry}, ` +
      `last seen ${t.lastEntry}.`
    );
  }

  if (rates.available) {
    const rated = clients.filter((c) => c.effectiveRateCovered !== null);
    if (rated.length >= 2) {
      const sorted = rated.slice().sort((a, b) => b.effectiveRateCovered - a.effectiveRateCovered);
      const hi = sorted[0];
      const lo = sorted[sorted.length - 1];
      nb.add(
        `Observed per-covered-hour rates span ${money(lo.effectiveRateCovered)} (${lo.label}) to ` +
        `${money(hi.effectiveRateCovered)} (${hi.label}) across the ${rated.length} client(s) with billing figures.`,
        `Observed per-covered-hour rates span ${money(lo.effectiveRateCovered)} (<client>) to ` +
        `${money(hi.effectiveRateCovered)} (<client>) across the ${rated.length} client(s) with billing figures.`
      );
    }
    if (rates.coveragePctOfHours < 100) {
      nb.add(
        `${pct(100 - rates.coveragePctOfHours)} of tracked hours carry no billing figure in this file. ` +
        'The per-covered-hour rate excludes those hours; the blended rate includes them.'
      );
    }
    if (totals.derivedFromRateCount > 0) {
      nb.add(
        `${totals.derivedFromRateCount} entr${totals.derivedFromRateCount === 1 ? 'y' : 'ies'} carried an hourly-rate ` +
        'column but no amount; their figures were computed as rate x hours from the file\'s own columns.'
      );
    }
  }

  if (billableShare.available) {
    nb.add(
      `Of the ${hrs(totals.knownFlagHours)} with a readable billable flag, ${hrs(totals.billableHours)} ` +
      `(${pct(billableShare.billableSharePct)}) are marked billable and ${hrs(totals.nonBillableHours)} are marked non-billable.`
    );
    if (totals.unknownBillableHours > 0) {
      nb.add(
        `${hrs(totals.unknownBillableHours)} carry a billable flag the engine could not read; ` +
        'they are counted in total hours but excluded from the billable-share figure.'
      );
    }
  } else if (meta.hasBillable) {
    nb.add('A billable column exists but no row carried a readable flag, so no billable-share figure is reported.');
  } else {
    nb.add('No billable column was found, so this report contains no billable-share figure.');
  }

  if (monthly.length >= 2) {
    const sorted = monthly.slice().sort((a, b) => b.hours - a.hours);
    nb.add(
      `Most-tracked month: ${sorted[0].month} at ${hrs(sorted[0].hours)} across ${sorted[0].activeClients} client(s). ` +
      `Least: ${sorted[sorted.length - 1].month} at ${hrs(sorted[sorted.length - 1].hours)}.`
    );
  }

  const busiest = weekdays.slice().sort((a, b) => b.hours - a.hours)[0];
  if (busiest && busiest.hours > 0) {
    nb.add(`${busiest.weekday} carries the most tracked time in this file: ${hrs(busiest.hours)}.`);
  }

  for (const c of analysis.mergedSpellings) {
    nb.add(
      `${c.label}: ${c.spellingCount} different spellings in this file were grouped into one client ` +
      `(${c.spellings.join(' / ')}). Grouping is string-based only.`,
      `<client>: ${c.spellingCount} different spellings in this file were grouped into one client. ` +
      'Grouping is string-based only.'
    );
  }

  if (meta.negativeAmountsIgnored > 0) {
    nb.add(
      `${meta.negativeAmountsIgnored} row(s) carried a negative billed amount. The hours were counted; ` +
      'the negative figures were left out of every revenue and rate calculation, because a negative billed ' +
      'amount on a time entry has no single deterministic reading.'
    );
  }

  if ((extra && extra.skippedCount) > 0) {
    nb.add(
      `${extra.skippedCount} row(s) could not be read and are listed on the "Flagged Rows" sheet. ` +
      'They were not counted anywhere in this report.'
    );
  }

  return {
    generated: true,
    counts: {
      clients: analysis.clientCount,
      entries: totals.entries,
      pricedEntries: totals.pricedEntries,
      skippedRows: (extra && extra.skippedCount) || 0,
      monthsObserved: window.months,
      trackedDays: totals.trackedDays,
    },
    hours: {
      total: totals.hours,
      billable: totals.billableHours,
      nonBillable: totals.nonBillableHours,
      unknownFlag: totals.unknownBillableHours,
      covered: totals.coveredHours,
    },
    revenue: {
      total: totals.revenue,
      averagePerTrackedDay: totals.trackedDays ? round2(totals.revenue / totals.trackedDays) : 0,
    },
    rates: {
      available: rates.available,
      effectiveRateCovered: rates.effectiveRateCovered,
      blendedRateAllHours: rates.blendedRateAllHours,
      coveragePctOfHours: rates.coveragePctOfHours,
    },
    billableShare,
    window,
    headline,
    notes: nb.display,
    lintableNotes: nb.lint,
    disclaimer: DISCLAIMER,
  };
}

// Every ENGINE-AUTHORED string, flattened, for the advice linter. Client names
// echoed from the buyer's file are deliberately excluded — see the note at the
// top of this file.
function summaryStrings(summary) {
  return [...summary.headline, ...summary.lintableNotes, summary.disclaimer];
}

module.exports = { buildSummary, summaryStrings, money, pct, hrs };
