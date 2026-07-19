// engine/lookalike.js
//
// Lookalike-domain heuristics (offline, deterministic).
//
// Three independent signals, all reported as OBSERVATIONS, never as verdicts:
//   1. punycode / non-ASCII  — an IDN domain (xn--) or raw non-ASCII labels.
//   2. confusable folding    — after folding common visual substitutions
//                              (rn->m, 0->o, 1->l, vv->w ...), the domain
//                              collapses onto a commonly-impersonated brand.
//   3. brand-adjacent        — a brand name appears in the domain but the
//                              registrable domain is NOT the brand's.
'use strict';

const { IMPERSONATION_TARGETS } = require('./constants');
const { registrableDomain } = require('./addresses');

// Characters that are visually confusable with ASCII letters.
const CONFUSABLE_MAP = {
  '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b',
  'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', // Cyrillic
  ' і': 'i', 'ѕ': 's', 'ԁ': 'd', 'ɑ': 'a', 'ο': 'o', 'ρ': 'p', 'ν': 'v', // Greek/other
};

function foldConfusables(s) {
  let out = String(s).toLowerCase();
  out = out.replace(/[^\x00-\x7F]/g, (ch) => (Object.prototype.hasOwnProperty.call(CONFUSABLE_MAP, ch) ? CONFUSABLE_MAP[ch] : ch));
  out = out.replace(/[0134578]/g, (ch) => CONFUSABLE_MAP[ch] || ch);
  out = out.replace(/vv/g, 'w').replace(/rn/g, 'm').replace(/cl/g, 'd');
  out = out.replace(/-/g, '');
  return out;
}

function hasNonAscii(s) {
  return /[^\x00-\x7F]/.test(String(s || ''));
}

function isPunycode(host) {
  return String(host || '').toLowerCase().split('.').some((lbl) => lbl.startsWith('xn--'));
}

// Levenshtein distance, capped for cheapness.
function editDistance(a, b) {
  const s = String(a);
  const t = String(b);
  if (s === t) return 0;
  if (Math.abs(s.length - t.length) > 3) return 99;
  const prev = new Array(t.length + 1);
  const cur = new Array(t.length + 1);
  for (let j = 0; j <= t.length; j += 1) prev[j] = j;
  for (let i = 1; i <= s.length; i += 1) {
    cur[0] = i;
    for (let j = 1; j <= t.length; j += 1) {
      const cost = s[i - 1] === t[j - 1] ? 0 : 1;
      cur[j] = Math.min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost);
    }
    for (let j = 0; j <= t.length; j += 1) prev[j] = cur[j];
  }
  return prev[t.length];
}

// Returns { punycode, nonAscii, confusable: [{target, folded}], brandAdjacent: [{brand}] }
function analyzeDomain(host) {
  const h = String(host || '').toLowerCase();
  const result = { host: h, punycode: false, nonAscii: false, confusable: [], brandAdjacent: [] };
  if (!h) return result;

  result.punycode = isPunycode(h);
  result.nonAscii = hasNonAscii(h);

  const reg = registrableDomain(h);
  const regBase = reg.split('.')[0] || '';
  const folded = foldConfusables(reg);
  const foldedBase = foldConfusables(regBase);

  for (const target of IMPERSONATION_TARGETS) {
    const targetBase = target.split('.')[0];

    // Exact match on the registrable domain -> this IS the brand; no signal.
    if (reg === target) continue;

    // 1. Confusable / typo folding onto the brand.
    if (foldedBase === targetBase || (foldedBase.length > 4 && editDistance(foldedBase, targetBase) === 1)) {
      result.confusable.push({ target, folded: folded });
      continue;
    }

    // 2. Brand name appears somewhere in the hostname but the registrable
    //    domain is not the brand's (e.g. paypal.secure-login.example).
    //    Tested against the CONFUSABLE-FOLDED hostname as well, so that a
    //    substituted character inside a longer label (paypa1-billing.example
    //    -> paypalbilling.example) still surfaces.
    const foldedHost = foldConfusables(h);
    if ((h.indexOf(targetBase) !== -1 || foldedHost.indexOf(targetBase) !== -1) && regBase !== targetBase && foldedBase !== targetBase) {
      result.brandAdjacent.push({ brand: target });
    }
  }

  return result;
}

module.exports = { analyzeDomain, foldConfusables, editDistance, isPunycode, hasNonAscii };
