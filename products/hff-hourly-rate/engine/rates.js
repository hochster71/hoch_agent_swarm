// engine/rates.js
//
// HFF — Effective Hourly Rate Report — deterministic analysis core.
//
// Everything here is arithmetic over the rows in the uploaded file. There is no
// market-rate database, no external lookup, no model. Language is observational
// by construction: the engine reports what hours and billing figures the file
// contains and what the arithmetic rates come out to — never whether a rate is
// good or bad, and never what the reader should charge or do.
//
// RATE DEFINITIONS (both reported, both plain arithmetic):
//   * effectiveRateCovered — observed revenue ÷ the hours of the entries that
//     CARRY billing figures. The rate on the hours the file actually prices.
//   * blendedRateAllHours — observed revenue ÷ ALL tracked hours (including
//     hours with no billing figures). What each tracked hour yielded overall.
// When every entry carries billing figures the two are identical.
'use strict';

const { WEEKDAY_NAMES } = require('./constants');

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

function weekdayIndex(dayNum) {
  // Day 0 (1970-01-01) was a Thursday; index 0 = Sunday.
  return (dayNum + 4) % 7;
}

// ------------------------------------------------------------- client rollup

function buildClients(entries) {
  const byKey = new Map();

  for (const e of entries) {
    if (!byKey.has(e.clientKey)) {
      byKey.set(e.clientKey, { clientKey: e.clientKey, labelCounts: new Map(), rows: [] });
    }
    const c = byKey.get(e.clientKey);
    c.rows.push(e);
    c.labelCounts.set(e.client, (c.labelCounts.get(e.client) || 0) + 1);
  }

  const clients = [];
  for (const c of byKey.values()) {
    // Display label = the spelling that appears most often; ties broken
    // alphabetically so output is deterministic.
    const label = [...c.labelCounts.entries()]
      .sort((a, b) => (b[1] - a[1]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))[0][0];

    const hours = c.rows.reduce((s, r) => s + r.hours, 0);
    const billableHours = c.rows.filter((r) => r.billable === true).reduce((s, r) => s + r.hours, 0);
    const nonBillableHours = c.rows.filter((r) => r.billable === false).reduce((s, r) => s + r.hours, 0);
    const unknownBillableHours = c.rows.filter((r) => r.billable === null).reduce((s, r) => s + r.hours, 0);

    const priced = c.rows.filter((r) => r.amount !== null);
    const revenue = priced.reduce((s, r) => s + r.amount, 0);
    const coveredHours = priced.reduce((s, r) => s + r.hours, 0);
    const derivedCount = priced.filter((r) => r.revenueSource === 'derived_from_rate').length;

    const sessionHours = c.rows.map((r) => r.hours);
    const months = new Set(c.rows.map((r) => r.month));
    const projects = new Set(c.rows.map((r) => r.project).filter(Boolean));
    const spellings = [...c.labelCounts.keys()].sort();

    clients.push({
      clientKey: c.clientKey,
      label,
      spellings,
      spellingCount: spellings.length,
      entryCount: c.rows.length,
      hours: round2(hours),
      billableHours: round2(billableHours),
      nonBillableHours: round2(nonBillableHours),
      unknownBillableHours: round2(unknownBillableHours),
      revenue: round2(revenue),
      pricedEntryCount: priced.length,
      coveredHours: round2(coveredHours),
      derivedFromRateCount: derivedCount,
      effectiveRateCovered: coveredHours > 0 && revenue > 0 ? round2(revenue / coveredHours) : null,
      blendedRateAllHours: hours > 0 && revenue > 0 ? round2(revenue / hours) : null,
      medianSessionHours: round2(median(sessionHours)),
      longestSessionHours: round2(Math.max(...sessionHours)),
      monthsActive: months.size,
      projectCount: projects.size,
      firstEntry: c.rows[0].date,
      lastEntry: c.rows[c.rows.length - 1].date,
      rows: c.rows,
      // filled in below, once totals are known
      hoursSharePct: 0,
      rank: 0,
    });
  }

  return clients;
}

// ------------------------------------------------------------- monthly series

function buildMonthly(entries, clientsByKey, hasBillable) {
  const byMonth = new Map();
  for (const e of entries) {
    if (!byMonth.has(e.month)) {
      byMonth.set(e.month, {
        month: e.month, hours: 0, billableHours: 0, knownFlagHours: 0,
        revenue: 0, coveredHours: 0, clientKeys: new Set(), perClient: new Map(),
      });
    }
    const m = byMonth.get(e.month);
    m.hours += e.hours;
    if (e.billable === true) { m.billableHours += e.hours; m.knownFlagHours += e.hours; }
    if (e.billable === false) { m.knownFlagHours += e.hours; }
    if (e.amount !== null) { m.revenue += e.amount; m.coveredHours += e.hours; }
    m.clientKeys.add(e.clientKey);
    m.perClient.set(e.clientKey, (m.perClient.get(e.clientKey) || 0) + e.hours);
  }

  return [...byMonth.values()]
    .sort((a, b) => (a.month < b.month ? -1 : a.month > b.month ? 1 : 0))
    .map((m) => {
      const entriesSorted = [...m.perClient.entries()]
        .sort((a, b) => (b[1] - a[1]) || (a[0] < b[0] ? -1 : 1));
      const top = entriesSorted.length ? entriesSorted[0] : null;
      return {
        month: m.month,
        hours: round2(m.hours),
        billableHours: round2(m.billableHours),
        billableSharePct: hasBillable && m.knownFlagHours > 0
          ? round2((m.billableHours / m.knownFlagHours) * 100) : null,
        revenue: round2(m.revenue),
        effectiveRateCovered: m.coveredHours > 0 && m.revenue > 0 ? round2(m.revenue / m.coveredHours) : null,
        activeClients: m.clientKeys.size,
        topClient: top ? (clientsByKey.get(top[0]) || {}).label || top[0] : '',
        topClientHours: top ? round2(top[1]) : 0,
      };
    });
}

// ------------------------------------------------------------- weekday series

function buildWeekdays(entries) {
  const hours = new Array(7).fill(0);
  for (const e of entries) hours[weekdayIndex(e.day)] += e.hours;
  return WEEKDAY_NAMES.map((name, i) => ({ weekday: name, hours: round2(hours[i]) }));
}

// ------------------------------------------------------------- entry point

function analyzeRates(entries, meta) {
  const info = meta || {};

  const clients = buildClients(entries);
  const clientsByKey = new Map(clients.map((c) => [c.clientKey, c]));

  const totalHours = round2(entries.reduce((s, e) => s + e.hours, 0));
  const billableHours = round2(entries.filter((e) => e.billable === true).reduce((s, e) => s + e.hours, 0));
  const nonBillableHours = round2(entries.filter((e) => e.billable === false).reduce((s, e) => s + e.hours, 0));
  const unknownBillableHours = round2(entries.filter((e) => e.billable === null).reduce((s, e) => s + e.hours, 0));
  const knownFlagHours = round2(billableHours + nonBillableHours);

  const priced = entries.filter((e) => e.amount !== null);
  const revenue = round2(priced.reduce((s, e) => s + e.amount, 0));
  const coveredHours = round2(priced.reduce((s, e) => s + e.hours, 0));
  const derivedFromRateCount = priced.filter((e) => e.revenueSource === 'derived_from_rate').length;

  const windowStart = entries[0].date;
  const windowEnd = entries[entries.length - 1].date;
  const windowDays = entries[entries.length - 1].day - entries[0].day;

  for (const c of clients) {
    c.hoursSharePct = totalHours > 0 ? round2((c.hours / totalHours) * 100) : 0;
  }
  clients.sort((a, b) => (b.hours - a.hours) || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0));
  clients.forEach((c, i) => { c.rank = i + 1; });

  const monthly = buildMonthly(entries, clientsByKey, !!info.hasBillable);
  const weekdays = buildWeekdays(entries);
  const trackedDays = new Set(entries.map((e) => e.day)).size;

  return {
    clients,
    monthly,
    weekdays,
    totals: {
      entries: entries.length,
      hours: totalHours,
      billableHours,
      nonBillableHours,
      unknownBillableHours,
      knownFlagHours,
      revenue,
      pricedEntries: priced.length,
      coveredHours,
      derivedFromRateCount,
      trackedDays,
    },
    rates: {
      available: revenue > 0 && coveredHours > 0,
      effectiveRateCovered: revenue > 0 && coveredHours > 0 ? round2(revenue / coveredHours) : null,
      blendedRateAllHours: revenue > 0 && totalHours > 0 ? round2(revenue / totalHours) : null,
      coveragePctOfHours: totalHours > 0 ? round2((coveredHours / totalHours) * 100) : 0,
    },
    billableShare: {
      available: !!info.hasBillable && knownFlagHours > 0,
      billableSharePct: info.hasBillable && knownFlagHours > 0
        ? round2((billableHours / knownFlagHours) * 100) : null,
    },
    clientCount: clients.length,
    mergedSpellings: clients.filter((c) => c.spellingCount > 1),
    window: { start: windowStart, end: windowEnd, days: windowDays, months: monthly.length },
    meta: {
      hasProject: !!info.hasProject,
      hasBillable: !!info.hasBillable,
      hasAmount: !!info.hasAmount,
      hasRate: !!info.hasRate,
      negativeAmountsIgnored: info.negativeAmountsIgnored || 0,
      durationUnit: info.durationUnit || 'hours',
    },
  };
}

module.exports = { analyzeRates, buildClients, buildMonthly, buildWeekdays, weekdayIndex, round2, median };
