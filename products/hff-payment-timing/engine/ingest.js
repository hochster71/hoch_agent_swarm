// engine/ingest.js
//
// HFF — Getting-Paid Speed Report — deterministic CSV ingest.
//
// DESIGN RULE (inherited from hff-invoice-aging / hff-vendor-spend / the rest of
// the HFF line): unparseable or ambiguous rows are FLAGGED, never silently
// dropped. Every skipped row comes back with its 1-based CSV line number and a
// machine-readable reason, so the buyer can see exactly what the engine could
// not read.
//
// Required columns: issued date, client, amount, paid date.
//   * The paid-date column MUST exist because this report is about how fast
//     clients pay once billed. A BLANK paid-date value simply means the invoice
//     is still open — that is expected, not an error.
// Optional columns: due date, terms, status, currency, reference.
//
// Handles: RFC4180 quoting (incl. escaped ""), CRLF, BOM, header aliasing,
// ISO / US / UK dates (with whole-file auto-detection), EU decimal commas,
// currency symbols, parenthesised negatives, trailing-minus negatives, and
// "Net 30" / "Due on receipt" style terms strings.
//
// SIGN CONVENTION: an invoice amount is money BILLED and must be positive. A
// negative amount is treated as a credit note, counted separately and disclosed
// — never folded into an invoice's payment-timing arithmetic.
'use strict';

const { CLIENT_SUFFIXES, MAX_LINE_AMOUNT, DEFAULT_NET_DAYS } = require('./constants');

// ---------------------------------------------------------------- CSV parsing

function splitCsv(text) {
  const src = String(text).replace(/^﻿/, '');
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (inQuotes) {
      if (c === '"') {
        if (src[i + 1] === '"') { field += '"'; i += 2; continue; }
        inQuotes = false; i += 1; continue;
      }
      field += c; i += 1; continue;
    }
    if (c === '"') { inQuotes = true; i += 1; continue; }
    if (c === ',') { row.push(field); field = ''; i += 1; continue; }
    if (c === '\r') { i += 1; continue; }
    if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; i += 1; continue; }
    field += c; i += 1;
  }
  row.push(field);
  rows.push(row);
  while (rows.length && rows[rows.length - 1].every((f) => String(f).trim() === '')) rows.pop();
  return rows;
}

// ---------------------------------------------------------------- header map

const HEADER_ALIASES = {
  issued: [
    'date', 'invoice date', 'issue date', 'issued', 'issued date', 'date issued',
    'bill date', 'billing date', 'created', 'created date', 'date created', 'invoice created',
  ],
  paid: [
    'paid date', 'date paid', 'payment date', 'paid on', 'settled date', 'date settled',
    'cleared date', 'date cleared', 'closed date', 'date closed', 'payment received',
    'received date', 'date received',
  ],
  client: [
    'client', 'customer', 'account', 'payer', 'bill to', 'billed to', 'client name',
    'customer name', 'account name', 'company', 'company name', 'debtor', 'counterparty',
  ],
  amount: [
    'amount', 'total', 'invoice amount', 'invoice total', 'billed', 'value', 'amount (usd)',
    'amount usd', 'net amount', 'subtotal', 'grand total', 'line total', 'invoice value',
  ],
  due: ['due date', 'date due', 'payment due', 'due on', 'due'],
  terms: ['terms', 'payment terms', 'net terms', 'net', 'credit terms'],
  status: ['status', 'payment status', 'state', 'paid?', 'invoice status'],
  currency: ['currency', 'ccy', 'curr'],
  reference: ['invoice', 'invoice number', 'invoice #', 'invoice no', 'number', 'reference', 'ref', 'id', 'invoice id'],
};

// "name" is ambiguous — accepted as the client only when nothing stronger claims it.
const WEAK_CLIENT_HEADERS = ['name'];

function normHeader(h) {
  return String(h).trim().toLowerCase().replace(/\s+/g, ' ').replace(/[^a-z0-9 ()#?]/g, '');
}

function mapHeaders(headerRow) {
  const map = {};
  let weakClientIdx;

  headerRow.forEach((raw, idx) => {
    const h = normHeader(raw);
    for (const [canon, aliases] of Object.entries(HEADER_ALIASES)) {
      if (!aliases.includes(h)) continue;
      if (map[canon] !== undefined) continue;
      map[canon] = idx;
      break;
    }
    if (map.client === undefined && WEAK_CLIENT_HEADERS.includes(h) && weakClientIdx === undefined) {
      weakClientIdx = idx;
    }
  });

  if (map.client === undefined && weakClientIdx !== undefined) {
    map.client = weakClientIdx;
    map._clientFromName = true;
  }
  return map;
}

// ---------------------------------------------------------------- dates

function isLeap(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }
const MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function validYMD(y, m, d) {
  if (!(y >= 1900 && y <= 2200)) return false;
  if (!(m >= 1 && m <= 12)) return false;
  const max = m === 2 && isLeap(y) ? 29 : MDAYS[m - 1];
  return d >= 1 && d <= max;
}

function parseDate(raw, order) {
  const s = String(raw).trim();
  if (!s) return null;
  let m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
  if (m) {
    const y = +m[1], mo = +m[2], d = +m[3];
    return validYMD(y, mo, d) ? { y, m: mo, d } : null;
  }
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})/);
  if (m) {
    const a = +m[1], b = +m[2];
    let y = +m[3];
    if (y < 100) y += y < 70 ? 2000 : 1900;
    const mo = order === 'uk' ? b : a;
    const d = order === 'uk' ? a : b;
    return validYMD(y, mo, d) ? { y, m: mo, d } : null;
  }
  return null;
}

function detectDateOrder(values, explicit) {
  if (explicit === 'us' || explicit === 'uk') return explicit;
  let firstOver12 = 0;
  let secondOver12 = 0;
  for (const v of values) {
    const m = String(v).trim().match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})/);
    if (!m) continue;
    if (+m[1] > 12) firstOver12 += 1;
    if (+m[2] > 12) secondOver12 += 1;
  }
  if (firstOver12 > 0 && secondOver12 === 0) return 'uk';
  return 'us';
}

function toISO(p) {
  return `${p.y}-${String(p.m).padStart(2, '0')}-${String(p.d).padStart(2, '0')}`;
}
function monthKey(p) {
  return `${p.y}-${String(p.m).padStart(2, '0')}`;
}
// Days since epoch — deterministic, timezone-free.
function dayNumber(p) {
  return Math.floor(Date.UTC(p.y, p.m - 1, p.d) / 86400000);
}

// ---------------------------------------------------------------- amounts

function parseAmount(raw) {
  let s = String(raw).trim();
  if (!s) return null;
  let negative = false;
  if (/^\(.*\)$/.test(s)) { negative = true; s = s.slice(1, -1); }
  if (/-\s*$/.test(s)) { negative = true; s = s.replace(/-\s*$/, ''); }
  s = s.replace(/[^\d.,\-]/g, '');            // strip $, £, €, USD, spaces
  if (s.startsWith('-')) { negative = true; s = s.slice(1); }
  s = s.replace(/-/g, '');
  if (s === '') return null;
  if (/^\d{1,3}(\.\d{3})+,\d{1,2}$/.test(s)) s = s.replace(/\./g, '').replace(',', '.');
  else if (/^\d+,\d{1,2}$/.test(s)) s = s.replace(',', '.');
  else s = s.replace(/,/g, '');
  if (!/^\d*\.?\d+$/.test(s)) return null;
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return negative ? -n : n;
}

function round2(n) {
  return Math.round((Number(n) + Number.EPSILON) * 100) / 100;
}

// ---------------------------------------------------------------- terms

// Parse a payment-terms string into a whole number of days, or null when the
// string carries no readable term. "Due on receipt" and equivalents are 0 days.
function parseTerms(raw) {
  const s = String(raw).trim().toLowerCase();
  if (!s) return null;
  if (/(due on receipt|on receipt|due immediately|immediate|upon receipt|\bcod\b|cash on delivery)/.test(s)) return 0;
  let m = s.match(/net\s*[-]?\s*(\d{1,3})/);
  if (m) return +m[1];
  m = s.match(/(\d{1,3})\s*days?/);
  if (m) return +m[1];
  m = s.match(/^(\d{1,3})$/);
  if (m) return +m[1];
  return null;
}

// ---------------------------------------------------------------- client keys

// Two spellings of the same client should land in one bucket. STRING
// normalization only — no client database — and every merge is disclosed.
function clientKey(raw) {
  let s = String(raw).toUpperCase();
  s = s.replace(/&/g, ' AND ');
  s = s.replace(/[^A-Z0-9 ]+/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  if (s.startsWith('THE ')) s = s.slice(4);
  let changed = true;
  while (changed) {
    changed = false;
    for (const suf of CLIENT_SUFFIXES) {
      if (s.endsWith(' ' + suf)) { s = s.slice(0, -(suf.length + 1)).trim(); changed = true; break; }
      if (s === suf) return s;
    }
  }
  return s.trim();
}

// ---------------------------------------------------------------- ingest

function ingestCsv(text, opts) {
  const options = opts || {};
  if (typeof text !== 'string' || text.trim() === '') {
    const err = new Error('The uploaded file is empty.');
    err.code = 'EMPTY_FILE';
    throw err;
  }
  const grid = splitCsv(text);
  if (grid.length < 2) {
    const err = new Error('The file needs a header row and at least one invoice row.');
    err.code = 'NO_ROWS';
    throw err;
  }
  const headerRow = grid[0];
  const map = mapHeaders(headerRow);

  const missing = [];
  if (map.issued === undefined) missing.push('issued date');
  if (map.client === undefined) missing.push('client');
  if (map.amount === undefined) missing.push('amount');
  if (map.paid === undefined) missing.push('paid date');
  if (missing.length) {
    const err = new Error(
      `Could not find these required column(s): ${missing.join(', ')}. ` +
      `This report needs an issue date, a client, an amount, and a paid-date column ` +
      `(a blank paid date just means the invoice is still open). ` +
      `Header seen: ${headerRow.map((h) => String(h).trim()).filter(Boolean).join(', ') || '(blank)'}.`
    );
    err.code = 'MISSING_COLUMNS';
    err.missing = missing;
    throw err;
  }

  // Date-order auto-detection considers issued, paid, and due columns together.
  const dateSamples = [];
  for (let i = 1; i < grid.length; i++) {
    const r = grid[i];
    for (const idx of [map.issued, map.paid, map.due]) {
      if (idx !== undefined && r[idx] !== undefined) dateSamples.push(r[idx]);
    }
  }
  const dateOrder = detectDateOrder(dateSamples, options.dateOrder);

  const invoices = [];
  const skipped = [];
  let creditNoteCount = 0;
  let creditNoteTotal = 0;
  const currencies = new Set();

  for (let i = 1; i < grid.length; i++) {
    const r = grid[i];
    const line = i + 1; // 1-based, header counts as line 1
    if (r.every((f) => String(f).trim() === '')) continue;

    const issuedRaw = r[map.issued] === undefined ? '' : r[map.issued];
    const clientRaw = r[map.client] === undefined ? '' : String(r[map.client]).trim();

    const issuedParts = parseDate(issuedRaw, dateOrder);
    if (!issuedParts) { skipped.push({ line, reason: 'unreadable_issue_date', value: String(issuedRaw).trim(), row: r }); continue; }
    if (!clientRaw) { skipped.push({ line, reason: 'missing_client', value: '', row: r }); continue; }
    const key = clientKey(clientRaw);
    if (!key) { skipped.push({ line, reason: 'unusable_client_name', value: clientRaw, row: r }); continue; }

    const amountRaw = String(r[map.amount] === undefined ? '' : r[map.amount]).trim();
    let amount = parseAmount(amountRaw);
    if (amount === null) { skipped.push({ line, reason: 'unreadable_amount', value: amountRaw, row: r }); continue; }
    if (amount === 0) { skipped.push({ line, reason: 'zero_amount', value: amountRaw, row: r }); continue; }
    if (amount < 0) {
      creditNoteCount += 1;
      creditNoteTotal = round2(creditNoteTotal + Math.abs(amount));
      skipped.push({ line, reason: 'credit_note', value: amountRaw, row: r });
      continue;
    }
    if (amount > MAX_LINE_AMOUNT) {
      skipped.push({ line, reason: 'implausible_amount', value: amountRaw, row: r }); continue;
    }
    amount = round2(amount);

    // ---- paid date (blank = still open, not an error)
    const paidRaw = map.paid !== undefined && r[map.paid] !== undefined ? String(r[map.paid]).trim() : '';
    let paidParts = null;
    let isPaid = false;
    if (paidRaw) {
      paidParts = parseDate(paidRaw, dateOrder);
      if (!paidParts) { skipped.push({ line, reason: 'unreadable_paid_date', value: paidRaw, row: r }); continue; }
      isPaid = true;
    }

    const issuedDay = dayNumber(issuedParts);
    let paidDay = null;
    let daysToPay = null;
    if (isPaid) {
      paidDay = dayNumber(paidParts);
      daysToPay = paidDay - issuedDay;
      if (daysToPay < 0) { skipped.push({ line, reason: 'paid_before_issued', value: `${toISO(issuedParts)} -> ${toISO(paidParts)}`, row: r }); continue; }
    }

    // ---- due basis: explicit due column > parseable terms > assumed net-30
    const termsRaw = map.terms !== undefined && r[map.terms] !== undefined ? String(r[map.terms]).trim() : '';
    const termsDays = parseTerms(termsRaw);
    const dueRaw = map.due !== undefined && r[map.due] !== undefined ? String(r[map.due]).trim() : '';
    const dueParts = dueRaw ? parseDate(dueRaw, dateOrder) : null;

    let dueDay;
    let dueBasis;
    let dueDate;
    if (dueParts) {
      dueDay = dayNumber(dueParts);
      dueDate = toISO(dueParts);
      dueBasis = 'due_column';
    } else if (termsDays !== null) {
      dueDay = issuedDay + termsDays;
      dueDate = null;
      dueBasis = 'terms';
    } else {
      dueDay = issuedDay + DEFAULT_NET_DAYS;
      dueDate = null;
      dueBasis = 'assumed_net_30';
    }

    if (map.currency !== undefined) {
      const cur = String(r[map.currency] || '').trim().toUpperCase();
      if (cur) currencies.add(cur);
    }

    invoices.push({
      line,
      issuedDate: toISO(issuedParts),
      issuedDay,
      issuedMonth: monthKey(issuedParts),
      client: clientRaw,
      clientKey: key,
      amount,
      paidDate: isPaid ? toISO(paidParts) : null,
      paidDay,
      isPaid,
      daysToPay,
      dueDate,
      dueDay,
      dueBasis,
      termsDays: termsDays === null ? null : termsDays,
      status: map.status !== undefined ? String(r[map.status] || '').trim() : '',
      reference: map.reference !== undefined ? String(r[map.reference] || '').trim() : '',
    });
  }

  if (invoices.length === 0) {
    const err = new Error(
      `No readable invoice rows. ${skipped.length} row(s) were flagged; the first reason was ` +
      `"${skipped.length ? skipped[0].reason : 'unknown'}".`
    );
    err.code = 'NO_VALID_ROWS';
    err.skipped = skipped;
    throw err;
  }

  invoices.sort((a, b) => (a.issuedDay - b.issuedDay) || (a.line - b.line));

  return {
    invoices,
    skipped,
    dateOrder,
    headerMap: map,
    hasDueColumn: map.due !== undefined,
    hasTermsColumn: map.terms !== undefined,
    hasStatus: map.status !== undefined,
    clientFromName: !!map._clientFromName,
    creditNoteCount,
    creditNoteTotal,
    currencies: Array.from(currencies).sort(),
    totalDataRows: grid.length - 1,
  };
}

module.exports = {
  ingestCsv, splitCsv, mapHeaders, parseDate, parseAmount, parseTerms, detectDateOrder,
  dayNumber, toISO, monthKey, clientKey, round2,
};
