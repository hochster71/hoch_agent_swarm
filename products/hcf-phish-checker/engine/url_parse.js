// engine/url_parse.js
//
// OFFLINE URL parsing helpers. No network. Turns raw user input into a normalized
// URL and its component parts, tolerating missing schemes and common paste noise.

'use strict';

// A minimal public-suffix-ish helper. This is NOT a full PSL; it is a heuristic
// used only to derive a "registrable domain" guess for lookalike checks. Honest
// limitation: multi-label ccTLDs (e.g. co.uk) are approximated, not authoritative.
const TWO_LABEL_SUFFIXES = new Set([
  'co.uk', 'org.uk', 'gov.uk', 'ac.uk', 'co.jp', 'co.kr', 'com.au', 'net.au',
  'org.au', 'com.br', 'com.cn', 'com.mx', 'co.in', 'co.nz', 'co.za', 'com.tr',
]);

function stripNoise(input) {
  let s = String(input == null ? '' : input).trim();
  // Strip surrounding angle brackets / quotes people paste from emails.
  s = s.replace(/^[<"'\s]+/, '').replace(/[>"'\s]+$/, '');
  // Defang common in "hxxp://" and "[.]" obfuscation used in threat intel.
  s = s.replace(/^h[xX]{2}p(s?):\/\//i, 'http$1://');
  s = s.replace(/\[\.\]/g, '.').replace(/\(\.\)/g, '.');
  s = s.replace(/\[:\]/g, ':');
  return s;
}

// Parse into a WHATWG URL, adding a default http:// scheme if none is present so
// bare hostnames ("paypal.com/login") still parse. Returns { url, addedScheme }.
function normalize(input) {
  const raw = stripNoise(input);
  if (raw === '') {
    const e = new Error('empty input');
    e.code = 'EMPTY_INPUT';
    throw e;
  }
  let addedScheme = false;
  let candidate = raw;
  if (!/^[a-z][a-z0-9+.-]*:/i.test(candidate)) {
    candidate = 'http://' + candidate;
    addedScheme = true;
  }
  let url;
  try {
    url = new URL(candidate);
  } catch (e) {
    const err = new Error('could not parse as a URL: ' + raw);
    err.code = 'UNPARSEABLE_URL';
    throw err;
  }
  // The WHATWG URL parser IDNA-encodes non-ASCII hosts to punycode, hiding the
  // original glyphs. Preserve the RAW host substring so homoglyph analysis can
  // inspect the actual characters the user would see.
  const rawHost = extractRawHost(candidate);
  return { url, addedScheme, raw, rawHost };
}

// Pull the host portion out of a scheme-bearing string WITHOUT WHATWG's IDNA
// normalization, so the original (possibly non-ASCII) characters are retained.
function extractRawHost(candidate) {
  let s = String(candidate).replace(/^[a-z][a-z0-9+.-]*:\/\//i, '');
  s = s.split('/')[0].split('?')[0].split('#')[0];
  // Drop userinfo.
  const at = s.lastIndexOf('@');
  if (at !== -1) s = s.slice(at + 1);
  // Drop port.
  if (s.startsWith('[')) {
    // IPv6 literal.
    const end = s.indexOf(']');
    return end !== -1 ? s.slice(0, end + 1) : s;
  }
  s = s.split(':')[0];
  return s;
}

function isIpv4(host) {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(host);
  if (!m) return false;
  return m.slice(1).every((o) => Number(o) >= 0 && Number(o) <= 255);
}

function isIpv6(host) {
  // WHATWG URL wraps IPv6 hosts in brackets.
  return /^\[[0-9a-f:]+\]$/i.test(host);
}

// Split a host into labels and derive a best-effort registrable domain.
function domainParts(host) {
  const labels = host.split('.').filter(Boolean);
  let registrable = host;
  if (labels.length >= 2) {
    const lastTwo = labels.slice(-2).join('.');
    if (TWO_LABEL_SUFFIXES.has(lastTwo) && labels.length >= 3) {
      registrable = labels.slice(-3).join('.');
    } else {
      registrable = lastTwo;
    }
  }
  const tld = labels.length ? labels[labels.length - 1] : '';
  return { labels, registrable, tld, subdomainCount: Math.max(0, labels.length - 2) };
}

module.exports = { stripNoise, normalize, isIpv4, isIpv6, domainParts, TWO_LABEL_SUFFIXES };
