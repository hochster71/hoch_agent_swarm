// engine/validate.js
//
// Validation suite (spec §Definition of done). Runs BEFORE the packet is released.
// Every check returns { name, pass, detail }. runValidation aggregates ok = all pass.
//
//   - totals reconcile: category rollup sums exactly to the accepted transactions
//   - no impossible values: percentages in [0,100], counts non-negative, no NaN
//   - est-tax arithmetic verified programmatically (recompute and compare)
//   - 1099 list matches the >$600 rule exactly
//   - runway is a non-negative number or a labeled string (never NaN/negative)

'use strict';

const { SE, THRESHOLD_1099 } = require('./constants');

const CENT = 0.01;

function approx(a, b, tol = CENT) {
  return Math.abs(a - b) <= tol;
}
function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

function runValidation(packet) {
  const checks = [];
  const add = (name, pass, detail) => checks.push({ name, pass: !!pass, detail: detail || '' });

  const txns = packet.transactions;
  const rollup = packet.rollup;

  // 1) Totals reconcile: sum of tx amounts == sum of rollup nets; inflow/outflow match.
  const txNet = round2(txns.reduce((s, t) => s + t.amount, 0));
  const txInflow = round2(txns.filter((t) => t.amount >= 0).reduce((s, t) => s + t.amount, 0));
  const txOutflow = round2(txns.filter((t) => t.amount < 0).reduce((s, t) => s + -t.amount, 0));
  const rollNet = round2(rollup.reduce((s, r) => s + r.net, 0));
  const rollInflow = round2(rollup.reduce((s, r) => s + r.inflow, 0));
  const rollOutflow = round2(rollup.reduce((s, r) => s + r.outflow, 0));
  add(
    'totals_reconcile',
    approx(txNet, rollNet, 0.05) && approx(txInflow, rollInflow, 0.05) && approx(txOutflow, rollOutflow, 0.05),
    `tx net ${txNet} vs rollup ${rollNet}; inflow ${txInflow}/${rollInflow}; outflow ${txOutflow}/${rollOutflow}`
  );

  // 2) No impossible values.
  let impossible = null;
  for (const r of rollup) {
    if (r.pctOfOutflow < 0 || r.pctOfOutflow > 100) impossible = `pct ${r.pctOfOutflow} for ${r.category}`;
    if (r.count < 0) impossible = `negative count for ${r.category}`;
    if ([r.inflow, r.outflow, r.net].some((v) => isNaN(v))) impossible = `NaN in ${r.category}`;
  }
  const pctSum = round2(rollup.reduce((s, r) => s + r.pctOfOutflow, 0));
  if (rollOutflow > 0 && !(pctSum >= 99.5 && pctSum <= 100.5)) impossible = `pct sum ${pctSum} != 100`;
  add('no_impossible_values', impossible === null, impossible || `pct sum ${pctSum}`);

  // 3) Est-tax arithmetic verified by independent recompute.
  const et = packet.estTax;
  const seBaseR = round2(Math.max(0, et.annualNetProfit) * SE.NET_EARNINGS_FACTOR);
  const ssR = round2(Math.min(seBaseR, SE.SS_WAGE_BASE) * SE.SS_RATE);
  const medR = round2(seBaseR * SE.MEDICARE_RATE);
  const seTaxR = round2(ssR + medR);
  const halfR = round2(seTaxR / 2);
  const totalR = round2(et.seTax + et.incomeTax);
  const qR = round2(et.totalAnnualTax / 4);
  const taxOk =
    approx(et.seBase, seBaseR) &&
    approx(et.ssPortion, ssR) &&
    approx(et.medicarePortion, medR) &&
    approx(et.seTax, seTaxR) &&
    approx(et.halfSeDeduction, halfR) &&
    approx(et.totalAnnualTax, totalR) &&
    approx(et.quarterlyPayment, qR) &&
    approx(round2(et.grossIncome - et.businessExpenses), et.netProfitPeriod) &&
    et.totalAnnualTax >= 0 &&
    et.quarterlyPayment >= 0;
  add(
    'est_tax_arithmetic',
    taxOk,
    `seTax ${et.seTax}/${seTaxR}; total ${et.totalAnnualTax}/${totalR}; qtr ${et.quarterlyPayment}/${qR}`
  );

  // 3b) Quarterly * 4 reconciles to annual (within rounding).
  add(
    'quarterly_reconciles',
    approx(round2(et.quarterlyPayment * 4), et.totalAnnualTax, 0.05),
    `${round2(et.quarterlyPayment * 4)} vs ${et.totalAnnualTax}`
  );

  // 4) 1099 rule: candidate iff totalPaid > 600, exactly.
  let ruleBad = null;
  for (const c of packet.list1099) {
    const shouldBe = c.totalPaid > THRESHOLD_1099;
    if (c.isCandidate !== shouldBe) ruleBad = `${c.payee} paid ${c.totalPaid} candidate=${c.isCandidate}`;
    if (c.totalPaid < 0) ruleBad = `${c.payee} negative total`;
  }
  add('rule_1099_over_600', ruleBad === null, ruleBad || `${packet.list1099.filter((c) => c.isCandidate).length} candidates`);

  // 5) Runway sane.
  const rw = packet.cashflow.runwayMonths;
  const runwayOk = rw == null || rw === 'net-positive' || (typeof rw === 'number' && rw >= 0 && isFinite(rw));
  add('runway_sane', runwayOk, `runway=${rw}`);

  // 6) Disclaimer present.
  add('disclaimer_present', typeof packet.disclaimer === 'string' && /not financial or tax advice/i.test(packet.disclaimer), packet.disclaimer ? 'present' : 'missing');

  const ok = checks.every((c) => c.pass);
  return { ok, checks };
}

module.exports = { runValidation };
