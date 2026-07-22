// engine/timing.js
//
// HFF — Getting-Paid Speed Report — deterministic payment-timing analysis.
//
// Everything here is arithmetic over the invoices the ingest accepted. No
// external data, no benchmarks, no randomness. Given the same file the numbers
// are byte-identical.
//
// Produces:
//   clients[]   per-client billed, share, invoice count, paid vs open counts,
//               amount paid and amount outstanding, median / mean / fastest /
//               slowest days-to-pay across that client's PAID invoices, on-time
//               vs late counts against each invoice's own due basis, oldest open
//               invoice age, and the spellings merged into the bucket.
//   monthly[]   per issue-month: invoices, billed, paid count, median days-to-pay
//               for the paid invoices issued that month, and on-time share.
//   totals      overall billed / paid / outstanding, median & mean days-to-pay,
//               on-time share, share paid by count and by value, oldest open age.
//   concentration  top-1/3/5 billed share, HHI (0-10,000), effective client count.
//   dueBasisMix how many invoices used a due-date column, parseable terms, or the
//               assumed net-30 fallback — so the on-time figure is never a black box.
'use strict';

function round2(n) {
  return Math.round((Number(n) + Number.EPSILON) * 100) / 100;
}
function round1(n) {
  return Math.round((Number(n) + Number.EPSILON) * 10) / 10;
}

function median(sortedNums) {
  if (!sortedNums.length) return 0;
  const mid = Math.floor(sortedNums.length / 2);
  return sortedNums.length % 2 ? sortedNums[mid] : (sortedNums[mid - 1] + sortedNums[mid]) / 2;
}

function mean(nums) {
  if (!nums.length) return 0;
  return nums.reduce((s, x) => s + x, 0) / nums.length;
}

function shareOf(part, whole) {
  if (!whole) return 0;
  return round1((part / whole) * 100);
}

// ------------------------------------------------------ per-invoice timing pass

// Attaches onTime / overdue / ageDays to each invoice. Runs BEFORE aggregation
// so clients and months read from the same flags.
function markInvoices(invoices, lastDayInFile) {
  for (const inv of invoices) {
    if (inv.isPaid) {
      inv.onTime = inv.paidDay <= inv.dueDay;
      inv.overdue = false;
      inv.ageDays = null;
    } else {
      inv.onTime = null;
      inv.ageDays = Math.max(0, lastDayInFile - inv.issuedDay);
      inv.overdue = lastDayInFile > inv.dueDay;
    }
  }
  return invoices;
}

// ------------------------------------------------------------------- clients

function buildClients(invoices) {
  const buckets = new Map();
  for (const inv of invoices) {
    if (!buckets.has(inv.clientKey)) {
      buckets.set(inv.clientKey, { clientKey: inv.clientKey, rows: [], spellings: new Map() });
    }
    const b = buckets.get(inv.clientKey);
    b.rows.push(inv);
    b.spellings.set(inv.client, (b.spellings.get(inv.client) || 0) + 1);
  }

  const clients = [];
  for (const b of buckets.values()) {
    const rows = b.rows.slice().sort((a, x) => (a.issuedDay - x.issuedDay) || (a.line - x.line));
    const paid = rows.filter((r) => r.isPaid);
    const open = rows.filter((r) => !r.isPaid);

    const billed = round2(rows.reduce((s, r) => s + r.amount, 0));
    const paidBilled = round2(paid.reduce((s, r) => s + r.amount, 0));
    const outstanding = round2(open.reduce((s, r) => s + r.amount, 0));

    const dtp = paid.map((r) => r.daysToPay).sort((a, x) => a - x);
    const medianDaysToPay = dtp.length ? round1(median(dtp)) : null;
    const meanDaysToPay = dtp.length ? round1(mean(dtp)) : null;
    const fastestDaysToPay = dtp.length ? dtp[0] : null;
    const slowestDaysToPay = dtp.length ? dtp[dtp.length - 1] : null;

    const onTimeCount = paid.filter((r) => r.onTime === true).length;
    const lateCount = paid.length - onTimeCount;
    const onTimePct = paid.length ? shareOf(onTimeCount, paid.length) : null;

    const overdueOpen = open.filter((r) => r.overdue);
    const oldestOpenAgeDays = open.length ? Math.max(...open.map((r) => r.ageDays)) : null;

    const spellings = Array.from(b.spellings.entries())
      .sort((a, x) => (x[1] - a[1]) || a[0].localeCompare(x[0]))
      .map((e) => e[0]);

    clients.push({
      clientKey: b.clientKey,
      label: spellings[0],
      spellings,
      spellingCount: spellings.length,
      invoiceCount: rows.length,
      paidCount: paid.length,
      openCount: open.length,
      billed,
      paidBilled,
      outstanding,
      medianDaysToPay,
      meanDaysToPay,
      fastestDaysToPay,
      slowestDaysToPay,
      onTimeCount,
      lateCount,
      onTimePct,
      overdueOpenCount: overdueOpen.length,
      overdueOpenTotal: round2(overdueOpen.reduce((s, r) => s + r.amount, 0)),
      oldestOpenAgeDays,
      firstInvoice: rows[0].issuedDate,
      lastInvoice: rows[rows.length - 1].issuedDate,
      rows,
    });
  }

  const totalBilled = round2(clients.reduce((s, c) => s + c.billed, 0));
  clients.sort((a, b) => (b.billed - a.billed) || a.label.localeCompare(b.label));
  clients.forEach((c, i) => {
    c.rank = i + 1;
    c.billedSharePct = shareOf(c.billed, totalBilled);
  });
  return { clients, totalBilled };
}

// ------------------------------------------------------------------- monthly

function buildMonthly(invoices) {
  const byMonth = new Map();
  for (const inv of invoices) {
    if (!byMonth.has(inv.issuedMonth)) byMonth.set(inv.issuedMonth, []);
    byMonth.get(inv.issuedMonth).push(inv);
  }
  const months = Array.from(byMonth.keys()).sort();
  return months.map((m) => {
    const rows = byMonth.get(m);
    const paid = rows.filter((r) => r.isPaid);
    const dtp = paid.map((r) => r.daysToPay).sort((a, x) => a - x);
    const onTimeCount = paid.filter((r) => r.onTime === true).length;
    return {
      month: m,
      invoices: rows.length,
      billed: round2(rows.reduce((s, r) => s + r.amount, 0)),
      paidCount: paid.length,
      openCount: rows.length - paid.length,
      medianDaysToPay: dtp.length ? round1(median(dtp)) : null,
      onTimePct: paid.length ? shareOf(onTimeCount, paid.length) : null,
    };
  });
}

// ------------------------------------------------------------- concentration

// HHI on the standard 0-10,000 scale over BILLED amount: the sum of squared
// percentage shares. Reported as a number with its scale stated; no threshold
// is applied and no judgement is attached to the value.
function buildConcentration(clients, totalBilled) {
  const positive = clients.filter((c) => c.billed > 0);
  const shares = positive.map((c) => (totalBilled > 0 ? c.billed / totalBilled : 0));
  const hhi = round1(shares.reduce((s, x) => s + x * x, 0) * 10000);
  const effectiveClientCount = hhi > 0 ? round1(10000 / hhi) : 0;

  const topShare = (n) => {
    const slice = positive.slice(0, n);
    const net = round2(slice.reduce((s, c) => s + c.billed, 0));
    return { clients: slice.length, billed: net, sharePct: shareOf(net, totalBilled) };
  };

  return {
    clientCount: clients.length,
    hhi,
    hhiScale: '0-10,000 (sum of squared percentage shares of billed)',
    effectiveClientCount,
    top1: topShare(1),
    top3: topShare(3),
    top5: topShare(5),
  };
}

// ------------------------------------------------------------------ analyze

function analyzeTiming(invoices, meta) {
  const info = meta || {};
  const lastDay = invoices.reduce((mx, inv) => {
    const cand = Math.max(inv.issuedDay, inv.paidDay == null ? inv.issuedDay : inv.paidDay);
    return Math.max(mx, cand);
  }, invoices.length ? invoices[0].issuedDay : 0);

  markInvoices(invoices, lastDay);

  const { clients, totalBilled } = buildClients(invoices);
  const monthly = buildMonthly(invoices);
  const concentration = buildConcentration(clients, totalBilled);

  const paid = invoices.filter((r) => r.isPaid);
  const open = invoices.filter((r) => !r.isPaid);
  const dtpAll = paid.map((r) => r.daysToPay).sort((a, x) => a - x);

  const paidBilled = round2(paid.reduce((s, r) => s + r.amount, 0));
  const outstanding = round2(open.reduce((s, r) => s + r.amount, 0));
  const onTimeCount = paid.filter((r) => r.onTime === true).length;
  const overdueOpen = open.filter((r) => r.overdue);

  const dueBasisMix = { due_column: 0, terms: 0, assumed_net_30: 0 };
  for (const inv of invoices) dueBasisMix[inv.dueBasis] += 1;

  const firstDay = invoices.length ? invoices[0].issuedDay : 0;
  const spanDays = invoices.length ? (lastDay - firstDay) + 1 : 0;
  const asOf = invoices.length
    ? invoices.reduce((mx, inv) => {
        const iso = inv.paidDate && inv.paidDate > (inv.issuedDate) ? inv.paidDate : inv.issuedDate;
        return iso > mx ? iso : mx;
      }, invoices[0].issuedDate)
    : null;

  const mergedClients = clients.filter((c) => c.spellingCount > 1);

  return {
    clients,
    monthly,
    concentration,
    dueBasisMix,
    totals: {
      invoiceCount: invoices.length,
      clientCount: clients.length,
      billed: totalBilled,
      paidCount: paid.length,
      openCount: open.length,
      paidBilled,
      outstanding,
      medianDaysToPay: dtpAll.length ? round1(median(dtpAll)) : null,
      meanDaysToPay: dtpAll.length ? round1(mean(dtpAll)) : null,
      fastestDaysToPay: dtpAll.length ? dtpAll[0] : null,
      slowestDaysToPay: dtpAll.length ? dtpAll[dtpAll.length - 1] : null,
      onTimeCount,
      lateCount: paid.length - onTimeCount,
      onTimePct: paid.length ? shareOf(onTimeCount, paid.length) : null,
      pctPaidByCount: shareOf(paid.length, invoices.length),
      pctPaidByValue: shareOf(paidBilled, totalBilled),
      overdueOpenCount: overdueOpen.length,
      overdueOpenTotal: round2(overdueOpen.reduce((s, r) => s + r.amount, 0)),
      oldestOpenAgeDays: open.length ? Math.max(...open.map((r) => r.ageDays)) : null,
    },
    window: {
      start: invoices.length ? invoices[0].issuedDate : null,
      end: invoices.length ? invoices[invoices.length - 1].issuedDate : null,
      asOf,
      monthsObserved: monthly.length,
      spanDays,
    },
    flags: {
      mergedClientCount: mergedClients.length,
      hasDueColumn: !!info.hasDueColumn,
      hasTermsColumn: !!info.hasTermsColumn,
      clientFromName: !!info.clientFromName,
      creditNoteCount: info.creditNoteCount || 0,
      creditNoteTotal: info.creditNoteTotal || 0,
      currencies: info.currencies || [],
    },
  };
}

module.exports = {
  analyzeTiming, buildClients, buildMonthly, buildConcentration, markInvoices,
  round2, round1, median, mean, shareOf,
};
