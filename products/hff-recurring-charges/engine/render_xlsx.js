// engine/render_xlsx.js
//
// HFF — Recurring Charge Finder — dependency-free XLSX writer.
//
// Builds a real SpreadsheetML (.xlsx) package by hand: [Content_Types].xml,
// package + workbook rels, styles, and one worksheet per tab. Cells use
// inline strings (t="inlineStr") so no sharedStrings table is needed. This
// removes the exceljs dependency the earlier HFF product carried, so the
// engine and its tests run with NO npm install.
//
// Sheets: Summary | Recurring Charges | All Occurrences | Flagged Rows
'use strict';

const { buildZip } = require('./zip');
const { DISCLAIMER } = require('./constants');

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;')
    // strip XML-illegal control chars
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '');
}

function colName(i) {
  let n = i + 1;
  let s = '';
  while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

// cell: number -> numeric cell; string -> inline string. styleIdx optional.
function cellXml(ref, value, styleIdx) {
  const s = styleIdx ? ` s="${styleIdx}"` : '';
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `<c r="${ref}"${s}><v>${value}</v></c>`;
  }
  if (value === null || value === undefined || value === '') return `<c r="${ref}"${s}/>`;
  return `<c r="${ref}"${s} t="inlineStr"><is><t xml:space="preserve">${esc(value)}</t></is></c>`;
}

function sheetXml(rows, opts) {
  const options = opts || {};
  const widths = options.widths || [];
  const colsXml = widths.length
    ? `<cols>${widths.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join('')}</cols>`
    : '';
  const body = rows.map((row, r) => {
    const cells = row.map((v, c) => {
      // style 1 = bold header row, style 2 = money
      let style = 0;
      if (options.headerRows && r < options.headerRows) style = 1;
      else if (options.moneyCols && options.moneyCols.includes(c) && typeof v === 'number') style = 2;
      return cellXml(colName(c) + (r + 1), v, style);
    }).join('');
    return `<row r="${r + 1}">${cells}</row>`;
  }).join('');
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
    `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
    colsXml +
    `<sheetData>${body}</sheetData></worksheet>`;
}

const STYLES_XML = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;

function buildWorkbook(sheets) {
  const files = [];
  const ctOverrides = sheets.map((_, i) =>
    `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`
  ).join('');

  files.push({
    name: '[Content_Types].xml',
    data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
      `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
      `<Default Extension="xml" ContentType="application/xml"/>` +
      `<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>` +
      `<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>` +
      ctOverrides + `</Types>`,
  });

  files.push({
    name: '_rels/.rels',
    data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>` +
      `</Relationships>`,
  });

  files.push({
    name: 'xl/workbook.xml',
    data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ` +
      `xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>` +
      sheets.map((s, i) => `<sheet name="${esc(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('') +
      `</sheets></workbook>`,
  });

  files.push({
    name: 'xl/_rels/workbook.xml.rels',
    data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>` +
      `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
      sheets.map((_, i) =>
        `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`
      ).join('') +
      `<Relationship Id="rId${sheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>` +
      `</Relationships>`,
  });

  files.push({ name: 'xl/styles.xml', data: STYLES_XML });
  sheets.forEach((s, i) => {
    files.push({ name: `xl/worksheets/sheet${i + 1}.xml`, data: sheetXml(s.rows, s.opts) });
  });

  return buildZip(files);
}

// ------------------------------------------------------------ report mapping

function renderXlsx(report) {
  const { summary, detection, skipped } = report;

  const summaryRows = [
    ['Recurring Charge Finder — Summary'],
    [],
    ['Observed window', `${summary.window.start || 'n/a'} to ${summary.window.end || 'n/a'}`],
    ['Recurring patterns observed', summary.counts.recurringPatterns],
    ['Charge rows read', summary.counts.chargeRows],
    ['Credit / refund rows excluded', summary.counts.creditRows],
    ['Rows flagged as unreadable', summary.counts.skippedRows],
    ['One-off / non-recurring merchants', summary.counts.oneOffMerchants],
    [],
    ['Combined monthly equivalent', summary.totals.monthlyEquivalent],
    ['Combined annualized', summary.totals.annualized],
    [],
    ['Confidence: high', summary.byConfidence.high],
    ['Confidence: medium', summary.byConfidence.medium],
    ['Confidence: low', summary.byConfidence.low],
    [],
    ['By cadence', 'Patterns', 'Annualized'],
  ];
  for (const [cad, v] of Object.entries(summary.byCadence)) summaryRows.push([cad, v.count, v.annualized]);
  summaryRows.push([], ['Observations']);
  for (const n of summary.notes) summaryRows.push([n]);
  summaryRows.push([], ['Disclaimer'], [DISCLAIMER]);

  const recHeader = ['Merchant (as written)', 'Grouping key', 'Cadence', 'Occurrences', 'Confidence',
    'Typical amount', 'First amount', 'Latest amount', 'Change %', 'Monthly equivalent',
    'Annualized', 'Median interval (days)', 'First seen', 'Last seen', 'Days since last', 'No charge since expected', 'Overlap tag'];
  const recRows = [recHeader].concat(detection.recurring.map((r) => ([
    r.label, r.merchantKey, r.cadence, r.occurrences, r.confidence,
    r.typicalAmount, r.firstAmount, r.latestAmount, r.amountChangePct, r.monthlyEquivalent,
    r.annualizedAmount, r.medianIntervalDays, r.firstSeen, r.lastSeen, r.daysSinceLastSeen,
    r.noChargeSinceExpected ? 'yes' : 'no', r.overlapTag || '',
  ])));

  const occHeader = ['Grouping key', 'CSV line', 'Date', 'Amount', 'Description'];
  const occRows = [occHeader];
  for (const r of detection.recurring) {
    for (const o of r.occurrenceRows) occRows.push([r.merchantKey, o.line, o.date, o.amount, o.description]);
  }

  const skHeader = ['CSV line', 'Reason', 'Value seen', 'Raw row'];
  const skRows = [skHeader].concat((skipped || []).map((s) => ([
    s.line, s.reason, s.value, (s.row || []).join(' | '),
  ])));
  if (skRows.length === 1) skRows.push(['—', 'none', 'Every data row was read successfully.', '']);

  return buildWorkbook([
    { name: 'Summary', rows: summaryRows, opts: { headerRows: 1, widths: [42, 18, 16], moneyCols: [1, 2] } },
    { name: 'Recurring Charges', rows: recRows, opts: { headerRows: 1, widths: [30, 22, 12, 12, 12, 14, 14, 14, 10, 18, 14, 18, 12, 12, 14, 20, 16], moneyCols: [5, 6, 7, 9, 10] } },
    { name: 'All Occurrences', rows: occRows, opts: { headerRows: 1, widths: [22, 10, 12, 14, 44], moneyCols: [3] } },
    { name: 'Flagged Rows', rows: skRows, opts: { headerRows: 1, widths: [10, 22, 24, 60] } },
  ]);
}

module.exports = { renderXlsx, buildWorkbook, sheetXml, esc, colName };
