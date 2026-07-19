// engine/score.js
//
// Turn findings into a bounded "attention" score and a band. The band describes
// HOW MUCH OF THE HEADER TEXT WARRANTS A SECOND LOOK — it is explicitly not a
// safety rating, and the wording never tells the reader what to do.
'use strict';

const WEIGHTS = { info: 0, low: 4, medium: 12, high: 25 };

const MEANINGS = {
  LOW: 'Few or no heuristic signals matched in this header text. That is not a statement that the message is safe — this tool cannot see the body, the links, the attachments, or whether the headers themselves were forged.',
  MODERATE: 'Several heuristic signals matched. Each one listed below also has ordinary, benign explanations (forwarding, mailing lists, and mail vendors all produce them), so the list is a starting point for your own verification rather than a conclusion.',
  ELEVATED: 'Many heuristic signals matched, including ones that commonly accompany impersonation. Benign explanations still exist for each individual signal. Confirm anything consequential through a channel you already trust, independent of this message.',
};

function scoreFindings(findings) {
  const list = Array.isArray(findings) ? findings : [];
  const counts = { info: 0, low: 0, medium: 0, high: 0 };
  let raw = 0;
  for (const fi of list) {
    const sev = WEIGHTS[fi.severity] === undefined ? 'low' : fi.severity;
    counts[sev] += 1;
    raw += WEIGHTS[sev];
  }
  const score = Math.max(0, Math.min(100, raw));
  const band = score >= 45 ? 'ELEVATED' : score >= 16 ? 'MODERATE' : 'LOW';
  return { score, band, meaning: MEANINGS[band], counts };
}

module.exports = { scoreFindings, WEIGHTS, MEANINGS };
