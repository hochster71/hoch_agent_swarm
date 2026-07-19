// engine/report_linter.js
//
// GUARDRAIL ENFORCEMENT (fail-closed).
//
// The product's hard promise is: heuristic only, NEVER a claim of certainty, and
// NEVER a real-world security decision instruction. This linter runs over the
// rendered report BEFORE it is returned, and throws if either:
//   * the mandatory disclaimer is missing, or
//   * a certainty over-claim leaked into the text, or
//   * a directive ("you should delete this", "block this sender") leaked in.
//
// A report that fails the linter must NOT be delivered. Paying does not buy past
// this gate — the paid endpoint surfaces the failure as 422 with no report body.
'use strict';

const FORBIDDEN = [
  // Certainty over-claims, in either direction.
  /\bguaranteed?\s+(safe|legitimate|malicious)\b/i,
  /\b100%\s*(safe|secure|certain|malicious|phishing|legitimate)\b/i,
  /\bverified\s+(safe|legitimate|authentic)\b/i,
  /\bdefinitely\s+(safe|legitimate|malicious|phishing|a\s+scam)\b/i,
  /\bcertainly\s+(safe|legitimate|malicious)\b/i,
  /\bconfirmed\s+(safe|legitimate|malicious|phishing)\b/i,
  /\bthis\s+(email|message|sender)\s+is\s+(safe|legitimate|malicious|phishing|a\s+scam)\b/i,
  /\bproves?\s+(the\s+)?(sender|message)\s+is\b/i,
  // Security decision instructions.
  /\byou\s+should\s+(delete|block|report|quarantine|ignore|trust)\b/i,
  /\b(delete|block|quarantine)\s+(this|the)\s+(email|message|sender)\b/i,
  /\bsafe\s+to\s+(click|open|reply|trust)\b/i,
  /\bdo\s+not\s+worry\b/i,
];

class ReportLintError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ReportLintError';
    this.code = 'REPORT_LINTER_FAILED';
  }
}

function lintReport(report, text) {
  const problems = [];
  if (!report || typeof report.disclaimer !== 'string' || report.disclaimer.trim() === '') {
    problems.push('mandatory disclaimer is missing');
  }
  const hay = String(text || '');
  for (const rx of FORBIDDEN) {
    if (rx.test(hay)) problems.push(`forbidden phrase present: ${rx}`);
  }
  if (problems.length) {
    throw new ReportLintError('report guardrail linter failed:\n  - ' + problems.join('\n  - '));
  }
  return true;
}

module.exports = { lintReport, ReportLintError, FORBIDDEN };
