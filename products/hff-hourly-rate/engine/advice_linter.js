// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL), ported from the proven
// hff-invoice-aging / hff-client-concentration linter and retuned for the
// hourly-rate domain.
//
// Scans every engine-authored string. FAILS CLOSED: if any banned phrase
// appears, the engine refuses to release the report — paid or free. This
// product describes the hours and billing figures in the uploaded file and the
// arithmetic rates they produce. It never says a rate is good or bad, never
// compares it to a market, and never tells the reader what to charge or which
// clients or hours to change.
'use strict';

const BANNED_PHRASES = [
  // direct instruction
  'you should raise',
  'you should lower',
  'you should charge',
  'you should bill',
  'you should drop',
  'you should fire',
  'you should focus on',
  'you need to raise',
  'you must raise',
  'you ought to',
  'raise your rate',
  'raise your rates',
  'lower your rate',
  'lower your rates',
  'increase your rate',
  'charge more',
  'charge less',
  'bill more',
  'bill less',
  'drop this client',
  'fire this client',
  'replace this client',
  'work fewer hours',
  'work more hours',
  'track more hours',
  // judgement about the rate or the hours
  'undercharging',
  'overcharging',
  'underbilling',
  'underpaid',
  'overpaid',
  'too low',
  'too high',
  'too cheap',
  'too expensive',
  'below market',
  'above market',
  'market rate',
  'not charging enough',
  'leaving money on the table',
  'worth more',
  'you deserve',
  'a red flag',
  'cause for concern',
  'your best client',
  'your worst client',
  'a bad client',
  'a good client',
  'unprofitable client',
  'profitable client',
  // recommendation framing
  'we recommend',
  'i recommend',
  'our recommendation',
  'we suggest',
  'we advise',
  'our advice',
  'the best move is',
  'the best strategy',
  'you can save',
  'you are losing money',
  // regulated-advice claims
  'financial advice',
  'tax advice',
  'legal advice',
  'investment advice',
  'career advice',
];

// The mandatory disclaimer legitimately contains some of the words above.
// Allowlist the exact fragments so it cannot trip the linter.
const ALLOWLIST = [
  'not financial, tax, or legal advice',
  'it does not tell you what to charge',
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
