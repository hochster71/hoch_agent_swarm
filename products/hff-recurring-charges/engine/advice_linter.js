// engine/advice_linter.js
//
// Advice-language linter (HARD GUARDRAIL), ported from the proven
// hff-invoice-aging linter and retuned for the recurring-charge domain.
//
// Scans every rendered string. FAILS CLOSED: if any banned phrase appears, the
// engine refuses to release the report. This product shows which charges repeat
// and what they cost per year. It never tells the user to cancel, keep, dispute,
// switch, or negotiate anything.
'use strict';

const BANNED_PHRASES = [
  'you should cancel',
  'you should keep',
  'you should switch',
  'you should downgrade',
  'you should negotiate',
  'you should dispute',
  'you should stop paying',
  'cancel this subscription',
  'cancel these subscriptions',
  'we suggest cancelling',
  'we suggest canceling',
  'worth cancelling',
  'worth canceling',
  'not worth the money',
  'a waste of money',
  'you are overpaying',
  'you can save',
  'save money by',
  'we recommend',
  'i recommend',
  'our recommendation',
  'we advise',
  'our advice',
  'the best move is',
  'the best strategy',
  'you ought to',
  'you should call your bank',
  'dispute this charge',
  'financial advice',
  'tax advice',
  'legal advice',
];

// The mandatory disclaimer legitimately contains advice words. Allowlist the
// exact fragments so the banner cannot trip its own linter.
const ALLOWLIST = [
  'not financial, tax, or legal advice',
  'it does not tell you what to keep, cancel, or dispute',
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
