// engine/index.js
//
// HFF — Runway engine entry point.
//
//   generateRunwayPacket({ csv, profile, generatedAt }) -> {
//     packet,            // structured result (all figures)
//     validation,        // { ok, checks[] }
//     files: { xlsx: Buffer, pdf: Buffer, xlsxName, pdfName }
//   }
//
// Pipeline: ingest -> categorize -> cashflow -> tax/1099 -> validate -> render (xlsx+pdf).
// The advice-language linter runs on every rendered string and FAILS CLOSED.
//
// GUARDRAIL: organizational tooling only. No advice. Non-advice banner on every artifact.

'use strict';

const { ingest } = require('./ingest');
const { categorize } = require('./categorize');
const { cashflow } = require('./cashflow');
const { taxWorksheet } = require('./tax');
const { runValidation } = require('./validate');
const { assertNoAdvice } = require('./advice_linter');
const { renderXlsx, collectStrings } = require('./render_xlsx');
const { renderPdf } = require('./render_pdf');
const { DISCLAIMER } = require('./constants');

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

function periodDays(transactions) {
  if (transactions.length === 0) return 0;
  const dates = transactions.map((t) => t.date).sort();
  const a = Date.parse(dates[0] + 'T00:00:00Z');
  const b = Date.parse(dates[dates.length - 1] + 'T00:00:00Z');
  return Math.max(1, Math.round((b - a) / 86400000) + 1);
}

// Build the structured packet (no file bytes yet).
function buildPacket(csv, profile) {
  const { transactions, rejected, columns } = ingest(csv);
  if (transactions.length === 0) {
    const err = new Error('NO_VALID_TRANSACTIONS: no rows could be parsed from the CSV.');
    err.code = 'NO_VALID_TRANSACTIONS';
    err.rejected = rejected;
    throw err;
  }
  const { categorized, rollup, totalOutflow } = categorize(transactions, profile);
  const cf = cashflow(categorized, profile);
  const pdays = periodDays(categorized);
  const { estTax, list1099 } = taxWorksheet(categorized, rollup, profile, pdays);

  return {
    columns,
    transactions: categorized,
    rejected,
    rollup,
    totalOutflow,
    cashflow: cf,
    estTax,
    list1099,
    periodDays: pdays,
    disclaimer: DISCLAIMER,
  };
}

// Build the one-page PDF text lines.
function pdfLines(packet) {
  const cf = packet.cashflow;
  const et = packet.estTax;
  const candidates = packet.list1099.filter((c) => c.isCandidate);
  const lines = [
    { text: 'HFF Runway - Cash-Flow & Tax-Prep Summary', size: 16, bold: true, gap: 22 },
    { text: DISCLAIMER, size: 8, gap: 26 },
    { text: `As-of date: ${cf.asOf}    Transactions: ${packet.transactions.length}    Flagged rows: ${packet.rejected.length}`, size: 10, gap: 20 },
    { text: 'Cash flow', size: 12, bold: true, gap: 16 },
    { text: `  30-day net: $${fmt(cf.windows.d30 && cf.windows.d30.net)}   60-day net: $${fmt(cf.windows.d60 && cf.windows.d60.net)}   90-day net: $${fmt(cf.windows.d90 && cf.windows.d90.net)}`, gap: 14 },
    { text: `  Avg monthly burn: $${fmt(cf.avgMonthlyBurn)}    Runway: ${cf.runwayMonths == null ? 'n/a (provide cash on hand)' : cf.runwayMonths + ' months'}`, gap: 20 },
    { text: 'Estimated tax (annualized, for your accountant)', size: 12, bold: true, gap: 16 },
    { text: `  Annualized net profit: $${fmt(et.annualNetProfit)}   SE tax: $${fmt(et.seTax)}   Income tax: $${fmt(et.incomeTax)}`, gap: 14 },
    { text: `  Total annual estimate: $${fmt(et.totalAnnualTax)}    Quarterly payment: $${fmt(et.quarterlyPayment)}`, gap: 20 },
    { text: '1099 candidates (contractors paid over $600)', size: 12, bold: true, gap: 16 },
  ];
  if (candidates.length === 0) {
    lines.push({ text: '  None detected.', gap: 14 });
  } else {
    for (const c of candidates.slice(0, 12)) {
      lines.push({ text: `  ${c.payee} - $${fmt(c.totalPaid)}${c.missingW9 ? '  (W-9 missing)' : ''}`, gap: 13 });
    }
  }
  lines.push({ text: 'Full detail is in the accompanying .xlsx workbook (Transactions, Categories, CashFlow, EstimatedTax, 1099).', size: 8, gap: 12 });
  return lines;
}

function fmt(n) {
  if (n == null || isNaN(n)) return '0.00';
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Main entry.
async function generateRunwayPacket({ csv, profile = {}, generatedAt } = {}) {
  const stamp = generatedAt || new Date().toISOString();
  const packet = buildPacket(csv, profile);
  packet.generatedAt = stamp;

  // Validate BEFORE render/release.
  const validation = runValidation(packet);

  // Advice linter over every rendered string (xlsx cells + pdf lines). Fails closed.
  const xlsxStrings = collectStrings(packet);
  const pdfStrings = pdfLines(packet).map((l) => l.text);
  assertNoAdvice([...xlsxStrings, ...pdfStrings]);

  if (!validation.ok) {
    const err = new Error('VALIDATION_FAILED: packet withheld. ' + validation.checks.filter((c) => !c.pass).map((c) => c.name).join(', '));
    err.code = 'VALIDATION_FAILED';
    err.validation = validation;
    throw err;
  }

  const xlsx = await renderXlsx(packet);
  const pdf = renderPdf(pdfLines(packet));

  const utc = stamp.replace(/[:.]/g, '-').replace(/[^0-9A-Za-z-]/g, '');
  return {
    packet,
    validation,
    files: {
      xlsx,
      pdf,
      xlsxName: `runway_packet_${utc}.xlsx`,
      pdfName: `runway_packet_${utc}.pdf`,
    },
  };
}

module.exports = { generateRunwayPacket, buildPacket, pdfLines };
