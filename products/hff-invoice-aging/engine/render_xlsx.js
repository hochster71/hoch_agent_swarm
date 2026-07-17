// engine/render_xlsx.js
//
// Stage 5b: multi-tab XLSX workbook via exceljs.
// Tabs: Summary, Aging (per-invoice), ByCustomer, Buckets.
// Every sheet carries the non-advice banner in row 1.

'use strict';

const { DISCLAIMER, AGING_BUCKETS } = require('./constants');

// Returns every string placed into the workbook, so the advice linter can scan them.
function collectStrings(report) {
  const out = [DISCLAIMER];
  for (const inv of report.aging.aged) out.push(inv.customer, inv.invoice, inv.bucketLabel, inv.statusRaw || '');
  for (const c of report.byCustomer) out.push(c.customer);
  for (const b of report.aging.buckets) out.push(b.label);
  return out;
}

async function renderXlsx(report) {
  const ExcelJS = require('exceljs');
  const wb = new ExcelJS.Workbook();
  wb.creator = 'HFF Invoice Aging';
  wb.created = new Date(report.generatedAt || '2026-01-01T00:00:00Z');

  const bannerRow = (ws, span) => {
    ws.mergeCells(1, 1, 1, span);
    const cell = ws.getCell(1, 1);
    cell.value = DISCLAIMER;
    cell.font = { italic: true, color: { argb: 'FF8A6D00' }, size: 9 };
    cell.alignment = { wrapText: true, vertical: 'middle' };
    ws.getRow(1).height = 42;
  };

  const ag = report.aging;

  // --- Summary ---
  const sum = wb.addWorksheet('Summary');
  bannerRow(sum, 2);
  sum.getColumn(1).width = 44;
  sum.getColumn(2).width = 22;
  const rows = [
    ['HFF Invoice Aging Snapshot', ''],
    ['Generated (UTC)', report.generatedAt],
    ['As-of date', ag.asOf || 'n/a'],
    ['Outstanding invoices', ag.outstandingCount],
    ['Paid / void (excluded)', ag.paidCount],
    ['Rows flagged (not parsed)', report.rejected.length],
    ['', ''],
    ['Total outstanding', ag.totalOutstanding],
  ];
  for (const b of ag.buckets) rows.push([b.label, b.balance]);
  rows.forEach((r) => sum.addRow(r));

  // --- Buckets ---
  const bk = wb.addWorksheet('Buckets');
  bannerRow(bk, 4);
  bk.addRow(['Aging bucket', 'Balance', 'Invoices', '% of outstanding']);
  bk.getRow(2).font = { bold: true };
  [24, 16, 12, 18].forEach((w, i) => (bk.getColumn(i + 1).width = w));
  for (const b of ag.buckets) bk.addRow([b.label, b.balance, b.count, b.pctOfOutstanding]);
  bk.addRow(['TOTAL', ag.totalOutstanding, ag.outstandingCount, ag.totalOutstanding > 0 ? 100 : 0]);

  // --- ByCustomer (who owes what) ---
  const cust = wb.addWorksheet('ByCustomer');
  bannerRow(cust, 9);
  const custHead = ['Customer', 'Outstanding', 'Invoices', 'Oldest days past due'];
  for (const b of AGING_BUCKETS) custHead.push(b.label);
  cust.addRow(custHead);
  cust.getRow(2).font = { bold: true };
  [28, 16, 10, 20, 16, 14, 14, 14, 14].forEach((w, i) => (cust.getColumn(i + 1).width = w));
  for (const c of report.byCustomer) {
    const row = [c.customer, c.outstanding, c.count, c.oldestDaysPastDue];
    for (const b of AGING_BUCKETS) row.push(c.buckets[b.key] || 0);
    cust.addRow(row);
  }
  if (report.byCustomer.length === 0) cust.addRow(['(no outstanding invoices)', '', '', '']);

  // --- Aging (per-invoice detail) ---
  const det = wb.addWorksheet('Aging');
  bannerRow(det, 7);
  det.addRow(['Invoice', 'Customer', 'Issue date', 'Due date', 'Balance', 'Days past due', 'Bucket']);
  det.getRow(2).font = { bold: true };
  [16, 26, 14, 14, 14, 14, 18].forEach((w, i) => (det.getColumn(i + 1).width = w));
  for (const inv of ag.aged) {
    det.addRow([inv.invoice, inv.customer, inv.issueDate || '', inv.dueDate, inv.balance, inv.daysPastDue, inv.bucketLabel]);
  }
  if (ag.aged.length === 0) det.addRow(['(no outstanding invoices)', '', '', '', '', '', '']);

  const buf = await wb.xlsx.writeBuffer();
  return Buffer.from(buf);
}

module.exports = { renderXlsx, collectStrings };
