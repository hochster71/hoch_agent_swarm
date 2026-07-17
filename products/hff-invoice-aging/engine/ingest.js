// engine/ingest.js
//
// Stage 1: Ingest & normalize an AR / invoice CSV. Auto-detects columns, computes the
// outstanding balance per invoice, and normalizes dates. Unparseable rows are FLAGGED
// (rejected list with a reason), never silently dropped.
//
// Accepted logical columns (auto-detected, tolerant of common export headers):
//   invoice   — invoice number / id            (optional; synthesized if absent)
//   customer  — who owes                        (required)
//   issue     — invoice / issue date           (optional)
//   due       — due date                        (required — aging is measured from here)
//   amount    — invoice total / amount          (required unless a balance column exists)
//   paid      — amount paid to date             (optional)
//   balance   — outstanding balance             (optional; if present, used directly)
//   status    — paid/open/void text             (optional; 'paid'/'void' zeroes the balance)

'use strict';

// Minimal, dependency-free CSV parser (handles quotes, escaped quotes, embedded commas/newlines).
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
        if (s[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { record.push(field); field = ''; }
    else if (c === '\n') { record.push(field); rows.push(record); record = []; field = ''; }
    else field += c;
  }
  if (field.length > 0 || record.length > 0) { record.push(field); rows.push(record); }
  return rows.filter((r) => !(r.length === 1 && r[0].trim() === ''));
}

function norm(h) {
  return String(h || '').trim().toLowerCase().replace(/[^a-z0-9]/g, '');
}

function detectColumns(headers) {
  const map = {};
  const normed = headers.map(norm);
  const find = (candidates) => {
    for (const cand of candidates) {
      const idx = normed.indexOf(cand);
      if (idx !== -1) return idx;
    }
    for (let i = 0; i < normed.length; i++) {
      if (candidates.some((cand) => normed[i].includes(cand))) return i;
    }
    return -1;
  };
  map.invoice = find(['invoice', 'invoiceno', 'invoicenumber', 'invoiceid', 'number', 'docnumber', 'ref']);
  map.customer = find(['customer', 'client', 'company', 'payer', 'account', 'name', 'billto', 'debtor']);
  map.issue = find(['issuedate', 'invoicedate', 'date', 'createddate', 'issued']);
  map.due = find(['duedate', 'due', 'paymentdue', 'datedue']);
  map.amount = find(['amount', 'total', 'invoicetotal', 'invoiceamount', 'grandtotal', 'value']);
  map.paid = find(['amountpaid', 'paid', 'paidamount', 'received']);
  map.balance = find(['balance', 'balancedue', 'amountdue', 'outstanding', 'openbalance', 'owed', 'remaining']);
  map.status = find(['status', 'state', 'paidstatus']);
  return map;
}

function parseAmount(raw) {
  if (raw === undefined || raw === null) return NaN;
  let s = String(raw).trim();
  if (s === '') return NaN;
  let negative = false;
  if (/^\(.*\)$/.test(s)) { negative = true; s = s.slice(1, -1); }
  s = s.replace(/[$£€,\s]/g, '');
  if (s.startsWith('-')) { negative = true; s = s.slice(1); }
  const n = Number(s);
  if (!isFinite(n)) return NaN;
  return negative ? -n : n;
}

function parseDate(raw) {
  const s = String(raw || '').trim();
  if (!s) return null;
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) return isoDate(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (m) { let y = +m[3]; if (y < 100) y += 2000; return isoDate(y, +m[1], +m[2]); }
  m = s.match(/^(\d{1,2})[-\s]([A-Za-z]{3})[-\s](\d{2,4})/);
  if (m) {
    const months = { jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12 };
    const mo = months[m[2].toLowerCase()];
    let y = +m[3]; if (y < 100) y += 2000;
    if (mo) return isoDate(y, mo, +m[1]);
  }
  return null;
}

function isoDate(y, m, d) {
  if (!(m >= 1 && m <= 12 && d >= 1 && d <= 31)) return null;
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// ingest(csvText) -> { invoices: [...], rejected: [...], columns }
// Each invoice: { row, invoice, customer, issueDate, dueDate, amount, paid, balance, statusRaw }
function ingest(csvText) {
  const rows = parseCsv(csvText);
  if (rows.length === 0) return { invoices: [], rejected: [], columns: {} };

  const headers = rows[0];
  const cols = detectColumns(headers);

  const hasAmount = cols.amount !== -1;
  const hasBalance = cols.balance !== -1;

  if (cols.customer === -1 || cols.due === -1 || (!hasAmount && !hasBalance)) {
    return {
      invoices: [],
      rejected: [{
        row: 1,
        reason: 'Could not detect required columns (need customer, due date, and amount OR balance).',
        raw: headers.join(','),
      }],
      columns: cols,
    };
  }

  const invoices = [];
  const rejected = [];

  for (let r = 1; r < rows.length; r++) {
    const cells = rows[r];
    const rawRow = cells.join(',');

    const customer = String(cells[cols.customer] || '').trim();
    const dueDate = parseDate(cells[cols.due]);
    const issueDate = cols.issue !== -1 ? parseDate(cells[cols.issue]) : null;
    const invoiceNo = cols.invoice !== -1 ? String(cells[cols.invoice] || '').trim() : '';
    const statusRaw = cols.status !== -1 ? String(cells[cols.status] || '').trim() : '';

    const amount = hasAmount ? parseAmount(cells[cols.amount]) : NaN;
    const paid = cols.paid !== -1 ? parseAmount(cells[cols.paid]) : NaN;
    let balance = hasBalance ? parseAmount(cells[cols.balance]) : NaN;

    // Derive balance if not given directly.
    if (isNaN(balance)) {
      if (!isNaN(amount)) balance = round2(amount - (isNaN(paid) ? 0 : paid));
    }

    const reasons = [];
    if (!customer) reasons.push('missing customer');
    if (!dueDate) reasons.push('unparseable due date');
    if (isNaN(balance)) reasons.push('unparseable amount/balance');

    if (reasons.length) {
      rejected.push({ row: r + 1, reason: reasons.join('; '), raw: rawRow });
      continue;
    }

    // A 'paid' or 'void' status zeroes the outstanding balance regardless of numbers.
    const st = statusRaw.toLowerCase();
    if (st.includes('paid') || st.includes('void') || st.includes('cancel')) balance = 0;

    invoices.push({
      row: r + 1,
      invoice: invoiceNo || `row-${r + 1}`,
      customer,
      issueDate,
      dueDate,
      amount: isNaN(amount) ? round2(balance) : round2(amount),
      paid: isNaN(paid) ? null : round2(paid),
      balance: round2(Math.max(0, balance)),
      statusRaw,
    });
  }

  return { invoices, rejected, columns: cols };
}

module.exports = { ingest, parseCsv, detectColumns, parseAmount, parseDate, round2 };
