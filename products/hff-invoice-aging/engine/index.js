// engine/index.js
//
// HFF — Invoice Aging Snapshot engine entry point.
//
//   generateAgingReport({ csv, profile, generatedAt }) -> {
//     report,            // structured result (all figures)
//     validation,        // { ok, checks[] }
//     files: { xlsx: Buffer, pdf: Buffer, xlsxName, pdfName }
//   }
//
// Pipeline: ingest -> aging (bucket) -> summarize by customer -> validate -> render (xlsx+pdf).
// The advice-language linter runs on every rendered string and FAILS CLOSED.
//
// GUARDRAIL: organizational tooling only. No financial/collections/legal advice.

'use strict';

const { ingest } = require('./ingest');
const { aging } = require('./aging');
const { summarizeByCustomer } = require('./summary');
const { runValidation } = require('./validate');
const { assertNoAdvice } = require('./advice_linter');
const { renderXlsx, collectStrings } = require('./render_xlsx');
const { renderPdf } = require('./render_pdf');
const { DISCLAIMER } = require('./constants');

function fmt(n) {
  if (n == null || isNaN(n)) return '0.00';
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Build the structured report (no file bytes yet).
function buildReport(csv, profile) {
  const { invoices, rejected, columns } = ingest(csv);
  if (invoices.length === 0) {
    const err = new Error('NO_VALID_INVOICES: no rows could be parsed from the CSV.');
    err.code = 'NO_VALID_INVOICES';
    err.rejected = rejected;
    throw err;
  }
  const ag = aging(invoices, profile);
  const byCustomer = summarizeByCustomer(ag.aged);
  return {
    columns,
    invoices,
    rejected,
    aging: ag,
    byCustomer,
    disclaimer: DISCLAIMER,
  };
}

// Build the one-page PDF text lines.
function pdfLines(report) {
  const ag = report.aging;
  const lines = [
    { text: 'HFF Invoice Aging Snapshot', size: 16, bold: true, gap: 22 },
    { text: DISCLAIMER, size: 8, gap: 30 },
    { text: `As-of date: ${ag.asOf || 'n/a'}    Outstanding invoices: ${ag.outstandingCount}    Paid/void: ${ag.paidCount}    Flagged rows: ${report.rejected.length}`, size: 10, gap: 20 },
    { text: `Total outstanding: $${fmt(ag.totalOutstanding)}`, size: 12, bold: true, gap: 18 },
    { text: 'Aging buckets (by days past due)', size: 12, bold: true, gap: 16 },
  ];
  for (const b of ag.buckets) {
    lines.push({ text: `  ${b.label}: $${fmt(b.balance)}  (${b.count} inv, ${fmt(b.pctOfOutstanding)}%)`, gap: 14 });
  }
  lines.push({ text: 'Top customers by outstanding balance', size: 12, bold: true, gap: 16 });
  const top = report.byCustomer.slice(0, 10);
  if (top.length === 0) {
    lines.push({ text: '  None outstanding.', gap: 14 });
  } else {
    for (const c of top) {
      lines.push({ text: `  ${c.customer} - $${fmt(c.outstanding)}  (${c.count} inv, oldest ${c.oldestDaysPastDue}d past due)`, gap: 13 });
    }
  }
  lines.push({ text: 'Full detail is in the accompanying .xlsx workbook (Summary, Buckets, ByCustomer, Aging).', size: 8, gap: 12 });
  return lines;
}

async function generateAgingReport({ csv, profile = {}, generatedAt } = {}) {
  const stamp = generatedAt || new Date().toISOString();
  const report = buildReport(csv, profile);
  report.generatedAt = stamp;

  // Validate BEFORE render/release.
  const validation = runValidation(report);

  // Advice linter over every rendered string (xlsx cells + pdf lines). Fails closed.
  const xlsxStrings = collectStrings(report);
  const pdfStrings = pdfLines(report).map((l) => l.text);
  assertNoAdvice([...xlsxStrings, ...pdfStrings]);

  if (!validation.ok) {
    const err = new Error('VALIDATION_FAILED: report withheld. ' + validation.checks.filter((c) => !c.pass).map((c) => c.name).join(', '));
    err.code = 'VALIDATION_FAILED';
    err.validation = validation;
    throw err;
  }

  const xlsx = await renderXlsx(report);
  const pdf = renderPdf(pdfLines(report));

  const utc = stamp.replace(/[:.]/g, '-').replace(/[^0-9A-Za-z-]/g, '');
  return {
    report,
    validation,
    files: {
      xlsx,
      pdf,
      xlsxName: `invoice_aging_${utc}.xlsx`,
      pdfName: `invoice_aging_${utc}.pdf`,
    },
  };
}

module.exports = { generateAgingReport, buildReport, pdfLines };
