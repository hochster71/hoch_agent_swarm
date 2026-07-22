// engine/render_xlsx.js
//
// HFF — Getting-Paid Speed Report — dependency-free XLSX writer.
//
// Builds a real SpreadsheetML (.xlsx) package by hand: [Content_Types].xml,
// package + workbook rels, styles, and one worksheet per tab. Cells use inline
// strings (t="inlineStr") so no sharedStrings table is needed, which means the
// engine and its tests run with NO npm install.
//
// Sheets: Summary | Clients | Monthly | All Invoices | Flagged Rows
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

function blankIfNull(v) { return v === null || v === undefined ? '' : v; }

function renderXlsx(report) {
  const { summary, analysis, skipped } = report;
  const t = summary.timing;

  const summaryRows = [
    ['Getting-Paid Speed Report — Summary'],
    [],
    ['Observed window (issue dates)', `${summary.window.start} to ${summary.window.end}`],
    ['Latest date anywhere in file', summary.window.asOf],
    ['Calendar months observed', summary.counts.monthsObserved],
    ['Clients named in file', summary.counts.clients],
    ['Invoices read', summary.counts.invoices],
    ['Invoices paid', summary.counts.paid],
    ['Invoices still open', summary.counts.open],
    ['Rows flagged (unreadable or credit notes)', summary.counts.skippedRows],
    [],
    ['Total billed', t.billed],
    ['Billed that has been paid', t.paidBilled],
    ['Billed still outstanding', t.outstanding],
    ['Share paid by count %', t.pctPaidByCount],
    ['Share paid by value %', t.pctPaidByValue],
    [],
    ['Payment speed (paid invoices only)'],
    ['Median days to pay', blankIfNull(t.medianDaysToPay)],
    ['Mean days to pay', blankIfNull(t.meanDaysToPay)],
    ['Fastest days to pay', blankIfNull(t.fastestDaysToPay)],
    ['Slowest days to pay', blankIfNull(t.slowestDaysToPay)],
    ['On-time share % (paid on/before due)', blankIfNull(t.onTimePct)],
    [],
    ['Outstanding detail'],
    ['Open invoices past their due date', summary.counts.overdueOpen],
    ['Value of those past-due open invoices', t.overdueOpenTotal],
    ['Oldest open invoice age (days)', blankIfNull(t.oldestOpenAgeDays)],
    [],
    ['Due basis (how the due date for each invoice was set)'],
    ['From a due-date column', summary.dueBasisMix.due_column],
    ['From parseable terms', summary.dueBasisMix.terms],
    ['From an assumed net-30', summary.dueBasisMix.assumed_net_30],
    [],
    ['Concentration (arithmetic over this file only)'],
    ['Top client share of billed %', summary.concentration.top1SharePct],
    ['Top 3 share of billed %', summary.concentration.top3SharePct],
    ['Top 5 share of billed %', summary.concentration.top5SharePct],
    ['HHI', summary.concentration.hhi],
    ['HHI scale', summary.concentration.hhiScale],
    ['Effective client count', summary.concentration.effectiveClientCount],
    [],
    ['Client buckets that merged spellings', summary.counts.mergedClients],
  ];
  if (summary.currencies && summary.currencies.length) {
    summaryRows.push(['Currencies named in file', summary.currencies.join(', ')]);
  }
  summaryRows.push([], ['Observations']);
  for (const n of summary.notes) summaryRows.push([n]);
  summaryRows.push([], ['Disclaimer'], [DISCLAIMER]);

  const clientHeader = [
    'Rank', 'Client (as written)', 'Grouping key', 'Billed', 'Share of billed %',
    'Invoices', 'Paid', 'Open', 'Paid amount', 'Outstanding',
    'Median days to pay', 'Mean days to pay', 'Fastest', 'Slowest',
    'On-time paid', 'Late paid', 'On-time %',
    'Open past due', 'Oldest open age (days)',
    'First invoice', 'Last invoice', 'Spellings merged',
  ];
  const clientRows = [clientHeader].concat(analysis.clients.map((c) => ([
    c.rank, c.label, c.clientKey, c.billed, c.billedSharePct,
    c.invoiceCount, c.paidCount, c.openCount, c.paidBilled, c.outstanding,
    blankIfNull(c.medianDaysToPay), blankIfNull(c.meanDaysToPay),
    blankIfNull(c.fastestDaysToPay), blankIfNull(c.slowestDaysToPay),
    c.onTimeCount, c.lateCount, blankIfNull(c.onTimePct),
    c.overdueOpenCount, blankIfNull(c.oldestOpenAgeDays),
    c.firstInvoice, c.lastInvoice,
    c.spellingCount > 1 ? c.spellings.join(' / ') : '',
  ])));

  const monthHeader = ['Issue month', 'Invoices', 'Billed', 'Paid', 'Open',
    'Median days to pay (paid)', 'On-time % (paid)'];
  const monthRows = [monthHeader].concat(analysis.monthly.map((m) => ([
    m.month, m.invoices, m.billed, m.paidCount, m.openCount,
    blankIfNull(m.medianDaysToPay), blankIfNull(m.onTimePct),
  ])));

  const invHeader = ['CSV line', 'Issued', 'Client (as written)', 'Grouping key', 'Amount',
    'Paid date', 'Days to pay', 'Due date used', 'Due basis', 'On-time',
    'Open past due', 'Open age (days)', 'Terms (as written days)', 'Reference', 'Status'];
  const invRows = [invHeader];
  for (const c of analysis.clients) {
    for (const inv of c.rows) {
      invRows.push([
        inv.line, inv.issuedDate, inv.client, inv.clientKey, inv.amount,
        inv.paidDate || '', blankIfNull(inv.daysToPay),
        inv.dueDate || (`(day+${inv.dueDay - inv.issuedDay})`),
        inv.dueBasis,
        inv.isPaid ? (inv.onTime ? 'on time' : 'after due') : '',
        !inv.isPaid && inv.overdue ? 'yes' : '',
        inv.isPaid ? '' : blankIfNull(inv.ageDays),
        inv.termsDays === null ? '' : inv.termsDays,
        inv.reference, inv.status,
      ]);
    }
  }

  const skHeader = ['CSV line', 'Reason', 'Value seen', 'Raw row'];
  const skRows = [skHeader].concat((skipped || []).map((s) => ([
    s.line, s.reason, s.value, (s.row || []).join(' | '),
  ])));
  if (skRows.length === 1) skRows.push(['—', 'none', 'Every data row was read successfully.', '']);

  return buildWorkbook([
    { name: 'Summary', rows: summaryRows, opts: { headerRows: 1, widths: [46, 26] } },
    {
      name: 'Clients',
      rows: clientRows,
      opts: {
        headerRows: 1,
        widths: [6, 30, 24, 13, 14, 9, 7, 7, 13, 13, 15, 14, 9, 9, 11, 10, 10, 13, 18, 12, 12, 34],
        moneyCols: [3, 8, 9],
        pctCols: [4, 16],
      },
    },
    {
      name: 'Monthly',
      rows: monthRows,
      opts: { headerRows: 1, widths: [12, 10, 14, 8, 8, 22, 16], moneyCols: [2], pctCols: [6] },
    },
    {
      name: 'All Invoices',
      rows: invRows,
      opts: {
        headerRows: 1,
        widths: [9, 12, 30, 24, 13, 12, 11, 14, 15, 10, 12, 14, 18, 16, 14],
        moneyCols: [4],
      },
    },
    { name: 'Flagged Rows', rows: skRows, opts: { headerRows: 1, widths: [9, 22, 28, 60] } },
  ]);
}

module.exports = { renderXlsx, buildWorkbook, sheetXml, esc, colName };
