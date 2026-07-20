// engine/render_xlsx.js
//
// HFF — Effective Hourly Rate Report — dependency-free XLSX writer.
//
// Builds a real SpreadsheetML (.xlsx) package by hand: [Content_Types].xml,
// package + workbook rels, styles, and one worksheet per tab. Cells use inline
// strings (t="inlineStr") so no sharedStrings table is needed, which means the
// engine and its tests run with NO npm install.
//
// Sheets: Summary | Clients | Monthly | All Entries | Flagged Rows
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
    ['Effective Hourly Rate Report — Summary'],
    [],
    ['Observed window', `${summary.window.start} to ${summary.window.end}`],
    ['Calendar months observed', summary.counts.monthsObserved],
    ['Tracked days', summary.counts.trackedDays],
    ['Clients named in file', summary.counts.clients],
    ['Time entries read', summary.counts.entries],
    ['Entries carrying billing figures', summary.counts.pricedEntries],
    ['Rows flagged as unreadable', summary.counts.skippedRows],
    [],
    ['Total tracked hours', summary.hours.total],
    ['Hours marked billable', summary.hours.billable],
    ['Hours marked non-billable', summary.hours.nonBillable],
    ['Hours with unreadable billable flag', summary.hours.unknownFlag],
    ['Hours covered by billing figures', summary.hours.covered],
    [],
    ['Revenue observed', summary.revenue.total],
    ['Average revenue per tracked day', summary.revenue.averagePerTrackedDay],
    [],
    ['Rates (arithmetic over this file only)', summary.rates.available ? '' : 'no billing figures in file'],
  ];
  if (summary.rates.available) {
    summaryRows.push(['Effective rate per covered hour', summary.rates.effectiveRateCovered]);
    summaryRows.push(['Blended rate across all tracked hours', summary.rates.blendedRateAllHours]);
    summaryRows.push(['Share of hours covered by billing figures', summary.rates.coveragePctOfHours]);
  }
  summaryRows.push([]);
  summaryRows.push(['Billable share',
    summary.billableShare.available ? summary.billableShare.billableSharePct : 'no readable billable flags']);
  summaryRows.push([], ['Observations']);
  for (const n of summary.notes) summaryRows.push([n]);
  summaryRows.push([], ['Disclaimer'], [DISCLAIMER]);

  const clientHeader = [
    'Rank', 'Client (as written)', 'Grouping key', 'Hours', 'Share of hours %', 'Entries',
    'Billable hours', 'Non-billable hours', 'Unknown-flag hours',
    'Revenue', 'Covered hours', 'Rate per covered hour', 'Blended rate (all hours)',
    'Median session (h)', 'Longest session (h)', 'Months active', 'Projects',
    'First entry', 'Last entry', 'Spellings merged',
  ];
  const clientRows = [clientHeader].concat(analysis.clients.map((c) => ([
    c.rank, c.label, c.clientKey, c.hours, c.hoursSharePct, c.entryCount,
    c.billableHours, c.nonBillableHours, c.unknownBillableHours,
    c.revenue, c.coveredHours,
    c.effectiveRateCovered === null ? '' : c.effectiveRateCovered,
    c.blendedRateAllHours === null ? '' : c.blendedRateAllHours,
    c.medianSessionHours, c.longestSessionHours, c.monthsActive, c.projectCount,
    c.firstEntry, c.lastEntry,
    c.spellingCount > 1 ? c.spellings.join(' / ') : '',
  ])));

  const monthHeader = ['Month', 'Hours', 'Billable hours', 'Billable share %', 'Revenue',
    'Rate per covered hour', 'Active clients', 'Most-tracked client', 'Their hours'];
  const monthRows = [monthHeader].concat(analysis.monthly.map((m) => ([
    m.month, m.hours, m.billableHours,
    m.billableSharePct === null ? '' : m.billableSharePct,
    m.revenue,
    m.effectiveRateCovered === null ? '' : m.effectiveRateCovered,
    m.activeClients, m.topClient, m.topClientHours,
  ])));
  monthRows.push([]);
  monthRows.push(['Weekday totals']);
  monthRows.push(['Weekday', 'Hours']);
  for (const w of analysis.weekdays) monthRows.push([w.weekday, w.hours]);

  const entHeader = ['CSV line', 'Date', 'Client (as written)', 'Grouping key', 'Project',
    'Hours', 'Billable', 'Amount', 'Amount source', 'Description'];
  const entRows = [entHeader];
  for (const c of analysis.clients) {
    for (const r of c.rows) {
      entRows.push([
        r.line, r.date, r.client, r.clientKey, r.project, r.hours,
        r.billable === true ? 'yes' : r.billable === false ? 'no' : '',
        r.amount === null ? '' : r.amount,
        r.revenueSource === 'derived_from_rate' ? 'rate x hours' : r.revenueSource === 'amount' ? 'amount column' : '',
        r.description,
      ]);
    }
  }

  const skHeader = ['CSV line', 'Reason', 'Value seen', 'Raw row'];
  const skRows = [skHeader].concat((skipped || []).map((s) => ([
    s.line, s.reason, s.value, (s.row || []).join(' | '),
  ])));
  if (skRows.length === 1) skRows.push(['—', 'none', 'Every data row was read successfully.', '']);

  return buildWorkbook([
    { name: 'Summary', rows: summaryRows, opts: { headerRows: 1, widths: [46, 22] } },
    {
      name: 'Clients',
      rows: clientRows,
      opts: {
        headerRows: 1,
        widths: [6, 30, 24, 10, 15, 9, 14, 17, 18, 13, 14, 19, 21, 16, 17, 13, 10, 12, 12, 34],
        moneyCols: [9, 11, 12],
        pctCols: [4],
      },
    },
    {
      name: 'Monthly',
      rows: monthRows,
      opts: { headerRows: 1, widths: [10, 10, 14, 15, 13, 19, 13, 26, 12], moneyCols: [4, 5], pctCols: [3] },
    },
    {
      name: 'All Entries',
      rows: entRows,
      opts: { headerRows: 1, widths: [10, 12, 28, 22, 18, 8, 9, 12, 14, 40], moneyCols: [7] },
    },
    { name: 'Flagged Rows', rows: skRows, opts: { headerRows: 1, widths: [10, 24, 26, 60] } },
  ]);
}

module.exports = { renderXlsx, buildWorkbook, sheetXml, esc, colName };
