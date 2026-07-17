// engine/render_pdf.js
//
// Stage 5a: minimal, dependency-free one-page PDF summary.
// Produces a valid PDF 1.4 (single page, Helvetica) from an array of text lines.
// No external libraries — deterministic byte output.

'use strict';

// Escape text for a PDF literal string.
function esc(s) {
  return String(s)
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)')
    // PDF standard fonts are Latin-1; drop non-encodable chars to keep bytes valid.
    .replace(/[^\x20-\x7e]/g, '');
}

// lines: [{ text, size?, bold?, gap? }]
function buildContentStream(lines, pageHeight) {
  let y = pageHeight - 54;
  const parts = [];
  for (const ln of lines) {
    const size = ln.size || 10;
    const font = ln.bold ? '/F2' : '/F1';
    const gap = ln.gap != null ? ln.gap : size + 4;
    parts.push(`BT ${font} ${size} Tf 54 ${y} Td (${esc(ln.text)}) Tj ET`);
    y -= gap;
  }
  return parts.join('\n');
}

// renderPdf(lines) -> Buffer
function renderPdf(lines) {
  const pageWidth = 612; // US Letter
  const pageHeight = 792;
  const content = buildContentStream(lines, pageHeight);
  const contentBytes = Buffer.from(content, 'latin1');

  const objects = [];
  objects[1] = '<< /Type /Catalog /Pages 2 0 R >>';
  objects[2] = '<< /Type /Pages /Kids [3 0 R] /Count 1 >>';
  objects[3] =
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] ` +
    `/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>`;
  objects[4] = `<< /Length ${contentBytes.length} >>\nstream\n${content}\nendstream`;
  objects[5] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>';
  objects[6] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>';

  let pdf = '%PDF-1.4\n';
  const offsets = [];
  for (let i = 1; i < objects.length; i++) {
    offsets[i] = Buffer.byteLength(pdf, 'latin1');
    pdf += `${i} 0 obj\n${objects[i]}\nendobj\n`;
  }
  const xrefStart = Buffer.byteLength(pdf, 'latin1');
  const count = objects.length; // includes slot 0
  pdf += `xref\n0 ${count}\n`;
  pdf += `0000000000 65535 f \n`;
  for (let i = 1; i < count; i++) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${count} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return Buffer.from(pdf, 'latin1');
}

module.exports = { renderPdf };
