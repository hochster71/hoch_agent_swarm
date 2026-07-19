// engine/summary.js
//
// HFF — Client Revenue Concentration Report — factual summary assembly.
//
// Every sentence produced here is observational: "observed", "in this file",
// "accounts for". The engine states how revenue is distributed; it never says
// whether that distribution is good or bad, and never tells the reader what to
// do about it.
//
// LINTING DESIGN (improves on the sibling HFF products):
// notes that embed a client's name carry a parallel LINT-SAFE string in which
// the name is replaced by the token "<client>". The advice linter runs against
// those lint-safe strings, so:
//   * the engine's own wording is still fully guarded, AND
//   * a buyer whose client is literally called "Good Client LLC" or
//     "We Recommend Ltd" does not have their paid report withheld by a false
//     positive on their own data.
'use strict';

const { DISCLAIMER } = require('./constants');
const { round2 } = require('./concentration');

function money(n) {
  const v = Number(n) || 0;
  return (v < 0 ? '-' : '') + '$' + Math.abs(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function pct(n) {
  return `${(Number(n) || 0).toFixed(1)}%`;
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

function buildSummary(analysis, meta) {
  const { clients, metrics, totals, monthly, window, paymentTiming } = analysis;
  const top = clients.filter((c) => c.net > 0);

  const headline = [
    `${money(totals.net)} of net revenue is observed in this file across ${analysis.clientCount} named client(s).`,
    `Observed window: ${window.start} to ${window.end} (${window.months} calendar month(s)).`,
    `Share figures below are computed over the ${money(totals.netPositiveOnly)} contributed by the ` +
    `${metrics.contributingClients} client(s) that net above zero. The largest of those accounts for ` +
    `${pct(metrics.top1SharePct)}; the top three account for ${pct(metrics.top3SharePct)}.`,
  ];

  const nb = noteBuilder();

  if (metrics.clientsToReachHalf !== null) {
    nb.add(
      `${metrics.clientsToReachHalf} client(s) make up the first half of net revenue in this file; ` +
      `${metrics.clientsToReachEighty === null ? 'no subset reaches' : metrics.clientsToReachEighty + ' make up'} the first 80%.`
    );
  }

  nb.add(
    `Effective client count is ${metrics.effectiveClientCount} — that is the number of equal-sized clients ` +
    `that would produce the same distribution as the ${metrics.contributingClients} actually observed. ` +
    `The HHI for this file is ${metrics.hhi} on a 0–10,000 scale, where 10,000 would mean every dollar came from one client.`
  );

  // Concentration statement is purely arithmetic — no adjective attached.
  if (top.length) {
    const t = top[0];
    nb.add(
      `${t.label} is the largest client in this file: ${money(t.net)} net across ${t.invoiceCount} invoice(s), ` +
      `${pct(t.sharePct)} of observed net revenue, first seen ${t.firstInvoice}, last seen ${t.lastInvoice}.`,
      `<client> is the largest client in this file: ${money(t.net)} net across ${t.invoiceCount} invoice(s), ` +
      `${pct(t.sharePct)} of observed net revenue, first seen ${t.firstInvoice}, last seen ${t.lastInvoice}.`
    );
  }

  for (const c of analysis.dormant) {
    nb.add(
      `${c.label}: last invoice ${c.lastInvoice}, which is ${c.daysSinceLastInvoice} day(s) before the end of the window — ` +
      `longer than ${analysis.options.dormancyMultiple}x this client's own median gap of about ${c.medianGapDays} day(s) between invoices.`,
      `<client>: last invoice ${c.lastInvoice}, which is ${c.daysSinceLastInvoice} day(s) before the end of the window — ` +
      `longer than ${analysis.options.dormancyMultiple}x this client's own median gap of about ${c.medianGapDays} day(s) between invoices.`
    );
  }

  if (analysis.newClients.length) {
    nb.add(
      `${analysis.newClients.length} client(s) first appear within the last ` +
      `${analysis.options.newClientWindowDays} day(s) of the observed window.`
    );
  }

  for (const c of analysis.mergedSpellings) {
    nb.add(
      `${c.label}: ${c.spellingCount} different spellings in this file were grouped into one client ` +
      `(${c.spellings.join(' / ')}). Grouping is string-based only.`,
      `<client>: ${c.spellingCount} different spellings in this file were grouped into one client. ` +
      `Grouping is string-based only.`
    );
  }

  if (monthly.length >= 2) {
    const sorted = monthly.slice().sort((a, b) => b.net - a.net);
    nb.add(
      `Highest observed month: ${sorted[0].month} at ${money(sorted[0].net)} net across ` +
      `${sorted[0].activeClients} client(s). Lowest: ${sorted[sorted.length - 1].month} at ` +
      `${money(sorted[sorted.length - 1].net)}.`
    );
  }

  if (paymentTiming.available) {
    nb.add(
      `A paid-date column was present on ${paymentTiming.rowsWithPaidDate} row(s). ` +
      `Median observed time from invoice date to paid date is ${paymentTiming.medianDaysToPay} day(s); ` +
      `the longest observed is ${paymentTiming.slowestDaysToPay} day(s).`
    );
  } else {
    nb.add('No paid-date column was found, so this report contains no payment-timing figures.');
  }

  if (totals.creditRows > 0) {
    nb.add(
      `${totals.creditRows} row(s) carried a negative amount (credits or refunds) totalling ` +
      `${money(totals.credits)}. They were netted against the client they name, not discarded.`
    );
  }

  if (analysis.netNegativeClients.length) {
    nb.add(
      `${analysis.netNegativeClients.length} client(s) net to zero or below in this file and are therefore ` +
      `excluded from the share and concentration figures. They are still listed on the Clients sheet.`
    );
  }

  if ((meta && meta.skippedCount) > 0) {
    nb.add(
      `${meta.skippedCount} row(s) could not be read and are listed on the "Flagged Rows" sheet. ` +
      `They were not counted anywhere in this report.`
    );
  }

  return {
    generated: true,
    counts: {
      clients: analysis.clientCount,
      contributingClients: metrics.contributingClients,
      invoiceRows: totals.invoiceRows,
      creditRows: totals.creditRows,
      skippedRows: (meta && meta.skippedCount) || 0,
      monthsObserved: window.months,
      dormantClients: analysis.dormant.length,
      newClients: analysis.newClients.length,
    },
    totals: {
      gross: totals.gross,
      credits: totals.credits,
      net: totals.net,
      averagePerClient: metrics.contributingClients
        ? round2(totals.netPositiveOnly / metrics.contributingClients)
        : 0,
    },
    concentration: {
      top1SharePct: metrics.top1SharePct,
      top3SharePct: metrics.top3SharePct,
      top5SharePct: metrics.top5SharePct,
      top10SharePct: metrics.top10SharePct,
      hhi: metrics.hhi,
      effectiveClientCount: metrics.effectiveClientCount,
      clientsToReachHalf: metrics.clientsToReachHalf,
      clientsToReachEighty: metrics.clientsToReachEighty,
    },
    paymentTiming,
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

module.exports = { buildSummary, summaryStrings, money, pct };
