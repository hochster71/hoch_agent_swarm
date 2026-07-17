// engine/cashflow.js
//
// Stage 3: 30/60/90-day inflow/outflow snapshot + runway-in-months.
// Windows are measured back from the "as of" date (profile.as_of, else the latest
// transaction date). Runway = cash_on_hand / average monthly burn. If the operator is
// cash-flow positive over the window, runway is reported as "not applicable (net positive)".

'use strict';

function daysBetween(aIso, bIso) {
  const a = Date.parse(aIso + 'T00:00:00Z');
  const b = Date.parse(bIso + 'T00:00:00Z');
  return Math.round((b - a) / 86400000);
}

function windowStats(transactions, asOf, days) {
  let inflow = 0;
  let outflow = 0;
  let count = 0;
  for (const tx of transactions) {
    const age = daysBetween(tx.date, asOf);
    if (age >= 0 && age < days) {
      if (tx.amount >= 0) inflow += tx.amount;
      else outflow += -tx.amount;
      count += 1;
    }
  }
  return {
    windowDays: days,
    inflow: round2(inflow),
    outflow: round2(outflow),
    net: round2(inflow - outflow),
    count,
  };
}

// cashflow(categorized, profile) -> { asOf, windows:{d30,d60,d90}, avgMonthlyBurn, runwayMonths, cashOnHand }
function cashflow(transactions, profile) {
  if (transactions.length === 0) {
    return { asOf: null, windows: {}, avgMonthlyBurn: 0, runwayMonths: null, cashOnHand: 0 };
  }
  const dates = transactions.map((t) => t.date).sort();
  const asOf = (profile && profile.as_of) || dates[dates.length - 1];

  const d30 = windowStats(transactions, asOf, 30);
  const d60 = windowStats(transactions, asOf, 60);
  const d90 = windowStats(transactions, asOf, 90);

  // Average monthly burn from the 90-day window (net outflow per 30 days).
  // burn is POSITIVE when spending exceeds income.
  const netOver90 = d90.net; // inflow - outflow
  const avgMonthlyNet = round2(netOver90 / 3); // 90 days ~= 3 months
  const avgMonthlyBurn = avgMonthlyNet < 0 ? round2(-avgMonthlyNet) : 0;

  const cashOnHand =
    profile && typeof profile.cash_on_hand === 'number' ? round2(profile.cash_on_hand) : null;

  let runwayMonths = null;
  if (avgMonthlyBurn > 0 && cashOnHand !== null) {
    runwayMonths = round2(cashOnHand / avgMonthlyBurn);
  } else if (avgMonthlyBurn === 0) {
    runwayMonths = 'net-positive'; // labeled string, not a number
  }

  return {
    asOf,
    windows: { d30, d60, d90 },
    avgMonthlyNet,
    avgMonthlyBurn,
    cashOnHand,
    runwayMonths,
  };
}

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

module.exports = { cashflow, daysBetween };
