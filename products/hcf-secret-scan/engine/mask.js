// engine/mask.js
//
// Masking guardrail: the report NEVER carries a matched value verbatim.
// A value longer than 6 chars keeps its first 4 and last 2 characters so the
// owner can recognise it; everything between becomes bullets (capped at 12).
// A value of 6 chars or fewer is fully masked.
'use strict';

function mask(secret) {
  const s = String(secret == null ? '' : secret);
  if (s.length === 0) return '';
  if (s.length <= 6) return '•'.repeat(s.length);
  const middle = Math.min(s.length - 6, 12);
  return s.slice(0, 4) + '•'.repeat(middle) + s.slice(-2);
}

module.exports = { mask };
