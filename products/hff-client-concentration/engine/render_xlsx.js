// engine/render_xlsx.js
//
// HFF — Client Revenue Concentration Report — dependency-free XLSX writer.
//
// Builds a real SpreadsheetML (.xlsx) package by hand: [Content_Types].xml,
// package + workbook rels, styles, and one worksheet per tab. Cells use inline
// strings (t="inlineStr") so no sharedStrings table is needed, which means the
// engine and its tests run with NO npm install.
//
// Sheets: Summary | Clients | Monthly Revenue | All Invoices | Flagged Rows
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
    ['Client Revenue Concentration Report — Summary'],
    [],
    ['Observed window', `${summary.window.start} to ${summary.window.end}`],
    ['Calendar months observed', summary.counts.monthsObserved],
    ['Clients named in file', summary.counts.clients],
    ['Clients contributing net revenue', summary.counts.contributingClients],
    ['Invoice rows read', summary.counts.invoiceRows],
    ['Credit / refund rows read', summary.counts.creditRows],
    ['Rows flagged as unreadable', summary.counts.skippedRows],
    [],
    ['Gross revenue observed', summary.totals.gross],
    ['Credits / refunds observed', summary.totals.credits],
    ['Net revenue observed', summary.totals.net],
    ['Average net per contributing client', summary.totals.averagePerClient],
    [],
    ['Concentration', 'Value'],
    ['Largest client share', summary.concentration.top1SharePct],
    ['Top 3 share', summary.concentration.top3SharePct],
    ['Top 5 share', summary.concentration.top5SharePct],
    ['Top 10 share', summary.concentration.top10SharePct],
    ['HHI (0–10,000)', summary.concentration.hhi],
    ['Effective client count', summary.concentration.effectiveClientCount],
    ['Clients making up first 50%', summary.concentration.clientsToReachHalf],
    ['Clients making up first 80%', summary.concentration.clientsToReachEighty],
    [],
    ['Payment timing', summary.paymentTiming.available ? 'paid-date column present' : 'no paid-date column in file'],
  ];
  if (summary.paymentTiming.available) {
    summaryRows.push(['Median days to pay', summary.paymentTiming.medianDaysToPay]);
    summaryRows.push(['Longest observed days to pay', summary.paymentTiming.slowestDaysToPay]);
  }
  summaryRows.push([], ['Observations']);
  for (const n of summary.notes) summaryRows.push([n]);
  summaryRows.push([], ['Disclaimer'], [DISCLAIMER]);

  const clientHeader = [
    'Rank', 'Client (as written)', 'Grouping key', 'Net revenue', 'Share %', 'Invoices',
    'Gross', 'Credits', 'Average invoice', 'Largest invoice', 'Smallest invoice',
    'First invoice', 'Last invoice', 'Days since last', 'Median gap (days)',
    'Months with revenue', 'Median days to pay', 'New in window', 'No invoice since expected', 'Spellings merged',
  ];
  const clientRows = [clientHeader].concat(analysis.clients.map((c) => ([
    c.rank, c.label, c.clientKey, c.net, c.sharePct, c.invoiceCount,
    c.gross, c.credits, c.averageInvoice, c.largestInvoice, c.smallestInvoice,
    c.firstInvoice, c.lastInvoice, c.daysSinceLastInvoice,
    c.medianGapDays === null ? '' : c.medianGapDays,
    c.monthsWithRevenue,
    c.medianDaysToPay === null ? '' : c.medianDaysToPay,
    c.newInWindow ? 'yes' : 'no',
    c.noInvoiceSinceExpected ? 'yes' : 'no',
    c.spellingCount > 1 ? c.spellings.join(' / ') : '',
  ])));

  const monthHeader = ['Month', 'Net revenue', 'Gross', 'Credits', 'Active clients', 'Largest client that month', 'Amount', 'Share of month %'];
  const monthRows = [monthHeader].concat(analysis.monthly.map((m) => ([
    m.month, m.net, m.gross, m.credits, m.activeClients, m.topClient, m.topClientAmount, m.topClientSharePct,
  ])));

  const invHeader = ['CSV line', 'Date', 'Client (as written)', 'Grouping key', 'Amount', 'Invoice', 'Status', 'Paid date', 'Days to pay'];
  const invRows = [invHeader];
  for (const c of analysis.clients) {
    for (const r of c.rows) {
      invRows.push([
        r.line, r.date, r.client, r.clientKey, r.amount, r.invoice, r.status,
        r.paidDate, r.daysToPay === null ? '' : r.daysToPay,
      ]);
    }
  }

  const skHeader = ['CSV line', 'Reason', 'Value seen', 'Raw row'];
  const skRows = [skHeader].concat((skipped || []).map((s) => ([
    s.line, s.reason, s.value, (s.row || []).join(' | '),
  ])));
  if (skRows.length === 1) skRows.push(['—', 'none', 'Every data row was read successfully.', '']);

  return buildWorkbook([
    { name: 'Summary', rows: summaryRows, opts: { headerRows: 1, widths: [46, 20], moneyCols: [] } },
    {
      name: 'Clients',
      rows: clientRows,
      opts: {
        headerRows: 1,
        widths: [6, 30, 24, 14, 10, 10, 14, 12, 14, 15, 15, 13, 13, 14, 16, 18, 17, 13, 22, 34],
        moneyCols: [3, 6, 7, 8, 9, 10],
        pctCols: [4],
      },
    },
    {
      name: 'Monthly Revenue',
      rows: monthRows,
      opts: { headerRows: 1, widths: [10, 14, 14, 12, 14, 30, 14, 16], moneyCols: [1, 2, 3, 6], pctCols: [7] },
    },
    {
      name: 'All Invoices',
      rows: invRows,
      opts: { headerRows: 1, widths: [10, 12, 30, 24, 14, 16, 14, 12, 12], moneyCols: [4] },
    },
    { name: 'Flagged Rows', rows: skRows, opts: { headerRows: 1, widths: [10, 24, 26, 60] } },
  ]);
}

module.exports = { renderXlsx, buildWorkbook, sheetXml, esc, colName };
