// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL). Scans every rendered string for advice phrases.
// Fails CLOSED: if any banned phrase is found, the engine refuses to release the packet.
// This is organizational tooling — it shows math, it never tells the user what to do.

'use strict';

// Banned phrases (lowercased substrings). Kept conservative and specific so labeled,
// factual worksheet lines ("estimated tax", "deduction") are NOT flagged.
const BANNED_PHRASES = [
  'you should invest',
  'you should buy',
  'you should sell',
  'we recommend',
  'i recommend',
  'our recommendation',
  'the best move is',
  'the best strategy',
  'best investment',
  'you ought to',
  'we advise',
  'our advice',
  'financial advice',
  'investment advice',
  'tax advice is',
  'to minimize your taxes you',
  'to reduce your taxes you',
  'you should defer',
  'you should contribute',
  'buy this stock',
  'sell your',
  'we suggest you',
  'guaranteed return',
  'you will save',
  'trust us',
];

// The approved disclaimer contains the words "not financial or tax advice" — that exact
// phrase is allowlisted so the mandatory banner does not trip the linter.
const ALLOWLIST = ['not financial or tax advice'];

function lintStrings(strings) {
  const violations = [];
  for (const raw of strings) {
    if (raw == null) continue;
    const s = String(raw).toLowerCase();
    for (const phrase of BANNED_PHRASES) {
      let idx = s.indexOf(phrase);
      while (idx !== -1) {
        // skip if this occurrence is inside an allowlisted phrase
        const inAllow = ALLOWLIST.some((a) => {
          const aIdx = s.indexOf(a);
          return aIdx !== -1 && idx >= aIdx && idx < aIdx + a.length;
        });
        if (!inAllow) {
          violations.push({ phrase, text: String(raw) });
          break;
        }
        idx = s.indexOf(phrase, idx + 1);
      }
    }
  }
  return violations;
}

// Assert clean or throw (fail-closed release gate).
function assertNoAdvice(strings) {
  const violations = lintStrings(strings);
  if (violations.length > 0) {
    const detail = violations.map((v) => `"${v.phrase}" in: ${v.text}`).join(' | ');
    const err = new Error(`ADVICE_LINTER_FAILED: banned advice language detected — packet withheld. ${detail}`);
    err.code = 'ADVICE_LINTER_FAILED';
    err.violations = violations;
    throw err;
  }
  return true;
}

module.exports = { lintStrings, assertNoAdvice, BANNED_PHRASES };
