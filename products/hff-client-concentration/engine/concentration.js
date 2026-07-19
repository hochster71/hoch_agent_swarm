// engine/concentration.js
//
// HFF — Client Revenue Concentration Report — deterministic analysis core.
//
// Everything here is arithmetic over the rows in the uploaded file. There is no
// company database, no external lookup, no model. Language is observational by
// construction: the engine reports HOW revenue is distributed, never what the
// distribution means for the reader or what they should do about it.
'use strict';

const { NEW_CLIENT_WINDOW_DAYS, DORMANCY_MULTIPLE } = require('./constants');

function round2(n) {
  const v = Math.round((Number(n) + Number.EPSILON) * 100) / 100;
  return Object.is(v, -0) ? 0 : v;
}

function median(nums) {
  if (!nums.length) return null;
  const s = nums.slice().sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// ------------------------------------------------------------- client rollup

function buildClients(invoices) {
  const byKey = new Map();

  for (const inv of invoices) {
    if (!byKey.has(inv.clientKey)) {
      byKey.set(inv.clientKey, {
        clientKey: inv.clientKey,
        labelCounts: new Map(),
        rows: [],
        gross: 0,
        credits: 0,
      });
    }
    const c = byKey.get(inv.clientKey);
    c.rows.push(inv);
    c.labelCounts.set(inv.client, (c.labelCounts.get(inv.client) || 0) + 1);
    if (inv.amount > 0) c.gross += inv.amount;
    else c.credits += Math.abs(inv.amount);
  }

  const clients = [];
  for (const c of byKey.values()) {
    // Display label = the spelling that appears most often; ties broken
    // alphabetically so output is deterministic.
    const label = [...c.labelCounts.entries()]
      .sort((a, b) => (b[1] - a[1]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))[0][0];

    const positives = c.rows.filter((r) => r.amount > 0);
    const days = positives.map((r) => r.day).sort((a, b) => a - b);
    const gaps = [];
    for (let i = 1; i < days.length; i++) gaps.push(days[i] - days[i - 1]);

    const payDays = c.rows.map((r) => r.daysToPay).filter((d) => d !== null && d !== undefined);
    const months = new Set(positives.map((r) => r.month));

    const net = round2(c.gross - c.credits);
    const spellings = [...c.labelCounts.keys()].sort();

    clients.push({
      clientKey: c.clientKey,
      label,
      spellings,
      spellingCount: spellings.length,
      invoiceCount: positives.length,
      creditCount: c.rows.length - positives.length,
      gross: round2(c.gross),
      credits: round2(c.credits),
      net,
      averageInvoice: positives.length ? round2(c.gross / positives.length) : 0,
      largestInvoice: positives.length ? round2(Math.max(...positives.map((r) => r.amount))) : 0,
      smallestInvoice: positives.length ? round2(Math.min(...positives.map((r) => r.amount))) : 0,
      firstInvoice: positives.length ? positives[0].date : c.rows[0].date,
      lastInvoice: positives.length ? positives[positives.length - 1].date : c.rows[c.rows.length - 1].date,
      firstDay: days.length ? days[0] : c.rows[0].day,
      lastDay: days.length ? days[days.length - 1] : c.rows[c.rows.length - 1].day,
      medianGapDays: gaps.length ? Math.round(median(gaps)) : null,
      monthsWithRevenue: months.size,
      medianDaysToPay: payDays.length ? Math.round(median(payDays)) : null,
      slowestPaymentDays: payDays.length ? Math.max(...payDays) : null,
      paidRowsSeen: payDays.length,
      rows: c.rows,
      // filled in below, once the portfolio total is known
      sharePct: 0,
      rank: 0,
      daysSinceLastInvoice: 0,
      newInWindow: false,
      noInvoiceSinceExpected: false,
    });
  }

  return clients;
}

// ------------------------------------------------------------- concentration

function concentrationMetrics(clients, totalNet) {
  const contributing = clients.filter((c) => c.net > 0);
  const fractions = totalNet > 0 ? contributing.map((c) => c.net / totalNet) : [];
  const sumSquares = fractions.reduce((s, f) => s + f * f, 0);

  const sortedShares = contributing
    .map((c) => (totalNet > 0 ? (c.net / totalNet) * 100 : 0))
    .sort((a, b) => b - a);

  const topN = (n) => round2(sortedShares.slice(0, n).reduce((s, v) => s + v, 0));

  // Smallest number of clients whose combined share reaches 50% / 80%.
  const clientsToReach = (targetPct) => {
    if (!sortedShares.length) return null;
    let acc = 0;
    for (let i = 0; i < sortedShares.length; i++) {
      acc += sortedShares[i];
      if (acc >= targetPct - 1e-9) return i + 1;
    }
    return null;
  };

  return {
    contributingClients: contributing.length,
    top1SharePct: topN(1),
    top3SharePct: topN(3),
    top5SharePct: topN(5),
    top10SharePct: topN(10),
    // HHI on the standard 0–10,000 scale. 10,000 means every dollar in the file
    // came from one client; it falls toward 0 as revenue spreads out.
    hhi: sumSquares > 0 ? Math.round(sumSquares * 10000) : 0,
    // The number of EQUAL-sized clients that would produce this same HHI.
    effectiveClientCount: sumSquares > 0 ? round2(1 / sumSquares) : 0,
    clientsToReachHalf: clientsToReach(50),
    clientsToReachEighty: clientsToReach(80),
  };
}

// ------------------------------------------------------------- monthly series

function buildMonthly(invoices, clientsByKey) {
  const byMonth = new Map();
  for (const inv of invoices) {
    if (!byMonth.has(inv.month)) {
      byMonth.set(inv.month, { month: inv.month, gross: 0, credits: 0, clientKeys: new Set(), perClient: new Map() });
    }
    const m = byMonth.get(inv.month);
    if (inv.amount > 0) {
      m.gross += inv.amount;
      m.clientKeys.add(inv.clientKey);
      m.perClient.set(inv.clientKey, (m.perClient.get(inv.clientKey) || 0) + inv.amount);
    } else {
      m.credits += Math.abs(inv.amount);
    }
  }

  return [...byMonth.values()]
    .sort((a, b) => (a.month < b.month ? -1 : a.month > b.month ? 1 : 0))
    .map((m) => {
      const entries = [...m.perClient.entries()]
        .sort((a, b) => (b[1] - a[1]) || (a[0] < b[0] ? -1 : 1));
      const top = entries.length ? entries[0] : null;
      const net = round2(m.gross - m.credits);
      return {
        month: m.month,
        gross: round2(m.gross),
        credits: round2(m.credits),
        net,
        activeClients: m.clientKeys.size,
        topClient: top ? (clientsByKey.get(top[0]) || {}).label || top[0] : '',
        topClientAmount: top ? round2(top[1]) : 0,
        topClientSharePct: top && m.gross > 0 ? round2((top[1] / m.gross) * 100) : 0,
      };
    });
}

// ------------------------------------------------------------- entry point

function analyzeConcentration(invoices, opts) {
  const options = opts || {};

  const clients = buildClients(invoices);
  const clientsByKey = new Map(clients.map((c) => [c.clientKey, c]));

  const grossTotal = round2(invoices.filter((i) => i.amount > 0).reduce((s, i) => s + i.amount, 0));
  const creditTotal = round2(invoices.filter((i) => i.amount < 0).reduce((s, i) => s + Math.abs(i.amount), 0));
  const totalNet = round2(grossTotal - creditTotal);

  const windowStartDay = invoices[0].day;
  const windowEndDay = invoices[invoices.length - 1].day;
  const windowStart = invoices[0].date;
  const windowEnd = invoices[invoices.length - 1].date;
  const windowDays = windowEndDay - windowStartDay;

  // Share, rank, dormancy, newness.
  const netPositiveTotal = round2(clients.filter((c) => c.net > 0).reduce((s, c) => s + c.net, 0));
  for (const c of clients) {
    c.sharePct = netPositiveTotal > 0 && c.net > 0 ? round2((c.net / netPositiveTotal) * 100) : 0;
    c.daysSinceLastInvoice = windowEndDay - c.lastDay;
    c.newInWindow = windowEndDay - c.firstDay <= NEW_CLIENT_WINDOW_DAYS && windowDays > NEW_CLIENT_WINDOW_DAYS;
    c.noInvoiceSinceExpected =
      c.medianGapDays !== null &&
      c.medianGapDays > 0 &&
      c.daysSinceLastInvoice > c.medianGapDays * DORMANCY_MULTIPLE;
  }

  clients.sort((a, b) => (b.net - a.net) || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0));
  clients.forEach((c, i) => { c.rank = i + 1; });

  const metrics = concentrationMetrics(clients, netPositiveTotal);
  const monthly = buildMonthly(invoices, clientsByKey);

  const allPayDays = invoices.map((i) => i.daysToPay).filter((d) => d !== null && d !== undefined);

  return {
    clients,
    monthly,
    metrics,
    totals: {
      gross: grossTotal,
      credits: creditTotal,
      net: totalNet,
      netPositiveOnly: netPositiveTotal,
      invoiceRows: invoices.filter((i) => i.amount > 0).length,
      creditRows: invoices.filter((i) => i.amount < 0).length,
    },
    clientCount: clients.length,
    netNegativeClients: clients.filter((c) => c.net <= 0).map((c) => ({ label: c.label, net: c.net })),
    dormant: clients.filter((c) => c.noInvoiceSinceExpected),
    newClients: clients.filter((c) => c.newInWindow),
    mergedSpellings: clients.filter((c) => c.spellingCount > 1),
    paymentTiming: allPayDays.length
      ? {
        available: true,
        rowsWithPaidDate: allPayDays.length,
        medianDaysToPay: Math.round(median(allPayDays)),
        slowestDaysToPay: Math.max(...allPayDays),
      }
      : { available: false, rowsWithPaidDate: 0, medianDaysToPay: null, slowestDaysToPay: null },
    window: { start: windowStart, end: windowEnd, days: windowDays, months: monthly.length },
    options: { newClientWindowDays: NEW_CLIENT_WINDOW_DAYS, dormancyMultiple: DORMANCY_MULTIPLE, ...options },
  };
}

module.exports = { analyzeConcentration, buildClients, concentrationMetrics, buildMonthly, round2, median };
