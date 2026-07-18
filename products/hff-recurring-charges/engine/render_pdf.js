// engine/render_pdf.js
//
// HFF — Recurring Charge Finder — dependency-free one-page PDF summary.
// Adapted from the proven hff-invoice-aging / hsf-coloring-export renderer:
// hand-assembled PDF 1.4 objects, Helvetica base-14 fonts, latin1 bytes, no
// npm dependency and no randomness (byte-deterministic for a given report).
'use strict';

const { DISCLAIMER, PRODUCT_NAME } = require('./constants');
const { money } = require('./summary');

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
  const { summary, detection } = report;
  const ops = [];
  let y = PAGE_H - MARGIN;

  ops.push(text(MARGIN, y, 20, PRODUCT_NAME, true));
  y -= 18;
  ops.push(text(MARGIN, y, 9.5, `Observed window ${summary.window.start || 'n/a'} to ${summary.window.end || 'n/a'}  •  ${summary.counts.chargeRows} charge rows read  •  ${summary.counts.skippedRows} rows flagged`, false, 0.35));
  y -= 14;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 1, 0.2));
  y -= 26;

  // headline figures
  ops.push(text(MARGIN, y, 11, 'Recurring patterns observed', false, 0.3));
  ops.push(text(MARGIN, y - 22, 24, String(summary.counts.recurringPatterns), true));
  ops.push(text(MARGIN + 190, y, 11, 'Monthly equivalent', false, 0.3));
  ops.push(text(MARGIN + 190, y - 22, 24, money(summary.totals.monthlyEquivalent), true));
  ops.push(text(MARGIN + 380, y, 11, 'Annualized', false, 0.3));
  ops.push(text(MARGIN + 380, y - 22, 24, money(summary.totals.annualized), true));
  y -= 48;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 0.6, 0.75));
  y -= 22;

  // table
  const COLS = { merchant: MARGIN, cadence: MARGIN + 210, occ: MARGIN + 285, typical: MARGIN + 360, annual: MARGIN + 450, conf: MARGIN + 520 };
  ops.push(text(COLS.merchant, y, 9, 'MERCHANT', true, 0.35));
  ops.push(text(COLS.cadence, y, 9, 'CADENCE', true, 0.35));
  ops.push(rightText(COLS.occ + 40, y, 9, 'SEEN', true, 0.35));
  ops.push(rightText(COLS.typical + 60, y, 9, 'TYPICAL', true, 0.35));
  ops.push(rightText(COLS.annual + 60, y, 9, 'ANNUALIZED', true, 0.35));
  ops.push(text(COLS.conf, y, 9, 'CONF', true, 0.35));
  y -= 6;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 0.6, 0.75));
  y -= 15;

  const MAX_ROWS = 22;
  const shown = detection.recurring.slice(0, MAX_ROWS);
  for (const r of shown) {
    ops.push(text(COLS.merchant, y, 9.5, truncate(r.label, 9.5, 200)));
    ops.push(text(COLS.cadence, y, 9.5, r.cadence, false, 0.3));
    ops.push(rightText(COLS.occ + 40, y, 9.5, String(r.occurrences)));
    ops.push(rightText(COLS.typical + 60, y, 9.5, money(r.typicalAmount)));
    ops.push(rightText(COLS.annual + 60, y, 9.5, money(r.annualizedAmount), true));
    ops.push(text(COLS.conf, y, 8.5, r.confidence, false, 0.4));
    y -= 14;
  }
  if (detection.recurring.length > MAX_ROWS) {
    ops.push(text(MARGIN, y, 9, `+ ${detection.recurring.length - MAX_ROWS} more pattern(s) on the "Recurring Charges" sheet of the workbook.`, false, 0.4));
    y -= 14;
  }
  if (shown.length === 0) {
    ops.push(text(MARGIN, y, 10, 'No repeating charge pattern was observed in this file.', false, 0.3));
    y -= 16;
  }

  y -= 8;
  ops.push(line(MARGIN, y, PAGE_W - MARGIN, y, 0.6, 0.75));
  y -= 18;

  // observations
  ops.push(text(MARGIN, y, 10, 'Observations', true));
  y -= 14;
  const notes = summary.notes.slice(0, 8);
  for (const n of notes) {
    for (const ln of wrap('• ' + n, 8.5, PAGE_W - 2 * MARGIN).slice(0, 2)) {
      ops.push(text(MARGIN, y, 8.5, ln, false, 0.25));
      y -= 11;
    }
    if (y < MARGIN + 74) break;
  }
  if (!notes.length) { ops.push(text(MARGIN, y, 8.5, '• Nothing further to flag in this file.', false, 0.25)); y -= 11; }

  // disclaimer footer
  let dy = MARGIN + 52;
  ops.push(line(MARGIN, dy + 12, PAGE_W - MARGIN, dy + 12, 0.6, 0.75));
  for (const ln of wrap(DISCLAIMER, 7.5, PAGE_W - 2 * MARGIN)) {
    ops.push(text(MARGIN, dy, 7.5, ln, false, 0.4));
    dy -= 10;
  }
  ops.push(text(MARGIN, MARGIN - 14, 7.5, 'Hoch Finance Factory — organizational tooling. Generated from the file you supplied.', false, 0.55));

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
