// engine/entropy.js
//
// Shannon entropy in bits per character over the exact string given.
// Used to separate random-looking values (likely real credentials) from
// repeated/dictionary-ish values (likely placeholders). Deterministic.
'use strict';

function shannonEntropy(s) {
  if (typeof s !== 'string' || s.length === 0) return 0;
  const freq = new Map();
  for (const ch of s) freq.set(ch, (freq.get(ch) || 0) + 1);
  let h = 0;
  for (const n of freq.values()) {
    const p = n / s.length;
    h -= p * Math.log2(p);
  }
  return h;
}

module.exports = { shannonEntropy };
