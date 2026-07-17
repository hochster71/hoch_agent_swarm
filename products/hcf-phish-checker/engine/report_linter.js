// engine/report_linter.js
//
// GUARDRAIL ENFORCEMENT (fail-closed). The product's hard promise is: heuristic
// only, NEVER a claim of certainty. This linter runs over a rendered report and
// FAILS if either:
//   * the mandatory disclaimer is missing, or
//   * any certainty phrase leaked into the human-readable text
//     ("guaranteed safe", "definitely malicious", "100% safe", "verified safe"...)
//
// A report that fails the linter must NOT be delivered — it throws, exactly like
// hff-runway's advice-linter, so a broken guardrail can never ship as success.

'use strict';

// Phrases that would over-claim certainty in either direction.
const FORBIDDEN = [
  /\bguaranteed?\s+safe\b/i,
  /\b100%\s*(safe|secure|malicious|phishing)\b/i,
  /\bverified\s+safe\b/i,
  /\bdefinitely\s+(safe|malicious|phishing|a\s+scam)\b/i,
  /\bcertainly\s+(safe|malicious)\b/i,
  /\bthis\s+(link|site|url)\s+is\s+safe\b/i,
  /\bconfirmed\s+(safe|malicious|phishing)\b/i,
];

class ReportLintError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ReportLintError';
    this.code = 'REPORT_LINTER_FAILED';
  }
}

// report: the object from engine/index.js. text: its rendered human summary.
function lintReport(report, text) {
  const problems = [];
  if (!report || typeof report.disclaimer !== 'string' || report.disclaimer.trim() === '') {
    problems.push('mandatory disclaimer is missing');
  }
  const hay = String(text || '');
  for (const rx of FORBIDDEN) {
    if (rx.test(hay)) problems.push(`certainty phrase present: ${rx}`);
  }
  if (problems.length) {
    throw new ReportLintError('report guardrail linter failed:\n  - ' + problems.join('\n  - '));
  }
  return true;
}

module.exports = { lintReport, ReportLintError, FORBIDDEN };
