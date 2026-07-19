// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL), ported from the proven
// hff-invoice-aging / hff-recurring-charges linter and retuned for the client
// concentration domain.
//
// Scans every rendered string. FAILS CLOSED: if any banned phrase appears, the
// engine refuses to release the report — paid or free. This product describes
// how revenue in the uploaded file is distributed across clients. It never tells
// the reader that a distribution is good or bad, and never tells them to
// diversify, chase, drop, fire, or re-price a client.
'use strict';

const BANNED_PHRASES = [
  // direct instruction
  'you should diversify',
  'you should drop',
  'you should fire',
  'you should chase',
  'you should raise',
  'you should lower',
  'you should replace',
  'you should focus on',
  'you need to diversify',
  'you must diversify',
  'you ought to',
  'drop this client',
  'fire this client',
  'replace this client',
  'chase this client',
  'find new clients',
  'get more clients',
  'reduce your reliance',
  'diversify your',
  // judgement about the distribution
  'too dependent',
  'overly dependent',
  'dangerously concentrated',
  'unhealthy concentration',
  'healthy concentration',
  'this is risky',
  'this is dangerous',
  'this is unsafe',
  'a red flag',
  'cause for concern',
  'not worth keeping',
  'worth keeping',
  'your best client',
  'your worst client',
  'a bad client',
  'a good client',
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
];

// The mandatory disclaimer and a few factual labels legitimately contain some of
// the words above. Allowlist the exact fragments so they cannot trip the linter.
const ALLOWLIST = [
  'not financial, tax, or legal advice',
  'it does not tell you which clients to keep, chase, or drop',
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
