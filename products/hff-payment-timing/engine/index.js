// engine/index.js
//
// HFF — Getting-Paid Speed Report — engine entry point.
//
// buildReport(csvText, opts) runs the whole deterministic pipeline:
//   validate -> ingest (flag bad rows) -> timing analysis -> summarize ->
//   ADVICE LINTER (fails closed) -> render XLSX + PDF.
//
// The advice linter runs BEFORE any artifact bytes are produced, so a guardrail
// violation withholds the whole report rather than shipping a lintable artifact.
'use strict';

const { validateCsvInput } = require('./validate');
const { ingestCsv } = require('./ingest');
const { analyzeTiming } = require('./timing');
const { buildSummary, summaryStrings } = require('./summary');
const { assertNoAdvice } = require('./advice_linter');
const { renderXlsx } = require('./render_xlsx');
const { renderPdf } = require('./render_pdf');
const { PRODUCT_NAME, PRODUCT_SLUG, DISCLAIMER } = require('./constants');

function analyze(csvText, opts) {
  const options = opts || {};
  validateCsvInput(csvText);
  const ingested = ingestCsv(csvText, options);
  const analysis = analyzeTiming(ingested.invoices, {
    hasDueColumn: ingested.hasDueColumn,
    hasTermsColumn: ingested.hasTermsColumn,
    clientFromName: ingested.clientFromName,
    creditNoteCount: ingested.creditNoteCount,
    creditNoteTotal: ingested.creditNoteTotal,
    currencies: ingested.currencies,
  });
  const summary = buildSummary(analysis, { skippedCount: ingested.skipped.length });

  // HARD GUARDRAIL — fails closed before anything is rendered.
  assertNoAdvice(summaryStrings(summary));

  return {
    product: PRODUCT_SLUG,
    productName: PRODUCT_NAME,
    disclaimer: DISCLAIMER,
    dateOrder: ingested.dateOrder,
    summary,
    analysis,
    skipped: ingested.skipped,
  };
}

function buildReport(csvText, opts) {
  const report = analyze(csvText, opts);
  return {
    report,
    xlsx: renderXlsx(report),
    pdf: renderPdf(report),
  };
}

module.exports = { analyze, buildReport, PRODUCT_NAME, PRODUCT_SLUG, DISCLAIMER };
