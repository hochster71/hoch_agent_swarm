// engine/homoglyph.js
//
// OFFLINE homoglyph / punycode surface analysis. No network.
//
// Two heuristic signals:
//   1) PUNYCODE labels (xn--...) — an ASCII-Compatible Encoding of a non-ASCII
//      label. Legitimate for internationalized domains, but ALSO the classic
//      homograph-attack vector (e.g. "аpple.com" -> xn--pple-43d.com).
//   2) MIXED-SCRIPT hosts — a single label mixing Latin with Cyrillic/Greek
//      letters that LOOK like Latin (а, е, о, р, с ...). A strong lookalike
//      signal. We classify each character's Unicode script block heuristically.
//
// HONEST SCOPE: this detects *surface* confusability. It does not decode every
// punycode label to a rendered glyph, and cannot prove intent. Heuristic only.

'use strict';

// Confusable Cyrillic/Greek letters that share a glyph with a Latin letter.
const CONFUSABLE = {
  // Cyrillic
  'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c',
  'у': 'y', 'х': 'x', 'ѕ': 's', 'і': 'i', 'ј': 'j',
  'һ': 'h', 'ԁ': 'd', 'ԛ': 'q', 'ԝ': 'w',
  // Greek
  'α': 'a', 'ο': 'o', 'ρ': 'p', 'ν': 'v', 'κ': 'k',
  'Ι': 'I', 'Ο': 'O', 'Ρ': 'P', 'Β': 'B', 'Η': 'H',
};

function classifyScript(ch) {
  const c = ch.codePointAt(0);
  if (c <= 0x007f) return 'latin-ascii';
  if (c >= 0x0400 && c <= 0x04ff) return 'cyrillic';
  if (c >= 0x0370 && c <= 0x03ff) return 'greek';
  if (c >= 0x0080 && c <= 0x024f) return 'latin-ext';
  if (c >= 0x0600 && c <= 0x06ff) return 'arabic';
  if (c >= 0x4e00 && c <= 0x9fff) return 'han';
  return 'other';
}

// Returns { punycode, punycodeLabels, mixedScript, scripts, confusables }.
function analyzeHost(host) {
  const labels = String(host || '').split('.').filter(Boolean);
  const punycodeLabels = labels.filter((l) => /^xn--/i.test(l));

  const scripts = new Set();
  const confusables = [];
  for (const ch of String(host || '')) {
    if (ch === '.' || ch === '-') continue;
    const s = classifyScript(ch);
    scripts.add(s);
    if (Object.prototype.hasOwnProperty.call(CONFUSABLE, ch)) {
      confusables.push({ char: ch, looksLike: CONFUSABLE[ch], script: s });
    }
  }

  // Mixed script = more than one *letter* script present in the raw host (before
  // punycode decoding). Latin-ascii + latin-ext together is fine; latin + cyrillic
  // or latin + greek is the classic lookalike.
  const letterScripts = [...scripts].filter((s) => s !== 'other');
  const hasLatin = letterScripts.some((s) => s.startsWith('latin'));
  const hasNonLatinAlpha = letterScripts.some((s) => s === 'cyrillic' || s === 'greek' || s === 'arabic' || s === 'han');
  const mixedScript = hasLatin && hasNonLatinAlpha;

  return {
    punycode: punycodeLabels.length > 0,
    punycodeLabels,
    mixedScript,
    scripts: [...scripts],
    confusables,
  };
}

module.exports = { analyzeHost, classifyScript, CONFUSABLE };
