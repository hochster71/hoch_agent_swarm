// engine/tax.js
//
// Stage 4: estimated quarterly-tax worksheet + year-end 1099-candidate list.
//
// GUARDRAIL: this computes and SHOWS arithmetic with every input labeled. It frames the
// result as "an estimate for your accountant." It does NOT recommend a strategy or tell the
// user what to do. Every line is a labeled number the user's CPA can check.

'use strict';

const {
  SE,
  STANDARD_DEDUCTION,
  BRACKETS,
  NON_EXPENSE_CATEGORIES,
  INCOME_CATEGORY,
  CONTRACTOR_CATEGORY,
  THRESHOLD_1099,
} = require('./constants');

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// Progressive income tax from a bracket table. Returns { tax, lines[] } with per-bracket math shown.
function bracketTax(taxable, brackets) {
  let remaining = Math.max(0, taxable);
  let lastCap = 0;
  let tax = 0;
  const lines = [];
  for (const [cap, rate] of brackets) {
    if (remaining <= 0) break;
    const band = Math.min(remaining, cap - lastCap);
    if (band > 0) {
      const portion = round2(band * rate);
      tax += portion;
      lines.push({
        label: `  ${(rate * 100).toFixed(0)}% on $${round2(band).toLocaleString()} (band up to $${cap === Infinity ? '∞' : cap.toLocaleString()})`,
        value: portion,
      });
      remaining -= band;
      lastCap = cap;
    } else {
      lastCap = cap;
    }
  }
  return { tax: round2(tax), lines };
}

// worksheet(categorized, rollup, profile, periodDays) -> { estTax:{...}, list1099:[...] }
function taxWorksheet(categorized, rollup, profile, periodDays) {
  const filing = (profile && profile.filing_type) || 'single';
  const brackets = BRACKETS[filing] || BRACKETS.single;
  const stdDeduction = STANDARD_DEDUCTION[filing] || STANDARD_DEDUCTION.single;

  // --- Gross business income: sum of Income-category inflows ---
  let grossIncome = 0;
  let businessExpenses = 0;
  for (const b of rollup) {
    if (b.category === INCOME_CATEGORY) grossIncome += b.inflow;
    if (!NON_EXPENSE_CATEGORIES.has(b.category)) businessExpenses += b.outflow;
  }
  grossIncome = round2(grossIncome);
  businessExpenses = round2(businessExpenses);
  const netProfitPeriod = round2(grossIncome - businessExpenses);

  // --- Annualize the period's net profit so the worksheet estimates a full year ---
  const days = periodDays && periodDays > 0 ? periodDays : 90;
  const annualizationFactor = round2(365 / days);
  const annualNetProfit = round2(netProfitPeriod * annualizationFactor);

  // --- Self-employment tax (2024 parameters, labeled) ---
  const seBase = round2(Math.max(0, annualNetProfit) * SE.NET_EARNINGS_FACTOR);
  const ssPortion = round2(Math.min(seBase, SE.SS_WAGE_BASE) * SE.SS_RATE);
  const medicarePortion = round2(seBase * SE.MEDICARE_RATE);
  const seTax = round2(ssPortion + medicarePortion);
  const halfSeDeduction = round2(seTax / 2);

  // --- Income tax estimate ---
  const agi = round2(Math.max(0, annualNetProfit) - halfSeDeduction);
  const taxableIncome = round2(Math.max(0, agi - stdDeduction));
  const inc = bracketTax(taxableIncome, brackets);
  const incomeTax = inc.tax;

  // --- Totals ---
  const totalAnnualTax = round2(seTax + incomeTax);
  const quarterlyPayment = round2(totalAnnualTax / 4);

  // Fully labeled worksheet lines (every input shown).
  const lines = [
    { label: `Filing type`, value: filing },
    { label: `Period analyzed (days of data)`, value: days },
    { label: `Gross business income (sum of Income inflows, period)`, value: grossIncome },
    { label: `Business expenses (sum of deductible outflows, period)`, value: businessExpenses },
    { label: `Net profit (period) = income − expenses`, value: netProfitPeriod },
    { label: `Annualization factor = 365 ÷ ${days}`, value: annualizationFactor },
    { label: `Annualized net profit = period net × factor`, value: annualNetProfit },
    { label: `SE base = annualized net × ${SE.NET_EARNINGS_FACTOR} (92.35%)`, value: seBase },
    { label: `Social Security portion = min(SE base, $${SE.SS_WAGE_BASE.toLocaleString()}) × ${SE.SS_RATE * 100}%`, value: ssPortion },
    { label: `Medicare portion = SE base × ${SE.MEDICARE_RATE * 100}%`, value: medicarePortion },
    { label: `Self-employment tax = SS + Medicare`, value: seTax },
    { label: `½ SE-tax deduction = SE tax ÷ 2`, value: halfSeDeduction },
    { label: `Estimated AGI = annualized net − ½ SE deduction`, value: agi },
    { label: `Standard deduction (${filing})`, value: stdDeduction },
    { label: `Taxable income = AGI − standard deduction (floored at 0)`, value: taxableIncome },
    ...inc.lines,
    { label: `Estimated income tax (sum of bands)`, value: incomeTax },
    { label: `TOTAL estimated annual tax = SE tax + income tax`, value: totalAnnualTax },
    { label: `Estimated quarterly payment = total ÷ 4`, value: quarterlyPayment },
  ];

  const estTax = {
    filing,
    periodDays: days,
    grossIncome,
    businessExpenses,
    netProfitPeriod,
    annualizationFactor,
    annualNetProfit,
    seBase,
    ssPortion,
    medicarePortion,
    seTax,
    halfSeDeduction,
    agi,
    stdDeduction,
    taxableIncome,
    incomeTax,
    totalAnnualTax,
    quarterlyPayment,
    lines,
  };

  // --- 1099-candidate list ---
  const w9OnFile = new Set(
    ((profile && profile.w9_on_file) || []).map((n) => String(n).toLowerCase())
  );
  const contractorTotals = new Map();
  for (const tx of categorized) {
    if (tx.category !== CONTRACTOR_CATEGORY) continue;
    if (tx.amount >= 0) continue; // only money paid OUT to contractors counts
    const payee = normalizePayee(tx.description);
    if (!contractorTotals.has(payee)) contractorTotals.set(payee, { payee, total: 0, count: 0 });
    const e = contractorTotals.get(payee);
    e.total += -tx.amount;
    e.count += 1;
  }

  const list1099 = Array.from(contractorTotals.values())
    .map((e) => ({
      payee: e.payee,
      totalPaid: round2(e.total),
      payments: e.count,
      isCandidate: round2(e.total) > THRESHOLD_1099,
      w9OnFile: w9OnFile.has(e.payee.toLowerCase()),
      missingW9: round2(e.total) > THRESHOLD_1099 && !w9OnFile.has(e.payee.toLowerCase()),
    }))
    .sort((a, b) => b.totalPaid - a.totalPaid);

  return { estTax, list1099 };
}

// Collapse a raw bank description to a stable payee key (strip trailing IDs, dates, refs).
function normalizePayee(desc) {
  return String(desc)
    .replace(/\b\d{4,}\b/g, '') // strip long numbers (ref ids)
    .replace(/\s+#?\d+\s*$/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

module.exports = { taxWorksheet, bracketTax, normalizePayee };
