// engine/ingest.js
//
// HFF — Effective Hourly Rate Report — deterministic CSV ingest.
//
// DESIGN RULE (inherited from hff-invoice-aging / hff-recurring-charges /
// hff-client-concentration): unparseable rows are FLAGGED, never silently
// dropped. Every skipped row comes back with its 1-based CSV line number and a
// machine-readable reason, so the buyer can see exactly what the engine could
// not read.
//
// Required columns: date, client, duration.
// Optional columns: project, billable, amount, rate, description.
//
// Handles: RFC4180 quoting (incl. escaped ""), CRLF, BOM, header aliasing,
// ISO / US / UK dates (with whole-file auto-detection), durations as decimal
// hours, H:MM[:SS], "7h 30m" / "45 min" forms, minute-unit columns, EU decimal
// commas, currency symbols on amounts/rates, parenthesised negatives.
'use strict';

const { CLIENT_SUFFIXES, MAX_ENTRY_HOURS } = require('./constants');

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
    'date', 'start date', 'start_date', 'work date', 'entry date', 'day',
    'started', 'date worked', 'log date',
  ],
  client: [
    'client', 'customer', 'customer name', 'client name', 'account', 'account name',
    'company', 'company name', 'bill to', 'billto', 'billed to',
  ],
  duration: [
    'duration', 'hours', 'time', 'duration (h)', 'duration (hours)', 'hours worked',
    'time spent', 'duration (decimal)', 'decimal hours', 'logged hours', 'time (h)',
    'billable hours', 'hrs', 'total hours',
  ],
  duration_minutes: [
    'minutes', 'mins', 'duration (minutes)', 'duration (min)', 'time (min)', 'minutes worked',
  ],
  project: ['project', 'project name', 'job', 'matter', 'engagement'],
  task: ['task', 'task name', 'activity'],
  billable: ['billable', 'is billable', 'billable?', 'billing', 'billable status', 'billing status'],
  amount: [
    'amount', 'billed amount', 'earnings', 'revenue', 'income', 'amount (usd)',
    'billable amount', 'fee', 'billed', 'invoiced amount',
  ],
  rate: ['rate', 'hourly rate', 'rate (usd)', 'bill rate', 'billing rate', 'price per hour', 'rate per hour'],
  description: ['description', 'notes', 'note', 'task description', 'details', 'memo'],
};

function normHeader(h) {
  return String(h).trim().toLowerCase().replace(/\s+/g, ' ').replace(/[^a-z0-9 ()?]/g, '');
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
  // A minutes-unit column satisfies the duration requirement.
  if (map.duration === undefined && map.duration_minutes !== undefined) {
    map.duration = map.duration_minutes;
    map._durationUnit = 'minutes';
  } else {
    map._durationUnit = 'hours';
  }
  // "Task" can stand in for a missing project column.
  if (map.project === undefined && map.task !== undefined) map.project = map.task;
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

// ---------------------------------------------------------------- durations

// Returns HOURS as a number, or null if unreadable. Never negative.
function parseDuration(raw, unit) {
  let s = String(raw).trim().toLowerCase();
  if (!s) return null;

  // H:MM or H:MM:SS
  let m = s.match(/^(\d{1,3}):([0-5]?\d)(?::([0-5]?\d))?$/);
  if (m) return +m[1] + (+m[2]) / 60 + (m[3] ? (+m[3]) / 3600 : 0);

  // "7h 30m", "7h30m", "7h", "30m", "45 min", "90 mins", "1.5h"
  m = s.match(/^(?:(\d+(?:[.,]\d+)?)\s*h(?:ours?|rs?)?)?\s*(?:(\d+(?:[.,]\d+)?)\s*m(?:in(?:ute)?s?)?)?$/);
  if (m && (m[1] !== undefined || m[2] !== undefined)) {
    const h = m[1] ? Number(m[1].replace(',', '.')) : 0;
    const mins = m[2] ? Number(m[2].replace(',', '.')) : 0;
    if (!Number.isFinite(h) || !Number.isFinite(mins)) return null;
    return h + mins / 60;
  }

  // Plain number; EU decimal comma accepted. Unit comes from the header.
  s = s.replace(/,/g, '.');
  if (!/^\d*\.?\d+$/.test(s)) return null;
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return unit === 'minutes' ? n / 60 : n;
}

function roundHours(h) {
  return Math.round(h * 10000) / 10000;
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

// ---------------------------------------------------------------- billable

// true / false / null (unknown). Never throws.
function parseBillable(raw) {
  const s = String(raw).trim().toLowerCase();
  if (!s) return null;
  if (['yes', 'y', 'true', '1', 'billable', 'billed'].includes(s)) return true;
  if (['no', 'n', 'false', '0', 'non-billable', 'nonbillable', 'not billable', 'non billable', 'unbilled'].includes(s)) return false;
  return null;
}

// ---------------------------------------------------------------- client keys

// Two spellings of the same client should land in one bucket. This is a STRING
// normalization only — there is no company database behind it.
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
      if (s === suf) { return s; }
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
    const err = new Error('The file needs a header row and at least one time-entry row.');
    err.code = 'NO_ROWS';
    throw err;
  }
  const headerRow = grid[0];
  const map = mapHeaders(headerRow);
  const missing = ['date', 'client', 'duration'].filter((k) => map[k] === undefined);
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
  const durationUnit = map._durationUnit;

  const entries = [];
  const skipped = [];
  let negativeAmountsIgnored = 0;

  for (let i = 1; i < grid.length; i++) {
    const r = grid[i];
    const line = i + 1; // 1-based, header counts as line 1
    if (r.every((f) => String(f).trim() === '')) continue;

    const dRaw = r[map.date] === undefined ? '' : r[map.date];
    const cRaw = r[map.client] === undefined ? '' : String(r[map.client]).trim();
    const hRaw = r[map.duration] === undefined ? '' : r[map.duration];

    const dParts = parseDate(dRaw, dateOrder);
    if (!dParts) { skipped.push({ line, reason: 'unreadable_date', value: String(dRaw).trim(), row: r }); continue; }
    if (!cRaw) { skipped.push({ line, reason: 'missing_client', value: '', row: r }); continue; }
    const key = clientKey(cRaw);
    if (!key) { skipped.push({ line, reason: 'unusable_client_name', value: cRaw, row: r }); continue; }

    const hoursRaw = parseDuration(hRaw, durationUnit);
    if (hoursRaw === null) { skipped.push({ line, reason: 'unreadable_duration', value: String(hRaw).trim(), row: r }); continue; }
    if (hoursRaw <= 0) { skipped.push({ line, reason: 'zero_duration', value: String(hRaw).trim(), row: r }); continue; }
    if (hoursRaw > MAX_ENTRY_HOURS) { skipped.push({ line, reason: 'implausible_duration', value: String(hRaw).trim(), row: r }); continue; }
    const hours = roundHours(hoursRaw);

    // Billing figures are OPTIONAL. A negative amount is ignored (counted and
    // disclosed), because a time entry with a negative billed amount has no
    // deterministic meaning here — the hours themselves still count.
    let amount = null;
    let revenueSource = null;
    if (map.amount !== undefined) {
      const a = parseAmount(r[map.amount] === undefined ? '' : r[map.amount]);
      if (a !== null && a < 0) { negativeAmountsIgnored += 1; }
      else if (a !== null && a > 0) { amount = a; revenueSource = 'amount'; }
      else if (a === 0) { amount = 0; revenueSource = 'amount'; }
    }
    if (amount === null && map.rate !== undefined) {
      const rate = parseAmount(r[map.rate] === undefined ? '' : r[map.rate]);
      if (rate !== null && rate > 0) {
        amount = Math.round(rate * hours * 100) / 100;
        revenueSource = 'derived_from_rate';
      }
    }

    const billable = map.billable !== undefined
      ? parseBillable(r[map.billable] === undefined ? '' : r[map.billable])
      : null;

    entries.push({
      line,
      date: toISO(dParts),
      day: dayNumber(dParts),
      month: monthKey(dParts),
      client: cRaw,
      clientKey: key,
      project: map.project !== undefined ? String(r[map.project] || '').trim() : '',
      description: map.description !== undefined ? String(r[map.description] || '').trim() : '',
      hours,
      billable,
      amount,
      revenueSource,
    });
  }

  if (entries.length === 0) {
    const err = new Error(
      `No readable time-entry rows. ${skipped.length} row(s) were flagged; the first reason was ` +
      `"${skipped.length ? skipped[0].reason : 'unknown'}".`
    );
    err.code = 'NO_VALID_ROWS';
    err.skipped = skipped;
    throw err;
  }

  entries.sort((a, b) => (a.day - b.day) || (a.line - b.line));

  return {
    entries,
    skipped,
    dateOrder,
    durationUnit,
    headerMap: map,
    hasProject: map.project !== undefined,
    hasBillable: map.billable !== undefined,
    hasAmount: map.amount !== undefined,
    hasRate: map.rate !== undefined,
    negativeAmountsIgnored,
    totalDataRows: grid.length - 1,
  };
}

module.exports = {
  ingestCsv, splitCsv, parseDate, parseAmount, parseDuration, parseBillable,
  detectDateOrder, dayNumber, toISO, monthKey, clientKey, roundHours,
};
