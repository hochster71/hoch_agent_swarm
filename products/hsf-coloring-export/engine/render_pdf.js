// engine/render_pdf.js
//
// HSF — Coloring Book Export — dependency-free multi-page coloring PDF.
//
// Extends the proven hff-invoice-aging single-page renderer to:
//   * multiple US-Letter pages (612x792),
//   * vector line-art (stroke-only paths from engine/motifs.js),
//   * OUTLINED headings (PDF text render mode 1 = stroke) kids can color in,
//   * a mandatory diagonal PREVIEW watermark on EVERY page unless the caller
//     (the entitlement-gated endpoint) explicitly passes watermarkFree:true.
//
// Deterministic byte output: no dates, no randomness, latin1 only.

'use strict';

const PAGE_W = 612;
const PAGE_H = 792;
const MARGIN = 54;

const WATERMARK_TEXT = 'PREVIEW - PURCHASE TO REMOVE WATERMARK';
const WATERMARK_FOOTER = 'Free preview - buy the export to print watermark-free. Story Studio / HSF.';

function esc(s) {
  return String(s)
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)')
    .replace(/[^\x20-\x7e]/g, '');
}

// crude Helvetica width estimate (avg 0.52em) for centering / wrapping
function textWidth(s, size) { return esc(s).length * size * 0.52; }

function wrap(text, size, maxWidth) {
  const words = String(text).split(/\s+/).filter(Boolean);
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

function filledText(x, y, size, text, opts) {
  const font = opts && opts.bold ? '/F2' : '/F1';
  return `BT ${font} ${size} Tf 0 Tr ${f2(x)} ${f2(y)} Td (${esc(text)}) Tj ET`;
}

// Outlined (colorable) text: render mode 1 = stroke glyph outlines.
function outlineText(x, y, size, text, lineWidth) {
  return [
    'q', `${lineWidth || 1.1} w`, '0 0 0 RG',
    `BT /F2 ${size} Tf 1 Tr ${f2(x)} ${f2(y)} Td (${esc(text)}) Tj ET`,
    'Q',
  ].join('\n');
}

function centeredOutline(y, size, text, lw) {
  const x = Math.max(MARGIN, (PAGE_W - textWidth(text, size)) / 2);
  return outlineText(x, y, size, text, lw);
}
function centeredFilled(y, size, text, opts) {
  const x = Math.max(MARGIN, (PAGE_W - textWidth(text, size)) / 2);
  return filledText(x, y, size, text, opts);
}

function f2(n) { return Number(Number(n).toFixed(2)); }

function watermarkOps() {
  // Diagonal outlined watermark, light gray, across the page center + footer.
  // Drawn LAST so it cannot be hidden by page art.
  const c = 0.7071;
  return [
    'q', '0.75 G', '0.75 g', '1.4 w',
    `${c} ${c} ${-c} ${c} 96 180 cm`,
    `BT /F2 30 Tf 1 Tr 0 0 Td (${esc(WATERMARK_TEXT)}) Tj ET`,
    `BT /F2 30 Tf 1 Tr 0 -220 Td (${esc(WATERMARK_TEXT)}) Tj ET`,
    'Q',
    'q', '0.35 g',
    `BT /F1 9 Tf 0 Tr ${f2((PAGE_W - textWidth(WATERMARK_FOOTER, 9)) / 2)} 20 Td (${esc(WATERMARK_FOOTER)}) Tj ET`,
    'Q',
  ].join('\n');
}

function pageFrame() {
  // rounded-feel double border kids can color
  return [
    'q', '2 w', '0 0 0 RG',
    `${MARGIN - 18} ${MARGIN - 18} ${PAGE_W - 2 * (MARGIN - 18)} ${PAGE_H - 2 * (MARGIN - 18)} re S`,
    '0.8 w',
    `${MARGIN - 10} ${MARGIN - 10} ${PAGE_W - 2 * (MARGIN - 10)} ${PAGE_H - 2 * (MARGIN - 10)} re S`,
    'Q',
  ].join('\n');
}

// ---- page builders --------------------------------------------------------

function coverPage(title, subtitle, coverMotif) {
  const ops = [pageFrame(), 'q', '2 w', '0 0 0 RG'];
  ops.push(coverMotif(MARGIN + 20, 300, PAGE_W - 2 * (MARGIN + 20), 300));
  ops.push('Q');
  const titleLines = wrap(title, 30, PAGE_W - 2 * MARGIN - 20);
  let y = 250;
  for (const ln of titleLines.slice(0, 3)) { ops.push(centeredOutline(y, 30, ln, 1.3)); y -= 40; }
  ops.push(centeredFilled(y - 6, 13, subtitle, { bold: false }));
  ops.push(centeredFilled(y - 30, 11, 'A coloring book made from my story', {}));
  ops.push(centeredFilled(96, 11, 'Colored by: ____________________________', {}));
  return ops.join('\n');
}

function scenePage(scene, index, total, motif) {
  const ops = [pageFrame()];
  // kicker (small outline) + heading (big outline, wrapped to 2 lines)
  ops.push(centeredOutline(PAGE_H - 96, 13, String(scene.kicker || '').toUpperCase(), 0.8));
  const heading = scene.heading || scene.kicker || 'My Story';
  const hLines = wrap(heading, 22, PAGE_W - 2 * MARGIN - 10).slice(0, 2);
  let y = PAGE_H - 130;
  for (const ln of hLines) { ops.push(centeredOutline(y, 22, ln, 1.1)); y -= 30; }
  // the big drawing
  ops.push('q', '2.2 w', '0 0 0 RG', '1 J 1 j');
  ops.push(motif(MARGIN + 6, 170, PAGE_W - 2 * (MARGIN + 6), y - 190));
  ops.push('Q');
  // caption: first wrapped lines of the body, small filled text (read-aloud line)
  const capLines = wrap(scene.body || '', 10.5, PAGE_W - 2 * MARGIN - 20).slice(0, 3);
  let cy = 138;
  for (const ln of capLines) { ops.push(centeredFilled(cy, 10.5, ln, {})); cy -= 15; }
  ops.push(centeredFilled(66, 10, `Page ${index + 1} of ${total}`, {}));
  return ops.join('\n');
}

function backPage(title) {
  const ops = [pageFrame()];
  ops.push(centeredOutline(PAGE_H - 150, 24, 'THE END', 1.2));
  ops.push('q', '2 w', '0 0 0 RG');
  const { backCover } = require('./motifs');
  ops.push(backCover(MARGIN + 40, 260, PAGE_W - 2 * (MARGIN + 40), 300));
  ops.push('Q');
  const t = wrap(`This certifies that this copy of "${title}" was colored with great care by`, 11, PAGE_W - 2 * MARGIN - 30);
  let y = 210;
  for (const ln of t) { ops.push(centeredFilled(y, 11, ln, {})); y -= 16; }
  ops.push(centeredFilled(y - 14, 12, '____________________________', {}));
  ops.push(centeredFilled(96, 9, 'Made with Story Studio - Hoch Storybook Factory', {}));
  return ops.join('\n');
}

// ---- document assembly ----------------------------------------------------

// pages: array of content-op strings (one per page). watermarkFree: boolean.
function renderColoringPdf(pageContents, watermarkFree) {
  const contents = pageContents.map((ops) =>
    watermarkFree === true ? ops : ops + '\n' + watermarkOps()
  );

  const n = contents.length;
  // object layout: 1 catalog, 2 pages, 3..(2+n) page objs, (3+n)..(2+2n) content objs, then F1, F2
  const pageObjStart = 3;
  const contentObjStart = 3 + n;
  const fontF1 = 3 + 2 * n;
  const fontF2 = 4 + 2 * n;

  const objects = [];
  objects[1] = '<< /Type /Catalog /Pages 2 0 R >>';
  const kids = [];
  for (let i = 0; i < n; i++) kids.push(`${pageObjStart + i} 0 R`);
  objects[2] = `<< /Type /Pages /Kids [${kids.join(' ')}] /Count ${n} >>`;
  for (let i = 0; i < n; i++) {
    objects[pageObjStart + i] =
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PAGE_W} ${PAGE_H}] ` +
      `/Resources << /Font << /F1 ${fontF1} 0 R /F2 ${fontF2} 0 R >> >> /Contents ${contentObjStart + i} 0 R >>`;
    const bytes = Buffer.from(contents[i], 'latin1');
    objects[contentObjStart + i] = `<< /Length ${bytes.length} >>\nstream\n${contents[i]}\nendstream`;
  }
  objects[fontF1] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>';
  objects[fontF2] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>';

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

module.exports = {
  renderColoringPdf,
  coverPage,
  scenePage,
  backPage,
  WATERMARK_TEXT,
  PAGE_W,
  PAGE_H,
  esc,
};
