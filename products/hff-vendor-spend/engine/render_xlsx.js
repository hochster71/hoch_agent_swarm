// engine/render_xlsx.js
//
// HFF — Vendor Spend Rollup — dependency-free XLSX writer.
//
// Builds a real SpreadsheetML (.xlsx) package by hand: [Content_Types].xml,
// package + workbook rels, styles, and one worksheet per tab. Cells use inline
// strings (t="inlineStr") so no sharedStrings table is needed, which means the
// engine and its tests run with NO npm install.
//
// Sheets: Summary | Vendors | Monthly | Categories | All Payments | Flagged Rows
'use strict';

const { buildZip } = require('./zip');
const { DISCLAIMER } = require('./constants');

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;')
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '');
}

function colName(i) {
  let n = i + 1;
  let s = '';
  while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

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
      let style = 0;
      if (options.headerRows && r < options.headerRows) style = 1;
      else if (options.moneyCols && options.moneyCols.includes(c) && typeof v === 'number') style = 2;
      else if (options.pctCols && options.pctCols.includes(c) && typeof v === 'number') style = 3;
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
<numFmts count="2"><numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00"/><numFmt numFmtId="165" formatCode="0.0&quot;%&quot;"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
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
  const { summary, analysis, skipped } = report;

  const summaryRows = [
    ['Vendor Spend Rollup — Summary'],
    [],
    ['Observed window', `${summary.window.start} to ${summary.window.end}`],
    ['Calendar months observed', summary.counts.monthsObserved],
    ['Days spanned', summary.window.spanDays],
    ['Vendors named in file', summary.counts.vendors],
    ['Payments read', summary.counts.payments],
    ['Refund / credit rows read', summary.counts.refunds],
    ['Rows flagged as unreadable', summary.counts.skippedRows],
    [],
    ['Gross paid out', summary.spend.grossPaid],
    ['Refunds / credits', summary.spend.refundTotal],
    ['Net spend', summary.spend.net],
    ['Average net per observed month', summary.spend.averagePerMonth],
    ['Average payment', summary.spend.averagePayment],
    [],
    ['Concentration (arithmetic over this file only)'],
    ['Top vendor share %', summary.concentration.top1SharePct],
    ['Top 3 share %', summary.concentration.top3SharePct],
    ['Top 5 share %', summary.concentration.top5SharePct],
    ['Top 10 share %', summary.concentration.top10SharePct],
    ['HHI', summary.concentration.hhi],
    ['HHI scale', summary.concentration.hhiScale],
    ['Effective vendor count', summary.concentration.effectiveVendorCount],
    ['Vendors making up the first 50% of net spend', summary.concentration.vendorsForHalfOfSpend],
    ['Vendors making up the first 80% of net spend', summary.concentration.vendorsForEightyPctOfSpend],
    [],
    ['Vendors with a measurable payment cadence', summary.counts.recurringVendors],
    ['Vendors quiet vs their own rhythm', summary.counts.quietVendors],
    ['Vendor buckets that merged spellings', summary.counts.mergedVendors],
  ];
  if (summary.currencies && summary.currencies.length) {
    summaryRows.push(['Currencies named in file', summary.currencies.join(', ')]);
  }
  summaryRows.push([], ['Observations']);
  for (const n of summary.notes) summaryRows.push([n]);
  summaryRows.push([], ['Disclaimer'], [DISCLAIMER]);

  const vendorHeader = [
    'Rank', 'Vendor (as written)', 'Grouping key', 'Net spend', 'Share of net %',
    'Gross paid', 'Refunds', 'Payments', 'Refund rows',
    'Smallest payment', 'Median payment', 'Largest payment',
    'Median gap (days)', 'Days since last payment', 'Quiet vs own rhythm',
    'First to last drift', 'Drift %',
    'First payment', 'Last payment', 'Months active', 'Categories seen', 'Spellings merged',
  ];
  const vendorRows = [vendorHeader].concat(analysis.vendors.map((v) => ([
    v.rank, v.label, v.vendorKey, v.net, v.netSharePct,
    v.grossPaid, v.refundTotal, v.paymentCount, v.refundCount,
    v.minPayment, v.medianPayment, v.maxPayment,
    v.medianGapDays === null ? '' : v.medianGapDays,
    v.daysSinceLastPayment,
    v.quietVsOwnRhythm ? 'yes' : '',
    v.driftAmount === null ? '' : v.driftAmount,
    v.driftPct === null ? '' : v.driftPct,
    v.firstPayment, v.lastPayment, v.monthsActive,
    v.categories.join(' / '),
    v.spellingCount > 1 ? v.spellings.join(' / ') : '',
  ])));

  const monthHeader = ['Month', 'Net spend', 'Gross paid', 'Refunds', 'Payments',
    'Active vendors', 'Largest vendor that month', 'Their net'];
  const monthRows = [monthHeader].concat(analysis.monthly.map((m) => ([
    m.month, m.net, m.grossPaid, m.refunds, m.paymentCount,
    m.activeVendors, m.topVendor, m.topVendorNet,
  ])));

  const catHeader = ['Category (as written in file)', 'Net spend', 'Share of net %'];
  const catRows = [catHeader].concat(analysis.categories.map((c) => ([
    c.category, c.net, c.netSharePct,
  ])));
  if (catRows.length === 1) {
    catRows.push(['—', '', '']);
    catRows.push(['This file has no category column, so no category rollup could be produced.']);
  }

  const payHeader = ['CSV line', 'Date', 'Vendor (as written)', 'Grouping key', 'Amount',
    'Kind', 'Category', 'Reference', 'Status', 'Memo'];
  const payRows = [payHeader];
  for (const v of analysis.vendors) {
    for (const r of v.rows) {
      payRows.push([
        r.line, r.date, r.vendor, r.vendorKey, r.amount,
        r.isRefund ? 'refund / credit' : 'payment',
        r.category, r.reference, r.status, r.memo,
      ]);
    }
  }

  const skHeader = ['CSV line', 'Reason', 'Value seen', 'Raw row'];
  const skRows = [skHeader].concat((skipped || []).map((s) => ([
    s.line, s.reason, s.value, (s.row || []).join(' | '),
  ])));
  if (skRows.length === 1) skRows.push(['—', 'none', 'Every data row was read successfully.', '']);

  return buildWorkbook([
    { name: 'Summary', rows: summaryRows, opts: { headerRows: 1, widths: [48, 24] } },
    {
      name: 'Vendors',
      rows: vendorRows,
      opts: {
        headerRows: 1,
        widths: [6, 32, 26, 13, 14, 13, 11, 10, 12, 16, 15, 15, 16, 21, 19, 16, 9, 12, 12, 13, 26, 36],
        moneyCols: [3, 5, 6, 9, 10, 11, 15],
        pctCols: [4, 16],
      },
    },
    {
      name: 'Monthly',
      rows: monthRows,
      opts: { headerRows: 1, widths: [10, 13, 13, 11, 10, 14, 28, 12], moneyCols: [1, 2, 3, 7] },
    },
    {
      name: 'Categories',
      rows: catRows,
      opts: { headerRows: 1, widths: [38, 13, 14], moneyCols: [1], pctCols: [2] },
    },
    {
      name: 'All Payments',
      rows: payRows,
      opts: { headerRows: 1, widths: [10, 12, 30, 24, 13, 16, 20, 18, 14, 40], moneyCols: [4] },
    },
    { name: 'Flagged Rows', rows: skRows, opts: { headerRows: 1, widths: [10, 24, 26, 60] } },
  ]);
}

module.exports = { renderXlsx, buildWorkbook, sheetXml, esc, colName };
