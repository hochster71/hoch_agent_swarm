// engine/ingest.js
//
// HFF — Recurring Charge Finder — deterministic CSV ingest.
//
// DESIGN RULE (inherited from hff-invoice-aging): unparseable rows are FLAGGED,
// never silently dropped. Every skipped row comes back with its 1-based line
// number and a machine-readable reason so the buyer can see exactly what the
// engine could not read.
//
// Handles: RFC4180 quoting (incl. escaped ""), CRLF, BOM, header aliasing,
// ISO / US / UK dates (with auto-detection), currency symbols, thousands
// separators, EU decimal commas, parenthesised negatives, trailing-minus.
'use strict';

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
  // drop trailing fully-empty rows
  while (rows.length && rows[rows.length - 1].every((f) => String(f).trim() === '')) rows.pop();
  return rows;
}

// ---------------------------------------------------------------- header map

const HEADER_ALIASES = {
  date: ['date', 'transaction date', 'transaction_date', 'posted date', 'posted_date', 'post date', 'trans date', 'trans_date', 'booking date', 'value date'],
  description: ['description', 'merchant', 'name', 'payee', 'memo', 'details', 'narrative', 'transaction description', 'merchant name', 'reference'],
  amount: ['amount', 'debit', 'charge', 'value', 'transaction amount', 'amount (usd)', 'withdrawal'],
  account: ['account', 'account name', 'card', 'card last 4', 'source'],
  category: ['category', 'type', 'transaction type'],
};

function normHeader(h) {
  return String(h).trim().toLowerCase().replace(/\s+/g, ' ').replace(/[^a-z0-9 ()]/g, '');
}

function mapHeaders(headerRow) {
  const map = {};
  headerRow.forEach((raw, idx) => {
    const h = normHeader(raw);
    for (const [canon, aliases] of Object.entries(HEADER_ALIASES)) {
      if (map[canon] !== undefined) continue;
      if (aliases.includes(h)) { map[canon] = idx; break; }
    }
  });
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

// Returns { y, m, d } parts or null. `order` is 'us' | 'uk' for ambiguous slash dates.
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
    let a = +m[1], b = +m[2], y = +m[3];
    if (y < 100) y += y < 70 ? 2000 : 1900;
    const mo = order === 'uk' ? b : a;
    const d = order === 'uk' ? a : b;
    return validYMD(y, mo, d) ? { y, m: mo, d } : null;
  }
  return null;
}

// Detect slash-date order across the whole file. Explicit wins; else infer.
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
  // EU style 1.234,56  ->  1234.56
  if (/^\d{1,3}(\.\d{3})+,\d{1,2}$/.test(s)) s = s.replace(/\./g, '').replace(',', '.');
  else if (/^\d+,\d{1,2}$/.test(s)) s = s.replace(',', '.');
  else s = s.replace(/,/g, '');
  if (!/^\d*\.?\d+$/.test(s)) return null;
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return negative ? -n : n;
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
    const err = new Error('The file needs a header row and at least one transaction row.');
    err.code = 'NO_ROWS';
    throw err;
  }
  const headerRow = grid[0];
  const map = mapHeaders(headerRow);
  const missing = ['date', 'description', 'amount'].filter((k) => map[k] === undefined);
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

  const transactions = [];
  const skipped = [];

  for (let i = 1; i < grid.length; i++) {
    const r = grid[i];
    const line = i + 1; // 1-based including header
    if (r.every((f) => String(f).trim() === '')) continue;

    const dRaw = r[map.date] === undefined ? '' : r[map.date];
    const desc = r[map.description] === undefined ? '' : String(r[map.description]).trim();
    const aRaw = r[map.amount] === undefined ? '' : r[map.amount];

    const dParts = parseDate(dRaw, dateOrder);
    if (!dParts) { skipped.push({ line, reason: 'unreadable_date', value: String(dRaw).trim(), row: r }); continue; }
    if (!desc) { skipped.push({ line, reason: 'missing_description', value: '', row: r }); continue; }
    const amount = parseAmount(aRaw);
    if (amount === null) { skipped.push({ line, reason: 'unreadable_amount', value: String(aRaw).trim(), row: r }); continue; }
    if (amount === 0) { skipped.push({ line, reason: 'zero_amount', value: String(aRaw).trim(), row: r }); continue; }

    transactions.push({
      line,
      date: toISO(dParts),
      day: dayNumber(dParts),
      description: desc,
      amount,
      account: map.account !== undefined ? String(r[map.account] || '').trim() : '',
      category: map.category !== undefined ? String(r[map.category] || '').trim() : '',
    });
  }

  if (transactions.length === 0) {
    const err = new Error(
      `No readable transactions. ${skipped.length} row(s) were flagged; the first reason was ` +
      `"${skipped.length ? skipped[0].reason : 'unknown'}".`
    );
    err.code = 'NO_VALID_ROWS';
    err.skipped = skipped;
    throw err;
  }

  transactions.sort((a, b) => (a.day - b.day) || (a.line - b.line));

  return { transactions, skipped, dateOrder, headerMap: map, totalDataRows: grid.length - 1 };
}

module.exports = { ingestCsv, splitCsv, parseDate, parseAmount, detectDateOrder, dayNumber, toISO };
