// engine/render_pdf.js
//
// HFF — Vendor Spend Rollup — dependency-free one-page PDF.
// Adapted from the proven hff-client-concentration / hff-hourly-rate renderer:
// hand-assembled PDF 1.4 objects, Helvetica base-14 fonts, latin1 bytes, no npm
// dependency and no randomness (byte-deterministic for a given report).
'use strict';

const { DISCLAIMER, PRODUCT_NAME } = require('./constants');
const { money, pct } = require('./summary');

const PAGE_W = 612;
const PAGE_H = 792;
const MARGIN = 48;

function esc(s) {
  return String(s)
    .replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
    .replace(/[^\x20-\x7e]/g, '');
}
function f2(n) { return Number(Number(n).toFixed(2)); }
function textWidth(s, size) { return esc(s).length * size * 0.5; }

function text(x, y, size, s, bold, gray) {
  const font = bold ? '/F2' : '/F1';
  const g = gray === undefined ? 0 : gray;
  return `q ${g} g BT ${font} ${size} Tf ${f2(x)} ${f2(y)} Td (${esc(s)}) Tj ET Q`;
}
function rightText(xRight, y, size, s, bold, gray) {
  return text(xRight - textWidth(s, size), y, size, s, bold, gray);
}
function line(x1, y1, x2, y2, w, gray) {
  return `q ${gray === undefined ? 0.7 : gray} G ${w || 0.6} w ${f2(x1)} ${f2(y1)} m ${f2(x2)} ${f2(y2)} l S Q`;
}
function bar(x, y, w, h, gray) {
  return `q ${gray === undefined ? 0.55 : gray} g ${f2(x)} ${f2(y)} ${f2(w)} ${f2(h)} re f Q`;
}
function wrap(s, size, maxWidth) {
  const words = String(s).split(/\s+/).filter(Boolean);
  const lines = [];
  let cur = '';
  for (const w of words) {
    const next = cur ? cur + ' ' + w : w;
    if (textWidth(next, size) > maxWidth && cur) { lines.push(cur); cur = w; }
    else cur = next;
  }
  if (cur) lines.push(cur);
  return lines;
}
function truncate(s, size, maxWidth) {
  let out = String(s);
  while (out.length > 3 && textWidth(out, size) > maxWidth) out = out.slice(0, -1);
  return out.length < String(s).length ? out.slice(0, -1) + '.' : out;
}

function renderPdf(report) {
  const { summary, analysis } = report;
  const ops = [];
  let y = PAGE_H - MARGIN;

  ops.push(text(MARGIN, y, 20, PRODUCT_NAME, true));
  y -= 18;
  ops.push(text(MARGIN, y, 9.5,
    `Observed window ${summary.window.start} to ${summary.window.end}  •  ` +
    `${summary.counts.payments} payments read  •  ${summary.counts.skippedRows} rows flagged`,
    false, 0.35));
  y -= 14;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 1, 0.2));
  y -= 26;

  // headline figures
  ops.push(text(MARGIN, y, 11, 'Net spend', false, 0.3));
  ops.push(text(MARGIN, y - 22, 22, money(summary.spend.net), true));
  ops.push(text(MARGIN + 210, y, 11, 'Vendors', false, 0.3));
  ops.push(text(MARGIN + 210, y - 22, 22, String(summary.counts.vendors), true));
  ops.push(text(MARGIN + 330, y, 11, 'Top vendor share', false, 0.3));
  ops.push(text(MARGIN + 330, y - 22, 22, pct(summary.concentration.top1SharePct), true));
  y -= 46;
  const sub =
    `${money(summary.spend.grossPaid)} gross less ${money(summary.spend.refundTotal)} in credits  •  ` +
    `${money(summary.spend.averagePerMonth)} average per month across ${summary.counts.monthsObserved} months  •  ` +
    `${summary.concentration.vendorsForHalfOfSpend} vendor(s) make up the first 50%`;
  ops.push(text(MARGIN, y, 8.5, sub, false, 0.4));
  y -= 14;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 0.6, 0.75));
  y -= 22;

  // vendor table with a net-share bar
  const COLS = { rank: MARGIN, vendor: MARGIN + 24, netCol: MARGIN + 250, barX: MARGIN + 300, pays: MARGIN + 452, share: MARGIN + 516 };
  ops.push(text(COLS.rank, y, 9, '#', true, 0.35));
  ops.push(text(COLS.vendor, y, 9, 'VENDOR', true, 0.35));
  ops.push(rightText(COLS.netCol + 40, y, 9, 'NET', true, 0.35));
  ops.push(rightText(COLS.pays + 34, y, 9, 'PMTS', true, 0.35));
  ops.push(rightText(COLS.share + 32, y, 9, 'SHARE', true, 0.35));
  y -= 6;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 0.6, 0.75));
  y -= 15;

  const MAX_ROWS = 20;
  const shown = analysis.vendors.slice(0, MAX_ROWS);
  const maxNet = shown.length ? Math.max(...shown.map((v) => Math.abs(v.net))) : 0;
  const BAR_MAX = 136;

  for (const v of shown) {
    ops.push(text(COLS.rank, y, 9, String(v.rank), false, 0.45));
    ops.push(text(COLS.vendor, y, 9.5, truncate(v.label, 9.5, 215)));
    ops.push(rightText(COLS.netCol + 40, y, 9.5, money(v.net), true));
    if (maxNet > 0) {
      const w = Math.max(1, (Math.abs(v.net) / maxNet) * BAR_MAX);
      ops.push(bar(COLS.barX, y - 1, w, 6, 0.55));
    }
    ops.push(rightText(COLS.pays + 34, y, 9, String(v.paymentCount), false, 0.35));
    ops.push(rightText(COLS.share + 32, y, 8.5, pct(v.netSharePct), false, 0.35));
    y -= 14;
  }
  if (analysis.vendors.length > MAX_ROWS) {
    ops.push(text(MARGIN, y, 9,
      `+ ${analysis.vendors.length - MAX_ROWS} more vendor(s) on the "Vendors" sheet of the workbook.`, false, 0.4));
    y -= 14;
  }

  y -= 8;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 0.6, 0.75));
  y -= 18;

  ops.push(text(MARGIN, y, 10, 'Observations', true));
  y -= 14;
  const notes = summary.notes.slice(0, 8);
  for (const n of notes) {
    for (const ln of wrap('• ' + n, 8.5, PAGE_W - 2 * MARGIN).slice(0, 2)) {
      ops.push(text(MARGIN, y, 8.5, ln, false, 0.25));
      y -= 11;
    }
    if (y < MARGIN + 84) break;
  }
  if (!notes.length) { ops.push(text(MARGIN, y, 8.5, '• Nothing further to note in this file.', false, 0.25)); y -= 11; }

  // disclaimer footer
  let dy = MARGIN + 62;
  ops.push(line(MARGIN, dy + 12, PAGE_W - MARGIN, dy + 12, 0.6, 0.75));
  for (const ln of wrap(DISCLAIMER, 7.5, PAGE_W - 2 * MARGIN)) {
    ops.push(text(MARGIN, dy, 7.5, ln, false, 0.4));
    dy -= 10;
  }
  ops.push(text(MARGIN, MARGIN - 14, 7.5,
    'Hoch Finance Factory — organizational tooling. Generated from the file you supplied.', false, 0.55));

  return assemble(ops.join('\n'));
}

function assemble(content) {
  const objects = [];
  objects[1] = '<< /Type /Catalog /Pages 2 0 R >>';
  objects[2] = '<< /Type /Pages /Kids [3 0 R] /Count 1 >>';
  objects[3] = `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PAGE_W} ${PAGE_H}] ` +
    `/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>`;
  const bytes = Buffer.byteLength(content, 'latin1');
  objects[4] = `<< /Length ${bytes} >>\nstream\n${content}\nendstream`;
  objects[5] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>';
  objects[6] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>';

  let pdf = '%PDF-1.4\n';
  const offsets = [];
  for (let i = 1; i < objects.length; i++) {
    offsets[i] = Buffer.byteLength(pdf, 'latin1');
    pdf += `${i} 0 obj\n${objects[i]}\nendobj\n`;
  }
  const xrefStart = Buffer.byteLength(pdf, 'latin1');
  const count = objects.length;
  pdf += `xref\n0 ${count}\n0000000000 65535 f \n`;
  for (let i = 1; i < count; i++) pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  pdf += `trailer\n<< /Size ${count} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;
  return Buffer.from(pdf, 'latin1');
}

module.exports = { renderPdf, PAGE_W, PAGE_H, esc, wrap };
