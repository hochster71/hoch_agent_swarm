// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL), ported from the proven
// hff-vendor-spend / hff-hourly-rate linter and retuned for the payment-timing
// domain.
//
// Scans every engine-authored string. FAILS CLOSED: if any banned phrase
// appears, the engine refuses to release the report — paid or free. This
// product describes the invoices recorded in the uploaded file and the payment
// timing those invoices arithmetically produce. It never tells the reader to
// chase a client, send anyone to collections, add a fee, or drop a client, and
// it never judges a client as good or bad. Neutral, factual descriptors like
// "paid late", "overdue", "outstanding", and "still open" are NOT banned — they
// describe what the dates in the file arithmetically show.
'use strict';

const BANNED_PHRASES = [
  // collections / dunning instruction
  'you should chase',
  'you should follow up',
  'you should call',
  'you should email',
  'you should remind',
  'chase the client',
  'chase this client',
  'chase them',
  'chase up',
  'go after',
  'send to collections',
  'send them to collections',
  'send it to collections',
  'refer to collections',
  'collections agency',
  'collection agency',
  'debt collector',
  'hire a collector',
  'a late fee',
  'late fees',
  'charge a fee',
  'charge interest',
  'add interest',
  'apply interest',
  'a penalty',
  'penalise',
  'penalize',
  'demand payment',
  'small claims',
  'take legal action',
  'take them to court',
  'a lawsuit',
  'withhold work',
  'stop working with',
  'cut them off',
  'cut off the client',
  'fire the client',
  'fire this client',
  'drop the client',
  'drop this client',
  'blacklist',
  // judgement about the client
  'a bad client',
  'a good client',
  'your best client',
  'your worst client',
  'a deadbeat',
  'deadbeat client',
  'a bad payer',
  'an unreliable client',
  'a red flag',
  'cause for concern',
  'not worth it',
  'not worth keeping',
  // action framing on terms / deposits
  'require a deposit',
  'ask for a deposit',
  'demand a deposit',
  'tighten your terms',
  'shorten your terms',
  'switch to net',
  'move them to net',
  'you should invoice',
  'invoice sooner',
  // recommendation framing
  'we recommend',
  'i recommend',
  'our recommendation',
  'we suggest',
  'we advise',
  'our advice',
  'the best move is',
  'the best strategy',
  'you should prioritize',
  'you should prioritise',
  'you should focus on',
  // regulated-advice claims
  'financial advice',
  'tax advice',
  'legal advice',
  'investment advice',
  'accounting advice',
  'collections advice',
];

// The mandatory disclaimer legitimately contains some of the words above.
// Allowlist the exact fragments so it cannot trip the linter.
const ALLOWLIST = [
  'not financial, tax, legal, or collections advice',
  'it does not tell you which clients to chase or how to collect',
];

function lintStrings(strings) {
  const violations = [];
  for (const raw of strings) {
    if (raw == null) continue;
    const s = String(raw).toLowerCase();
    for (const phrase of BANNED_PHRASES) {
      let idx = s.indexOf(phrase);
      while (idx !== -1) {
        const inAllow = ALLOWLIST.some((a) => {
          const aIdx = s.indexOf(a);
          return aIdx !== -1 && idx >= aIdx && idx < aIdx + a.length;
        });
        if (!inAllow) { violations.push({ phrase, text: String(raw) }); break; }
        idx = s.indexOf(phrase, idx + 1);
      }
    }
  }
  return violations;
}

function assertNoAdvice(strings) {
  const violations = lintStrings(strings);
  if (violations.length > 0) {
    const detail = violations.map((v) => `"${v.phrase}" in: ${v.text}`).join(' | ');
    const err = new Error(
      `ADVICE_LINTER_FAILED: banned advice language detected — report withheld. ${detail}`
    );
    err.code = 'ADVICE_LINTER_FAILED';
    err.violations = violations;
    throw err;
  }
  return true;
}

module.exports = { lintStrings, assertNoAdvice, BANNED_PHRASES, ALLOWLIST };
