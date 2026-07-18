// engine/recurring.js
//
// HFF — Recurring Charge Finder — deterministic recurrence detection.
//
// Pipeline:
//   1. Split charges from credits/refunds using the file's dominant sign.
//   2. Normalize each merchant string (strip POS prefixes, store numbers,
//      reference codes, city/state tails) into a grouping key.
//   3. For each merchant group, sort by date, compute day intervals, take the
//      MEDIAN interval, and classify it into a cadence bucket.
//   4. Score confidence from occurrence count + interval consistency (coefficient
//      of variation) + amount stability.
//   5. Report factual observations only: typical amount, amount drift, annualized
//      cost at the observed cadence, days since last seen. NEVER a suggestion.
'use strict';

const { CADENCES, IRREGULAR, OVERLAP_TAGS } = require('./constants');

// ------------------------------------------------------------ normalization

// Noise fragments commonly prepended by processors/banks.
const PREFIXES = [
  'POS ', 'POS DEBIT ', 'DEBIT CARD PURCHASE ', 'CARD PURCHASE ', 'RECURRING PAYMENT ',
  'PURCHASE AUTHORIZED ON ', 'ACH DEBIT ', 'ACH ', 'PMNT ', 'PAYMENT TO ',
  'SQ *', 'SQ*', 'TST* ', 'TST*', 'PP*', 'PAYPAL *', 'PAYPAL*', 'IC* ', 'IC*', 'WWW.', 'WEB ',
];

const US_STATES = new Set(('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO ' +
  'MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC').split(' '));

function normalizeMerchant(raw) {
  let s = String(raw).toUpperCase();
  s = s.replace(/[‘’“”]/g, '');
  s = s.replace(/\s+/g, ' ').trim();
  // strip leading noise prefixes (repeatedly)
  let changed = true;
  while (changed) {
    changed = false;
    for (const p of PREFIXES) {
      if (s.startsWith(p)) { s = s.slice(p.length).trim(); changed = true; }
    }
  }
  s = s.replace(/^\d{2}\/\d{2}\s+/, '');            // leading posting date
  s = s.replace(/\b(?:REF|ID|INV|TXN|AUTH|CONF)#?\s*[A-Z0-9-]{4,}\b/g, ' '); // ref codes
  s = s.replace(/#\s*\d+/g, ' ');                    // store numbers
  s = s.replace(/\b\d{5,}\b/g, ' ');                 // long digit runs
  s = s.replace(/\bX{2,}\d+\b/g, ' ');               // masked card tails
  s = s.replace(/\.(COM|NET|ORG|CO|IO|TV)\b/g, ' '); // domain tails
  s = s.replace(/[^A-Z0-9 &]/g, ' ');
  s = s.replace(/\s+/g, ' ').trim();
  // drop a trailing US state token and any trailing city word left behind
  const parts = s.split(' ');
  if (parts.length > 1 && US_STATES.has(parts[parts.length - 1])) parts.pop();
  s = parts.join(' ').trim();
  // keep the first 3 meaningful tokens — enough to identify the merchant,
  // short enough that per-charge suffixes collapse together
  const tokens = s.split(' ').filter((t) => t.length > 1 || /^\d$/.test(t));
  return tokens.slice(0, 3).join(' ') || String(raw).toUpperCase().trim();
}

// ------------------------------------------------------------ stats helpers

function median(nums) {
  if (!nums.length) return 0;
  const a = nums.slice().sort((x, y) => x - y);
  const mid = a.length >> 1;
  return a.length % 2 ? a[mid] : (a[mid - 1] + a[mid]) / 2;
}

function mean(nums) {
  if (!nums.length) return 0;
  return nums.reduce((s, n) => s + n, 0) / nums.length;
}

function stdev(nums) {
  if (nums.length < 2) return 0;
  const m = mean(nums);
  return Math.sqrt(nums.reduce((s, n) => s + (n - m) * (n - m), 0) / (nums.length - 1));
}

function round2(n) { return Math.round((n + Number.EPSILON) * 100) / 100; }

function classifyCadence(medianDays) {
  for (const c of CADENCES) {
    if (medianDays >= c.min && medianDays <= c.max) return c;
  }
  return { label: IRREGULAR, perYear: 0 };
}

function overlapTagFor(key) {
  for (const t of OVERLAP_TAGS) {
    if (t.patterns.some((p) => key.includes(p))) return t.tag;
  }
  return null;
}

// ------------------------------------------------------------ detection

// dominant sign: whichever sign holds more rows is treated as "a charge".
function dominantSign(transactions) {
  let neg = 0;
  let pos = 0;
  for (const t of transactions) { if (t.amount < 0) neg += 1; else pos += 1; }
  return neg > pos ? -1 : 1;
}

function detectRecurring(transactions, opts) {
  const options = opts || {};
  const minOccurrences = options.minOccurrences || 2;
  const sign = options.chargeSign || dominantSign(transactions);

  const charges = transactions.filter((t) => (sign < 0 ? t.amount < 0 : t.amount > 0));
  const credits = transactions.filter((t) => (sign < 0 ? t.amount >= 0 : t.amount <= 0));

  const groups = new Map();
  for (const t of charges) {
    const key = normalizeMerchant(t.description);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(Object.assign({}, t, { magnitude: Math.abs(t.amount) }));
  }

  const latestDay = charges.reduce((m, t) => Math.max(m, t.day), charges.length ? charges[0].day : 0);

  const recurring = [];
  const oneOff = [];

  for (const [key, rows] of groups) {
    rows.sort((a, b) => a.day - b.day);
    if (rows.length < minOccurrences) {
      oneOff.push({ merchantKey: key, label: rows[0].description, occurrences: rows.length, amount: round2(rows[0].magnitude), lastSeen: rows[0].date });
      continue;
    }

    const intervals = [];
    for (let i = 1; i < rows.length; i++) intervals.push(rows[i].day - rows[i - 1].day);
    const medInterval = median(intervals);
    const cadence = classifyCadence(medInterval);

    const amounts = rows.map((r) => r.magnitude);
    const typical = round2(median(amounts));
    const first = round2(amounts[0]);
    const latest = round2(amounts[amounts.length - 1]);
    const amountCv = typical > 0 ? stdev(amounts) / typical : 0;

    const intervalCv = medInterval > 0 ? stdev(intervals) / medInterval : 1;

    let confidence;
    if (cadence.label !== IRREGULAR && rows.length >= 3 && intervalCv <= 0.2 && amountCv <= 0.2) confidence = 'high';
    else if (cadence.label !== IRREGULAR && (rows.length >= 3 || intervalCv <= 0.25)) confidence = 'medium';
    else confidence = 'low';

    // Only surface as "recurring" when there is a real cadence signal, or when a
    // merchant repeats at least 3 times with stable amounts.
    const isRecurring = cadence.label !== IRREGULAR || (rows.length >= 3 && amountCv <= 0.1);
    if (!isRecurring) {
      oneOff.push({ merchantKey: key, label: rows[0].description, occurrences: rows.length, amount: typical, lastSeen: rows[rows.length - 1].date });
      continue;
    }

    const perYear = cadence.perYear || (medInterval > 0 ? 365 / medInterval : 0);
    const annualized = round2(typical * perYear);
    const daysSinceLast = latestDay - rows[rows.length - 1].day;
    const dormant = medInterval > 0 && daysSinceLast > medInterval * 2.5;
    const changePct = first > 0 ? round2(((latest - first) / first) * 100) : 0;

    recurring.push({
      merchantKey: key,
      label: rows[0].description,
      occurrences: rows.length,
      cadence: cadence.label,
      medianIntervalDays: round2(medInterval),
      intervalConsistency: round2(1 - Math.min(intervalCv, 1)),
      typicalAmount: typical,
      firstAmount: first,
      latestAmount: latest,
      minAmount: round2(Math.min.apply(null, amounts)),
      maxAmount: round2(Math.max.apply(null, amounts)),
      amountChangePct: changePct,
      amountChanged: Math.abs(changePct) >= 5,
      monthlyEquivalent: round2((typical * perYear) / 12),
      annualizedAmount: annualized,
      firstSeen: rows[0].date,
      lastSeen: rows[rows.length - 1].date,
      daysSinceLastSeen: daysSinceLast,
      noChargeSinceExpected: dormant,
      confidence,
      overlapTag: overlapTagFor(key),
      accounts: Array.from(new Set(rows.map((r) => r.account).filter(Boolean))),
      occurrenceRows: rows.map((r) => ({ line: r.line, date: r.date, amount: round2(r.magnitude), description: r.description })),
    });
  }

  recurring.sort((a, b) => (b.annualizedAmount - a.annualizedAmount) || a.merchantKey.localeCompare(b.merchantKey));
  oneOff.sort((a, b) => (b.amount - a.amount) || a.merchantKey.localeCompare(b.merchantKey));

  // Factual overlap groups: two or more DISTINCT recurring merchants sharing a tag.
  const tagMap = new Map();
  for (const r of recurring) {
    if (!r.overlapTag) continue;
    if (!tagMap.has(r.overlapTag)) tagMap.set(r.overlapTag, []);
    tagMap.get(r.overlapTag).push(r.merchantKey);
  }
  const overlaps = [];
  for (const [tag, merchants] of tagMap) {
    if (merchants.length >= 2) {
      const combined = recurring
        .filter((r) => r.overlapTag === tag)
        .reduce((s, r) => s + r.annualizedAmount, 0);
      overlaps.push({ tag, merchants, count: merchants.length, combinedAnnualized: round2(combined) });
    }
  }
  overlaps.sort((a, b) => b.combinedAnnualized - a.combinedAnnualized);

  return {
    chargeSign: sign,
    chargeCount: charges.length,
    creditCount: credits.length,
    recurring,
    oneOff,
    overlaps,
    windowStart: charges.length ? charges[0].date : null,
    windowEnd: charges.length ? charges[charges.length - 1].date : null,
  };
}

module.exports = { detectRecurring, normalizeMerchant, classifyCadence, median, stdev, round2, dominantSign };
