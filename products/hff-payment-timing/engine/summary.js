// engine/summary.js
//
// HFF — Getting-Paid Speed Report — factual summary assembly.
//
// Every sentence produced here is observational: "observed", "in this file",
// "recorded". The engine states what the invoices in the file arithmetically
// produce; it never tells the reader to chase a client, add a fee, or drop a
// client, and it never judges a client.
//
// LINTING DESIGN (inherited from hff-vendor-spend / hff-hourly-rate): notes that
// embed a client's name carry a parallel LINT-SAFE string in which the name is
// replaced by the token "<client>". The advice linter runs against those
// lint-safe strings, so the engine's own wording is fully guarded while a buyer
// whose client is literally named e.g. "Chase Them Consulting" does not have
// their paid report withheld by a false positive on their own data.
'use strict';

const { DISCLAIMER, DEFAULT_NET_DAYS } = require('./constants');
const { round2 } = require('./timing');

function money(n) {
  const v = Number(n) || 0;
  return (v < 0 ? '-' : '') + '$' + Math.abs(v).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
function pct(n) {
  if (n === null || n === undefined) return 'n/a';
  return `${(Number(n) || 0).toFixed(1)}%`;
}
function days(n) {
  if (n === null || n === undefined) return 'n/a';
  const v = Number(n);
  const s = Number.isInteger(v) ? String(v) : v.toFixed(1);
  return `${s} ${Math.abs(v) === 1 ? 'day' : 'days'}`;
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
  const { totals, window, concentration, dueBasisMix, flags, clients, monthly } = analysis;
  const notes = noteBuilder();

  // --- coverage of the window
  notes.add(
    `This file records ${plural(totals.invoiceCount, 'invoice', 'invoices')} to ` +
    `${plural(concentration.clientCount, 'client', 'clients')} issued between ${window.start} and ${window.end} ` +
    `(${plural(window.monthsObserved, 'calendar month', 'calendar months')}). ` +
    `${plural(totals.paidCount, 'invoice carries', 'invoices carry')} a paid date; ` +
    `${plural(totals.openCount, 'is', 'are')} still open.`
  );

  // --- speed headline
  if (totals.paidCount > 0) {
    notes.add(
      `Across the ${plural(totals.paidCount, 'paid invoice', 'paid invoices')}, the median time from issue to ` +
      `payment was ${days(totals.medianDaysToPay)} (mean ${days(totals.meanDaysToPay)}); the fastest was ` +
      `${days(totals.fastestDaysToPay)} and the slowest ${days(totals.slowestDaysToPay)}.`
    );
  } else {
    notes.add(
      'No invoice in this file carries a paid date, so no payment speed could be measured. ' +
      'Every invoice is treated as still open.'
    );
  }

  // --- on-time share
  if (totals.paidCount > 0) {
    notes.add(
      `${pct(totals.onTimePct)} of the paid invoices were paid on or before their due date; the rest were paid ` +
      `after it. On-time is measured per invoice against that invoice's own due basis.`
    );
  }

  // --- due-basis transparency
  notes.add(
    `Due dates came from a due-date column for ${plural(dueBasisMix.due_column, 'invoice', 'invoices')}, from ` +
    `parseable terms for ${plural(dueBasisMix.terms, 'invoice', 'invoices')}, and from an assumed net-${DEFAULT_NET_DAYS} ` +
    `for ${plural(dueBasisMix.assumed_net_30, 'invoice', 'invoices')}` +
    `${dueBasisMix.assumed_net_30 > 0 ? ' (the file gave no due date or terms for those, so the assumption is disclosed here)' : ''}.`
  );

  // --- outstanding
  if (totals.openCount > 0) {
    notes.add(
      `${plural(totals.openCount, 'invoice is', 'invoices are')} still open, totalling ${money(totals.outstanding)}. ` +
      `Of those, ${plural(totals.overdueOpenCount, 'is', 'are')} past the due date on file (totalling ` +
      `${money(totals.overdueOpenTotal)}), and the oldest open invoice was issued ${days(totals.oldestOpenAgeDays)} ` +
      `before ${window.asOf}, the latest date in the file. "Past the due date" is arithmetic against the due basis above.`
    );
  } else {
    notes.add('Every invoice in this file carries a paid date; nothing is left open.');
  }

  // --- top client by billed
  if (clients.length) {
    const top = clients[0];
    notes.add(
      `The largest client by amount billed in this file is ${top.label} at ${money(top.billed)} ` +
      `(${pct(top.billedSharePct)} of everything recorded), across ${plural(top.invoiceCount, 'invoice', 'invoices')}.`,
      `The largest client by amount billed in this file is <client> at ${money(top.billed)} ` +
      `(${pct(top.billedSharePct)} of everything recorded), across ${plural(top.invoiceCount, 'invoice', 'invoices')}.`
    );
  }

  // --- concentration, stated without judgement
  notes.add(
    `HHI over billed amount on the 0-10,000 scale comes out to ${concentration.hhi}, an effective client count of ` +
    `${concentration.effectiveClientCount}. The single largest client is ${pct(concentration.top1.sharePct)} of billed ` +
    `and the top ${concentration.top3.clients} are ${pct(concentration.top3.sharePct)}. These are arithmetic ` +
    `descriptions of the distribution in this file, with no threshold applied.`
  );

  // --- slowest-median client, factual only
  const paidClients = clients.filter((c) => c.paidCount > 0 && c.medianDaysToPay !== null);
  if (paidClients.length && clients.length > 1) {
    const slow = paidClients.slice().sort(
      (a, b) => (b.medianDaysToPay - a.medianDaysToPay) || a.label.localeCompare(b.label)
    )[0];
    notes.add(
      `The client with the longest median time-to-payment in this file is ${slow.label} at ` +
      `${days(slow.medianDaysToPay)} across ${plural(slow.paidCount, 'paid invoice', 'paid invoices')}. ` +
      `This is the arithmetic median of that client's own paid invoices, not a judgement about the client.`,
      `The client with the longest median time-to-payment in this file is <client> at ` +
      `${days(slow.medianDaysToPay)} across ${plural(slow.paidCount, 'paid invoice', 'paid invoices')}. ` +
      `This is the arithmetic median of that client's own paid invoices, not a judgement about the client.`
    );
  }

  // --- monthly shape
  if (monthly.length >= 2) {
    const withMedian = monthly.filter((m) => m.medianDaysToPay !== null);
    if (withMedian.length >= 2) {
      const sorted = withMedian.slice().sort((a, b) => a.medianDaysToPay - b.medianDaysToPay);
      const fast = sorted[0];
      const slow = sorted[sorted.length - 1];
      notes.add(
        `By issue month, the median time-to-payment for paid invoices ranges from ${days(fast.medianDaysToPay)} ` +
        `(invoices issued ${fast.month}) to ${days(slow.medianDaysToPay)} (issued ${slow.month}). ` +
        `Each month covers only the invoices issued in it that were later paid.`
      );
    }
  }

  // --- grouping transparency
  if (flags.mergedClientCount > 0) {
    notes.add(
      `${plural(flags.mergedClientCount, 'client bucket', 'client buckets')} merged more than one spelling from the ` +
      `file (for example a corporate suffix). Every merged spelling is listed on the Clients sheet so you can confirm ` +
      `the grouping. This is string matching only — there is no client database behind it.`
    );
  }

  if (flags.clientFromName) {
    notes.add(
      'This file had no dedicated client column, so a "name" column was read as the client. ' +
      'Confirm the grouping on the Clients sheet.'
    );
  }

  if (flags.creditNoteCount > 0) {
    notes.add(
      `${plural(flags.creditNoteCount, 'row carried', 'rows carried')} a negative amount totalling ` +
      `${money(flags.creditNoteTotal)}. Those are treated as credit notes, listed on the Flagged Rows sheet, and ` +
      `kept out of every invoice-timing figure above — they are not invoices awaiting payment.`
    );
  }

  if (flags.currencies.length > 1) {
    notes.add(
      `The currency column names more than one currency (${flags.currencies.join(', ')}). ` +
      `The engine does NOT convert currencies — every money total here is a plain sum of the numbers as written, ` +
      `so mixed-currency totals are not meaningful. Filter to one currency before relying on any total.`
    );
  }

  const skippedCount = options.skippedCount || 0;
  const nonCredit = skippedCount - (flags.creditNoteCount || 0);
  if (nonCredit > 0) {
    notes.add(
      `${plural(nonCredit, 'row was', 'rows were')} flagged as unreadable and left out of every figure above. ` +
      `Each one is listed with its CSV line number and the reason on the Flagged Rows sheet.`
    );
  } else if (skippedCount === 0) {
    notes.add('Every data row in the file was read successfully; nothing was left out.');
  }

  return {
    counts: {
      clients: concentration.clientCount,
      invoices: totals.invoiceCount,
      paid: totals.paidCount,
      open: totals.openCount,
      monthsObserved: window.monthsObserved,
      skippedRows: skippedCount,
      mergedClients: flags.mergedClientCount,
      overdueOpen: totals.overdueOpenCount,
    },
    timing: {
      billed: totals.billed,
      paidBilled: totals.paidBilled,
      outstanding: totals.outstanding,
      medianDaysToPay: totals.medianDaysToPay,
      meanDaysToPay: totals.meanDaysToPay,
      fastestDaysToPay: totals.fastestDaysToPay,
      slowestDaysToPay: totals.slowestDaysToPay,
      onTimePct: totals.onTimePct,
      pctPaidByCount: totals.pctPaidByCount,
      pctPaidByValue: totals.pctPaidByValue,
      oldestOpenAgeDays: totals.oldestOpenAgeDays,
      overdueOpenTotal: totals.overdueOpenTotal,
    },
    concentration: {
      hhi: concentration.hhi,
      hhiScale: concentration.hhiScale,
      effectiveClientCount: concentration.effectiveClientCount,
      top1SharePct: concentration.top1.sharePct,
      top3SharePct: concentration.top3.sharePct,
      top5SharePct: concentration.top5.sharePct,
    },
    dueBasisMix,
    window,
    topClient: clients.length
      ? { label: clients[0].label, billed: clients[0].billed, sharePct: clients[0].billedSharePct }
      : null,
    currencies: flags.currencies,
    notes: notes.display,
    lintNotes: notes.lint,
    disclaimer: DISCLAIMER,
  };
}

// Strings handed to the advice linter. Client-name-bearing notes are replaced
// by their lint-safe twins so buyer data cannot trip the guardrail.
function summaryStrings(summary) {
  return [].concat(summary.lintNotes, [summary.disclaimer]);
}

module.exports = { buildSummary, summaryStrings, money, pct, days, plural, round2 };
