// engine/score.js
//
// Aggregate heuristic findings into a CONCERN BAND. This is deliberately NOT a
// verdict: the bands are "LOW", "ELEVATED", and "HIGH" *heuristic concern*, and
// even "LOW" explicitly does not mean "safe". No band ever asserts certainty.

'use strict';

const WEIGHTS = { info: 0, low: 1, medium: 3, high: 6 };

// Band thresholds on the summed weight.
function bandFor(score, hasHigh) {
  if (hasHigh || score >= 6) return 'HIGH';
  if (score >= 3) return 'ELEVATED';
  return 'LOW';
}

const BAND_MEANING = {
  LOW: 'LOW heuristic concern — no strong signals were found in the URL text. This is NOT a guarantee of safety; offline heuristics cannot see the live page, certificate, or final redirect destination.',
  ELEVATED: 'ELEVATED heuristic concern — one or more moderate signals were found. Treat the link with caution and verify the destination through an independent, trusted channel before acting.',
  HIGH: 'HIGH heuristic concern — strong deception signals were found. Do not enter credentials or download anything from this link without independent verification.',
};

function scoreFindings(findings) {
  let score = 0;
  let hasHigh = false;
  const counts = { info: 0, low: 0, medium: 0, high: 0 };
  for (const fi of findings) {
    const w = WEIGHTS[fi.severity] != null ? WEIGHTS[fi.severity] : 0;
    score += w;
    counts[fi.severity] = (counts[fi.severity] || 0) + 1;
    if (fi.severity === 'high') hasHigh = true;
  }
  const band = bandFor(score, hasHigh);
  return { score, band, counts, meaning: BAND_MEANING[band] };
}

module.exports = { scoreFindings, WEIGHTS, BAND_MEANING };
