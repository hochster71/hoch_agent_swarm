// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL), ported from the proven
// hff-client-concentration / hff-hourly-rate linter and retuned for the
// vendor-spend domain.
//
// Scans every engine-authored string. FAILS CLOSED: if any banned phrase
// appears, the engine refuses to release the report — paid or free. This
// product describes the vendor payments recorded in the uploaded file and the
// arithmetic those payments produce. It never says a vendor is expensive or
// cheap, never calls spend wasteful, and never tells the reader what to cut,
// cancel, or renegotiate.
'use strict';

const BANNED_PHRASES = [
  // direct instruction
  'you should cancel',
  'you should cut',
  'you should drop',
  'you should switch',
  'you should renegotiate',
  'you should consolidate',
  'you should reduce',
  'you should stop paying',
  'you need to cut',
  'you must cut',
  'you ought to',
  'cancel this vendor',
  'drop this vendor',
  'switch vendors',
  'renegotiate with',
  'shop around',
  'find a cheaper',
  'consider cancelling',
  'consider canceling',
  'worth cancelling',
  'worth canceling',
  // judgement about the spend or the vendor
  'overpaying',
  'overpriced',
  'underpriced',
  'too expensive',
  'too cheap',
  'too high',
  'too low',
  'wasteful',
  'wasted spend',
  'waste of money',
  'unnecessary spend',
  'unnecessary expense',
  'excessive spend',
  'bloated',
  'a bad vendor',
  'a good vendor',
  'your best vendor',
  'your worst vendor',
  'a red flag',
  'cause for concern',
  'below market',
  'above market',
  'market rate',
  'a better deal',
  'bad value',
  'poor value',
  'not worth it',
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
  'you could save',
  'savings opportunity',
  'you are losing money',
  'cut costs',
  // regulated-advice claims
  'financial advice',
  'tax advice',
  'legal advice',
  'investment advice',
  'accounting advice',
  'deductible',
  'write off',
  'write-off',
];

// The mandatory disclaimer legitimately contains some of the words above.
// Allowlist the exact fragments so it cannot trip the linter.
const ALLOWLIST = [
  'not financial, tax, or legal advice',
  'it does not tell you which vendors to cut, keep, or renegotiate',
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
