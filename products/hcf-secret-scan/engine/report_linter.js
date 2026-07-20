// engine/report_linter.js
//
// GUARDRAIL (fail-closed): "heuristic only; never claim certainty; no
// real-world security decision advice."
//
// Runs over every string the report will show. If ANY banned pattern appears —
// a certainty over-claim, a compromise assertion, a safety assurance, or a
// security directive — the WHOLE report is withheld (throws), paid or free.
// A missing disclaimer or a finding without a benign explanation also fails.
'use strict';

const BANNED = [
  { re: /\b(definitely|certainly|guaranteed|undoubtedly|beyond doubt)\b/i, why: 'certainty over-claim' },
  { re: /\b(?:is|are|was|were|has been|have been)\s+(?:compromised|breached|leaked|stolen|hacked)\b/i, why: 'compromise asserted as fact' },
  { re: /\bthis (?:key|token|secret|credential|password) is (?:real|live|active|valid)\b/i, why: 'validity asserted as fact' },
  { re: /\byou (?:must|should|need to)\b/i, why: 'security directive' },
  { re: /\b(?:immediately|right away|as soon as possible|asap)\b/i, why: 'urgency directive' },
  { re: /\b(?:you are safe|safe to use|safe to share|safe to ignore|no risk|zero risk|nothing to worry about)\b/i, why: 'safety assurance' },
];

const REQUIRED_DISCLAIMER_MARK = 'NOT A GUARANTEE';

function lintErr(message) {
  const e = new Error('Report withheld by guardrail linter: ' + message);
  e.code = 'REPORT_LINTER_FAILED';
  return e;
}

function lintReport(report) {
  if (!report || typeof report !== 'object') throw lintErr('no report object');
  if (!report.disclaimer || !report.disclaimer.includes(REQUIRED_DISCLAIMER_MARK)) {
    throw lintErr('mandatory disclaimer missing from report.disclaimer');
  }
  if (!report.text || !report.text.includes(REQUIRED_DISCLAIMER_MARK)) {
    throw lintErr('mandatory disclaimer missing from rendered text');
  }
  const texts = [report.text, report.disclaimer, report.summary || ''];
  for (const f of report.findings || []) {
    if (!f.benign || String(f.benign).trim() === '') {
      throw lintErr('finding "' + (f.detector || '?') + '" has no benign explanation');
    }
    texts.push(String(f.explain || ''), String(f.benign || ''), String(f.label || ''));
  }
  for (const t of texts) {
    for (const b of BANNED) {
      if (b.re.test(t)) throw lintErr(b.why + ' (' + String(b.re) + ')');
    }
  }
  return true;
}

module.exports = { lintReport, BANNED, REQUIRED_DISCLAIMER_MARK };
