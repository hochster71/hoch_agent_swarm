// engine/ingest.js
//
// Stage 1: Ingest & normalize. Accepts common CSV shapes, auto-detects columns,
// normalizes signs to inflow(+)/outflow(-). Unparseable rows are FLAGGED (rejected
// list with a reason), never silently dropped.

'use strict';

// Minimal, dependency-free CSV parser that handles quoted fields, escaped quotes,
// and commas/newlines inside quotes.
function parseCsv(text) {
  const rows = [];
  let field = '';
  let record = [];
  let inQuotes = false;
  const s = String(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inQuotes) {
      if (c === '"') {
        if (s[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      record.push(field);
      field = '';
    } else if (c === '\n') {
      record.push(field);
      rows.push(record);
      record = [];
      field = '';
    } else {
      field += c;
    }
  }
  // trailing field / record
  if (field.length > 0 || record.length > 0) {
    record.push(field);
    rows.push(record);
  }
  // drop fully-empty trailing rows
  return rows.filter((r) => !(r.length === 1 && r[0].trim() === ''));
}

function norm(h) {
  return String(h || '').trim().toLowerCase().replace(/[^a-z0-9]/g, '');
}

// Detect which header maps to which logical column.
function detectColumns(headers) {
  const map = {};
  const normed = headers.map(norm);

  const find = (candidates) => {
    for (const cand of candidates) {
      const idx = normed.indexOf(cand);
      if (idx !== -1) return idx;
    }
    // partial contains match
    for (let i = 0; i < normed.length; i++) {
      if (candidates.some((cand) => normed[i].includes(cand))) return i;
    }
    return -1;
  };

  map.date = find(['date', 'transactiondate', 'posteddate', 'postingdate']);
  map.description = find(['description', 'desc', 'memo', 'details', 'name', 'payee', 'merchant', 'narrative']);
  map.amount = find(['amount', 'value']);
  map.debit = find(['debit', 'withdrawal', 'withdrawals', 'moneyout', 'paidout']);
  map.credit = find(['credit', 'deposit', 'deposits', 'moneyin', 'paidin']);
  map.category = find(['category', 'type']);
  return map;
}

function parseAmount(raw) {
  if (raw === undefined || raw === null) return NaN;
  let s = String(raw).trim();
  if (s === '') return NaN;
  let negative = false;
  // Parentheses denote negative in many bank exports: (123.45)
  if (/^\(.*\)$/.test(s)) {
    negative = true;
    s = s.slice(1, -1);
  }
  // Strip currency symbols, thousands separators, spaces.
  s = s.replace(/[$£€,\s]/g, '');
  if (s.startsWith('-')) {
    negative = true;
    s = s.slice(1);
  }
  const n = Number(s);
  if (!isFinite(n)) return NaN;
  return negative ? -n : n;
}

function parseDate(raw) {
  const s = String(raw || '').trim();
  if (!s) return null;
  // ISO YYYY-MM-DD
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) return isoDate(+m[1], +m[2], +m[3]);
  // US MM/DD/YYYY or M/D/YY
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (m) {
    let year = +m[3];
    if (year < 100) year += 2000;
    return isoDate(year, +m[1], +m[2]);
  }
  // DD-Mon-YYYY
  m = s.match(/^(\d{1,2})[-\s]([A-Za-z]{3})[-\s](\d{2,4})/);
  if (m) {
    const months = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
    const mo = months[m[2].toLowerCase()];
    let year = +m[3];
    if (year < 100) year += 2000;
    if (mo) return isoDate(year, mo, +m[1]);
  }
  return null;
}

function isoDate(y, m, d) {
  if (!(m >= 1 && m <= 12 && d >= 1 && d <= 31)) return null;
  const mm = String(m).padStart(2, '0');
  const dd = String(d).padStart(2, '0');
  return `${y}-${mm}-${dd}`;
}

// ingest(csvText) -> { transactions: [...], rejected: [...], columns }
// Each transaction: { row, date, description, amount(+in/-out), rawCategory }
function ingest(csvText) {
  const rows = parseCsv(csvText);
  if (rows.length === 0) {
    return { transactions: [], rejected: [], columns: {} };
  }
  const headers = rows[0];
  const cols = detectColumns(headers);

  const hasAmount = cols.amount !== -1;
  const hasDebitCredit = cols.debit !== -1 || cols.credit !== -1;

  const transactions = [];
  const rejected = [];

  if (cols.date === -1 || cols.description === -1 || (!hasAmount && !hasDebitCredit)) {
    // Cannot map required columns — reject the whole file with a clear reason.
    return {
      transactions: [],
      rejected: [{ row: 1, reason: 'Could not detect required columns (need date, description, and amount OR debit/credit).', raw: headers.join(',') }],
      columns: cols,
    };
  }

  for (let r = 1; r < rows.length; r++) {
    const cells = rows[r];
    const rawRow = cells.join(',');
    const date = parseDate(cells[cols.date]);
    const description = String(cells[cols.description] || '').trim();

    let amount = NaN;
    if (hasAmount) {
      amount = parseAmount(cells[cols.amount]);
    }
    if (isNaN(amount) && hasDebitCredit) {
      const debit = cols.debit !== -1 ? parseAmount(cells[cols.debit]) : NaN;
      const credit = cols.credit !== -1 ? parseAmount(cells[cols.credit]) : NaN;
      // credit = inflow (+), debit = outflow (-)
      if (!isNaN(credit) && credit !== 0) amount = Math.abs(credit);
      else if (!isNaN(debit) && debit !== 0) amount = -Math.abs(debit);
    }

    const reasons = [];
    if (!date) reasons.push('unparseable date');
    if (!description) reasons.push('missing description');
    if (isNaN(amount)) reasons.push('unparseable amount');

    if (reasons.length) {
      rejected.push({ row: r + 1, reason: reasons.join('; '), raw: rawRow });
      continue;
    }

    const rawCategory = cols.category !== -1 ? String(cells[cols.category] || '').trim() : '';
    transactions.push({
      row: r + 1,
      date,
      description,
      amount: round2(amount),
      rawCategory,
    });
  }

  return { transactions, rejected, columns: cols };
}

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

module.exports = { ingest, parseCsv, detectColumns, parseAmount, parseDate, round2 };
