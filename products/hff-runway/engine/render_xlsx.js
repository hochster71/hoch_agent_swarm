// engine/render_xlsx.js
//
// Stage 5b: multi-tab XLSX workbook via exceljs.
// Tabs: Summary, Transactions, Categories, CashFlow, EstimatedTax, 1099.
// Every sheet carries the non-advice banner in row 1.

'use strict';

const { DISCLAIMER } = require('./constants');

function money(n) {
  return typeof n === 'number' ? n : n;
}

// Returns the array of strings placed into the workbook, so the advice linter can scan them.
function collectStrings(packet) {
  const out = [DISCLAIMER];
  const { rollup, cashflow, estTax, list1099, transactions } = packet;
  for (const t of transactions) out.push(t.description, t.category, t.rule || '');
  for (const r of rollup) out.push(r.category);
  for (const l of estTax.lines) out.push(String(l.label));
  for (const c of list1099) out.push(c.payee);
  out.push(String(cashflow.runwayMonths));
  return out;
}

async function renderXlsx(packet) {
  const ExcelJS = require('exceljs');
  const wb = new ExcelJS.Workbook();
  wb.creator = 'HFF Runway';
  wb.created = new Date(packet.generatedAt || '2026-01-01T00:00:00Z');

  const bannerRow = (ws, span) => {
    ws.mergeCells(1, 1, 1, span);
    const cell = ws.getCell(1, 1);
    cell.value = DISCLAIMER;
    cell.font = { italic: true, color: { argb: 'FF8A6D00' }, size: 9 };
    cell.alignment = { wrapText: true, vertical: 'middle' };
    ws.getRow(1).height = 34;
  };

  // --- Summary ---
  const sum = wb.addWorksheet('Summary');
  bannerRow(sum, 2);
  sum.getColumn(1).width = 46;
  sum.getColumn(2).width = 22;
  const cf = packet.cashflow;
  const et = packet.estTax;
  const summaryRows = [
    ['HFF Runway packet', ''],
    ['Generated (UTC)', packet.generatedAt],
    ['As-of date', cf.asOf],
    ['Transactions accepted', packet.transactions.length],
    ['Rows flagged (not parsed)', packet.rejected.length],
    ['', ''],
    ['30-day net cash flow', cf.windows.d30 ? cf.windows.d30.net : 0],
    ['60-day net cash flow', cf.windows.d60 ? cf.windows.d60.net : 0],
    ['90-day net cash flow', cf.windows.d90 ? cf.windows.d90.net : 0],
    ['Avg monthly burn', cf.avgMonthlyBurn],
    ['Cash on hand (input)', cf.cashOnHand == null ? 'not provided' : cf.cashOnHand],
    ['Runway (months)', cf.runwayMonths == null ? 'n/a (need cash on hand)' : cf.runwayMonths],
    ['', ''],
    ['Estimated annual tax', et.totalAnnualTax],
    ['Estimated quarterly payment', et.quarterlyPayment],
    ['1099 candidates (> $600)', packet.list1099.filter((c) => c.isCandidate).length],
  ];
  summaryRows.forEach((r) => sum.addRow(r));

  // --- Transactions ---
  const tx = wb.addWorksheet('Transactions');
  bannerRow(tx, 5);
  tx.addRow(['Date', 'Description', 'Amount (+in/-out)', 'Category', 'Rule']);
  tx.getRow(2).font = { bold: true };
  [12, 40, 18, 18, 20].forEach((w, i) => (tx.getColumn(i + 1).width = w));
  for (const t of packet.transactions) {
    tx.addRow([t.date, t.description, t.amount, t.category, t.rule || '']);
  }

  // --- Categories ---
  const cat = wb.addWorksheet('Categories');
  bannerRow(cat, 6);
  cat.addRow(['Category', 'Inflow', 'Outflow', 'Net', 'Count', '% of outflow']);
  cat.getRow(2).font = { bold: true };
  [24, 14, 14, 14, 8, 14].forEach((w, i) => (cat.getColumn(i + 1).width = w));
  for (const r of packet.rollup) {
    cat.addRow([r.category, r.inflow, r.outflow, r.net, r.count, r.pctOfOutflow]);
  }

  // --- CashFlow ---
  const flow = wb.addWorksheet('CashFlow');
  bannerRow(flow, 5);
  flow.addRow(['Window', 'Inflow', 'Outflow', 'Net', 'Txns']);
  flow.getRow(2).font = { bold: true };
  [16, 14, 14, 14, 10].forEach((w, i) => (flow.getColumn(i + 1).width = w));
  for (const key of ['d30', 'd60', 'd90']) {
    const w = cf.windows[key];
    if (w) flow.addRow([`${w.windowDays} days`, w.inflow, w.outflow, w.net, w.count]);
  }
  flow.addRow([]);
  flow.addRow(['Avg monthly net', cf.avgMonthlyNet]);
  flow.addRow(['Avg monthly burn', cf.avgMonthlyBurn]);
  flow.addRow(['Cash on hand', cf.cashOnHand == null ? 'not provided' : cf.cashOnHand]);
  flow.addRow(['Runway (months)', cf.runwayMonths == null ? 'n/a' : cf.runwayMonths]);

  // --- EstimatedTax ---
  const est = wb.addWorksheet('EstimatedTax');
  bannerRow(est, 2);
  est.getColumn(1).width = 58;
  est.getColumn(2).width = 20;
  est.addRow(['Estimated-tax worksheet (every input labeled; verify with your accountant)', '']);
  est.getRow(2).font = { bold: true };
  for (const l of et.lines) est.addRow([l.label, l.value]);

  // --- 1099 ---
  const nec = wb.addWorksheet('1099');
  bannerRow(nec, 5);
  nec.addRow(['Payee', 'Total paid', 'Payments', '1099 candidate (>$600)', 'Missing W-9?']);
  nec.getRow(2).font = { bold: true };
  [34, 14, 12, 22, 14].forEach((w, i) => (nec.getColumn(i + 1).width = w));
  for (const c of packet.list1099) {
    nec.addRow([c.payee, c.totalPaid, c.payments, c.isCandidate ? 'YES' : 'no', c.missingW9 ? 'YES' : 'no']);
  }
  if (packet.list1099.length === 0) nec.addRow(['(no contractor payments detected)', '', '', '', '']);

  const buf = await wb.xlsx.writeBuffer();
  return Buffer.from(buf);
}

module.exports = { renderXlsx, collectStrings };
