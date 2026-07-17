// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL). Scans every rendered string for financial,
// collections, or legal advice phrases. Fails CLOSED: if any banned phrase is found, the
// engine refuses to release the report. This is organizational tooling — it shows which
// invoices are outstanding and how old they are; it never tells the user what to do.

'use strict';

// Banned phrases (lowercased substrings). Conservative and specific so factual, labeled
// summary lines ("outstanding balance", "90+ days") are NOT flagged.
const BANNED_PHRASES = [
  'you should collect',
  'you should call',
  'you should chase',
  'you should sue',
  'send to collections',
  'send this to collections',
  'turn over to collections',
  'hire a collection',
  'file a lawsuit',
  'take legal action',
  'you should charge interest',
  'charge them a late fee',
  'write this off',
  'you should write off',
  'we recommend',
  'i recommend',
  'our recommendation',
  'we advise',
  'our advice',
  'the best move is',
  'the best strategy',
  'you ought to',
  'you should factor',
  'sell this debt',
  'stop doing business with',
  'financial advice',
  'legal advice',
  'collections advice',
];

// The approved disclaimer contains "collections, or legal advice" — allowlist those exact
// fragments so the mandatory banner does not trip the linter.
const ALLOWLIST = ['collections, or legal advice', 'not financial, collections'];

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
    const err = new Error(`ADVICE_LINTER_FAILED: banned advice language detected — report withheld. ${detail}`);
    err.code = 'ADVICE_LINTER_FAILED';
    err.violations = violations;
    throw err;
  }
  return true;
}

module.exports = { lintStrings, assertNoAdvice, BANNED_PHRASES };
