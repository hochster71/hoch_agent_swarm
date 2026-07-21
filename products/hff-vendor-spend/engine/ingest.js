// engine/ingest.js
//
// HFF — Vendor Spend Rollup — deterministic CSV ingest.
//
// DESIGN RULE (inherited from hff-invoice-aging / hff-recurring-charges /
// hff-client-concentration / hff-hourly-rate): unparseable rows are FLAGGED,
// never silently dropped. Every skipped row comes back with its 1-based CSV
// line number and a machine-readable reason, so the buyer can see exactly what
// the engine could not read.
//
// Required columns: date, vendor, amount.
// Optional columns: category, description, reference, status, currency.
//
// Handles: RFC4180 quoting (incl. escaped ""), CRLF, BOM, header aliasing,
// ISO / US / UK dates (with whole-file auto-detection), separate debit/credit
// columns, EU decimal commas, currency symbols, parenthesised negatives,
// trailing-minus negatives, and payment-processor prefixes on vendor strings.
//
// SIGN CONVENTION: this report is about money PAID OUT. A positive amount is a
// payment. A negative amount is treated as a refund/credit against that vendor,
// counted separately and disclosed — never silently netted away in the counts.
'use strict';

const { VENDOR_SUFFIXES, PROCESSOR_PREFIXES, MAX_LINE_AMOUNT } = require('./constants');

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
  date: [
    'date', 'transaction date', 'posted date', 'post date', 'payment date', 'bill date',
    'invoice date', 'paid date', 'date paid', 'posting date', 'trans date', 'day',
  ],
  vendor: [
    'vendor', 'supplier', 'payee', 'merchant', 'description', 'name', 'vendor name',
    'supplier name', 'payee name', 'merchant name', 'paid to', 'bill from', 'company',
    'account name', 'counterparty',
  ],
  amount: [
    'amount', 'total', 'amount (usd)', 'amount usd', 'value', 'cost', 'spend', 'paid',
    'payment', 'payment amount', 'transaction amount', 'gross', 'gross amount', 'sum',
  ],
  debit: ['debit', 'withdrawal', 'withdrawals', 'money out', 'paid out', 'debit amount', 'outflow'],
  credit: ['credit', 'deposit', 'deposits', 'money in', 'paid in', 'credit amount', 'inflow', 'refund'],
  category: ['category', 'expense category', 'account', 'gl account', 'type', 'class', 'expense type'],
  memo: ['memo', 'notes', 'note', 'details', 'line description', 'item', 'particulars'],
  reference: ['reference', 'ref', 'invoice', 'invoice number', 'invoice #', 'bill number', 'transaction id', 'id'],
  status: ['status', 'payment status', 'state', 'paid?'],
  currency: ['currency', 'ccy', 'curr'],
};

// "description" is ambiguous: bank exports use it as the vendor string, while
// bill exports use it as a free-text memo alongside a real vendor column. It is
// only accepted as the vendor when no better vendor column exists.
const AMBIGUOUS_VENDOR_HEADERS = ['description', 'name'];

function normHeader(h) {
  return String(h).trim().toLowerCase().replace(/\s+/g, ' ').replace(/[^a-z0-9 ()#?]/g, '');
}

function mapHeaders(headerRow) {
  const map = {};
  const weakVendor = { idx: undefined };

  headerRow.forEach((raw, idx) => {
    const h = normHeader(raw);
    for (const [canon, aliases] of Object.entries(HEADER_ALIASES)) {
      if (!aliases.includes(h)) continue;
      if (canon === 'vendor' && AMBIGUOUS_VENDOR_HEADERS.includes(h)) {
        if (weakVendor.idx === undefined) weakVendor.idx = idx;
        continue;
      }
      if (map[canon] !== undefined) continue;
      map[canon] = idx;
      break;
    }
  });

  // Fall back to the ambiguous header only if nothing stronger claimed vendor.
  if (map.vendor === undefined && weakVendor.idx !== undefined) {
    map.vendor = weakVendor.idx;
    map._vendorFromDescription = true;
  }
  // If "description" became the vendor it must not also serve as the memo.
  if (map._vendorFromDescription && map.memo === map.vendor) delete map.memo;

  // Separate debit/credit columns satisfy the amount requirement.
  if (map.amount === undefined && (map.debit !== undefined || map.credit !== undefined)) {
    map._amountMode = 'debit_credit';
  } else {
    map._amountMode = 'single';
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

// ---------------------------------------------------------------- vendor keys

// Two spellings of the same vendor should land in one bucket. This is a STRING
// normalization only — there is no vendor database behind it, and every merge
// is disclosed in the report.
function vendorKey(raw) {
  let s = String(raw).toUpperCase();
  s = s.replace(/&/g, ' AND ');
  s = s.replace(/[^A-Z0-9 ]+/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();

  // Strip payment-processor noise from the front.
  let stripped = true;
  while (stripped) {
    stripped = false;
    for (const p of PROCESSOR_PREFIXES) {
      const pk = p.replace(/[^A-Z0-9 ]+/g, ' ').replace(/\s+/g, ' ');
      if (s.startsWith(pk) && s.length > pk.length) { s = s.slice(pk.length).trim(); stripped = true; break; }
    }
  }

  // Trailing store/reference numbers a card export tacks on ("STARBUCKS 00412").
  s = s.replace(/\s+#?\d{3,}$/, '').trim();

  if (s.startsWith('THE ')) s = s.slice(4);
  let changed = true;
  while (changed) {
    changed = false;
    for (const suf of VENDOR_SUFFIXES) {
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
    const err = new Error('The file needs a header row and at least one payment row.');
    err.code = 'NO_ROWS';
    throw err;
  }
  const headerRow = grid[0];
  const map = mapHeaders(headerRow);

  const missing = [];
  if (map.date === undefined) missing.push('date');
  if (map.vendor === undefined) missing.push('vendor');
  if (map.amount === undefined && map.debit === undefined && map.credit === undefined) missing.push('amount');
  if (missing.length) {
    const err = new Error(
      `Could not find these required column(s): ${missing.join(', ')}. ` +
      `Header seen: ${headerRow.map((h) => String(h).trim()).filter(Boolean).join(', ') || '(blank)'}.`
    );
    err.code = 'MISSING_COLUMNS';
    err.missing = missing;
    throw err;
  }

  const rawDates = grid.slice(1).map((r) => (r[map.date] === undefined ? '' : r[map.date]));
  const dateOrder = detectDateOrder(rawDates, options.dateOrder);

  const payments = [];
  const skipped = [];
  let refundCount = 0;
  let refundTotal = 0;
  const currencies = new Set();

  for (let i = 1; i < grid.length; i++) {
    const r = grid[i];
    const line = i + 1; // 1-based, header counts as line 1
    if (r.every((f) => String(f).trim() === '')) continue;

    const dRaw = r[map.date] === undefined ? '' : r[map.date];
    const vRaw = r[map.vendor] === undefined ? '' : String(r[map.vendor]).trim();

    const dParts = parseDate(dRaw, dateOrder);
    if (!dParts) { skipped.push({ line, reason: 'unreadable_date', value: String(dRaw).trim(), row: r }); continue; }
    if (!vRaw) { skipped.push({ line, reason: 'missing_vendor', value: '', row: r }); continue; }
    const key = vendorKey(vRaw);
    if (!key) { skipped.push({ line, reason: 'unusable_vendor_name', value: vRaw, row: r }); continue; }

    // ---- amount, from either a single column or a debit/credit pair
    let amount = null;
    let rawSeen = '';
    if (map._amountMode === 'debit_credit') {
      const d = map.debit !== undefined ? parseAmount(r[map.debit] === undefined ? '' : r[map.debit]) : null;
      const c = map.credit !== undefined ? parseAmount(r[map.credit] === undefined ? '' : r[map.credit]) : null;
      rawSeen = [
        map.debit !== undefined ? String(r[map.debit] || '').trim() : '',
        map.credit !== undefined ? String(r[map.credit] || '').trim() : '',
      ].filter(Boolean).join(' / ');
      // A debit is money out (positive spend); a credit is money back.
      if (d !== null && d !== 0) amount = Math.abs(d);
      else if (c !== null && c !== 0) amount = -Math.abs(c);
      else if (d === 0 || c === 0) amount = 0;
    } else {
      rawSeen = String(r[map.amount] === undefined ? '' : r[map.amount]).trim();
      amount = parseAmount(rawSeen);
    }

    if (amount === null) { skipped.push({ line, reason: 'unreadable_amount', value: rawSeen, row: r }); continue; }
    if (amount === 0) { skipped.push({ line, reason: 'zero_amount', value: rawSeen, row: r }); continue; }
    if (Math.abs(amount) > MAX_LINE_AMOUNT) {
      skipped.push({ line, reason: 'implausible_amount', value: rawSeen, row: r }); continue;
    }
    amount = round2(amount);

    const isRefund = amount < 0;
    if (isRefund) { refundCount += 1; refundTotal = round2(refundTotal + Math.abs(amount)); }

    if (map.currency !== undefined) {
      const cur = String(r[map.currency] || '').trim().toUpperCase();
      if (cur) currencies.add(cur);
    }

    payments.push({
      line,
      date: toISO(dParts),
      day: dayNumber(dParts),
      month: monthKey(dParts),
      vendor: vRaw,
      vendorKey: key,
      amount,                       // signed: + paid out, - refund/credit
      isRefund,
      category: map.category !== undefined ? String(r[map.category] || '').trim() : '',
      memo: map.memo !== undefined ? String(r[map.memo] || '').trim() : '',
      reference: map.reference !== undefined ? String(r[map.reference] || '').trim() : '',
      status: map.status !== undefined ? String(r[map.status] || '').trim() : '',
    });
  }

  if (payments.length === 0) {
    const err = new Error(
      `No readable payment rows. ${skipped.length} row(s) were flagged; the first reason was ` +
      `"${skipped.length ? skipped[0].reason : 'unknown'}".`
    );
    err.code = 'NO_VALID_ROWS';
    err.skipped = skipped;
    throw err;
  }

  payments.sort((a, b) => (a.day - b.day) || (a.line - b.line));

  return {
    payments,
    skipped,
    dateOrder,
    amountMode: map._amountMode,
    headerMap: map,
    hasCategory: map.category !== undefined,
    hasReference: map.reference !== undefined,
    hasStatus: map.status !== undefined,
    vendorFromDescription: !!map._vendorFromDescription,
    refundCount,
    refundTotal,
    currencies: Array.from(currencies).sort(),
    totalDataRows: grid.length - 1,
  };
}

module.exports = {
  ingestCsv, splitCsv, mapHeaders, parseDate, parseAmount, detectDateOrder,
  dayNumber, toISO, monthKey, vendorKey, round2,
};
