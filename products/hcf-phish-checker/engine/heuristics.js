// engine/heuristics.js
//
// OFFLINE heuristic checks for a single URL. No network calls are ever made.
// Each check returns a Finding: { id, title, severity, detail }.
//
// severity ∈ { info, low, medium, high }. Weights feed the aggregate concern
// band in engine/score.js. NOTHING here asserts certainty — every finding is a
// heuristic signal, and the report always carries the mandatory disclaimer.

'use strict';

const { isIpv4, isIpv6, domainParts } = require('./url_parse');
const { analyzeHost } = require('./homoglyph');

// Registrable domains that are frequently impersonated. If a host CONTAINS one
// of these brand tokens as a label but its registrable domain is NOT the brand's
// own, that's a strong lookalike signal (e.g. "paypal.account-verify.com").
const BRAND_TOKENS = [
  'paypal', 'apple', 'icloud', 'microsoft', 'office365', 'outlook', 'google',
  'gmail', 'amazon', 'netflix', 'facebook', 'instagram', 'whatsapp', 'coinbase',
  'binance', 'metamask', 'chase', 'wellsfargo', 'bankofamerica', 'usbank',
  'citibank', 'dhl', 'fedex', 'ups', 'usps', 'irs', 'linkedin', 'dropbox',
  'docusign', 'steam', 'roblox', 'venmo', 'zelle', 'stripe',
];

// Official registrable domains for the brands above (best-effort allow-list).
const BRAND_OFFICIAL = new Set([
  'paypal.com', 'apple.com', 'icloud.com', 'microsoft.com', 'office365.com',
  'outlook.com', 'live.com', 'google.com', 'gmail.com', 'amazon.com',
  'netflix.com', 'facebook.com', 'instagram.com', 'whatsapp.com', 'coinbase.com',
  'binance.com', 'metamask.io', 'chase.com', 'wellsfargo.com', 'bankofamerica.com',
  'usbank.com', 'citibank.com', 'dhl.com', 'fedex.com', 'ups.com', 'usps.com',
  'irs.gov', 'linkedin.com', 'dropbox.com', 'docusign.com', 'steampowered.com',
  'roblox.com', 'venmo.com', 'zellepay.com', 'stripe.com',
]);

// TLDs disproportionately abused for phishing / malware (heuristic, not a verdict).
const ABUSED_TLDS = new Set([
  'zip', 'mov', 'xyz', 'top', 'tk', 'ml', 'ga', 'cf', 'gq', 'country', 'kim',
  'work', 'click', 'link', 'rest', 'fit', 'loan', 'download', 'review', 'racing',
  'stream', 'gdn', 'men', 'date', 'faith', 'science', 'party', 'cricket',
]);

// Well-known URL shorteners. Offline we CANNOT follow them, so we flag that the
// true destination is unresolved rather than pretending it's fine.
const SHORTENERS = new Set([
  'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly',
  'rebrand.ly', 'cutt.ly', 'rb.gy', 'shorturl.at', 'tiny.cc', 'bl.ink',
  't.ly', 'lnkd.in', 'trib.al', 'v.gd', 's.id',
]);

// Query keys commonly used to carry an embedded redirect / open-redirect target.
const REDIRECT_PARAMS = ['url', 'redirect', 'redirect_uri', 'redirecturl', 'next',
  'target', 'dest', 'destination', 'continue', 'returnurl', 'return', 'goto', 'r', 'u'];

const RISKY_PATH_EXT = /\.(exe|scr|msi|bat|cmd|apk|dmg|jar|js|vbs|ps1|zip|rar|7z|iso|img)(\?|#|$)/i;

function f(id, title, severity, detail) {
  return { id, title, severity, detail };
}

// Run every heuristic against a parsed URL. `parsed` is { url, addedScheme }.
function runChecks(parsed) {
  const { url, addedScheme } = parsed;
  const findings = [];
  const host = url.hostname;
  const scheme = url.protocol.replace(':', '').toLowerCase();
  const parts = domainParts(host);

  // --- Scheme / TLS surface ---
  if (scheme === 'javascript' || scheme === 'data' || scheme === 'file') {
    findings.push(f('dangerous_scheme', `Non-web scheme "${scheme}:"`, 'high',
      `The link uses the "${scheme}:" scheme, which can execute code or open local content rather than a normal web page.`));
  } else if (scheme === 'http') {
    findings.push(f('no_tls', 'No TLS (http://, not https://)', 'medium',
      'The link is plain http, so traffic is not encrypted in transit. Legitimate sensitive sites use https. (TLS surface is inspected from the URL only — no live certificate was fetched.)'));
  } else if (scheme === 'https') {
    findings.push(f('tls_present', 'Uses https:// (URL-level only)', 'info',
      'The URL declares https. NOTE: offline, we cannot validate the live certificate — only that the scheme is https.'));
  }
  if (addedScheme) {
    findings.push(f('no_scheme_supplied', 'No scheme in original input', 'info',
      'The input had no http/https prefix; it was assumed to be http for analysis.'));
  }

  // --- Host is a raw IP address ---
  if (isIpv4(host) || isIpv6(host)) {
    findings.push(f('ip_host', 'Host is a raw IP address', 'high',
      `The link points at a raw IP (${host}) instead of a domain name. Legitimate consumer services almost always use named domains; raw IPs are common in phishing and malware.`));
  }

  // --- Credentials / userinfo in URL ---
  if (url.username || url.password || /@/.test(url.href.split('#')[0].replace(/^[a-z]+:\/\//i, '').split('/')[0])) {
    findings.push(f('userinfo_in_url', 'Embedded credentials / "@" before host', 'high',
      'The URL contains an "@" in the authority section. Everything before "@" is ignored by the browser, a classic trick to make "paypal.com@evil.example" look legitimate.'));
  }

  // --- Punycode / homoglyph ---
  // Analyze the RAW host (pre-IDNA) when available, so Cyrillic/Greek look-alikes
  // aren't hidden behind the URL parser's punycode normalization.
  const hg = analyzeHost(parsed.rawHost || host);
  if (parsed.rawHost && parsed.rawHost !== host) {
    // The parser encoded the host — capture the punycode form too.
    const hgAscii = analyzeHost(host);
    hg.punycode = hg.punycode || hgAscii.punycode;
    hg.punycodeLabels = hg.punycodeLabels.concat(hgAscii.punycodeLabels.filter((l) => !hg.punycodeLabels.includes(l)));
  }
  if (hg.punycode) {
    findings.push(f('punycode_host', 'Punycode label(s) present (xn--)', 'medium',
      `Host contains internationalized (punycode) label(s): ${hg.punycodeLabels.join(', ')}. These can render as letters that imitate a well-known brand (homograph attack).`));
  }
  if (hg.mixedScript || hg.confusables.length) {
    findings.push(f('homoglyph_mixed_script', 'Mixed-script / look-alike characters', 'high',
      `Host mixes character scripts (${hg.scripts.join(', ')})` +
      (hg.confusables.length ? `; look-alike characters: ${hg.confusables.map((c) => `"${c.char}"~"${c.looksLike}"`).join(', ')}` : '') +
      '. This is a hallmark of domain-spoofing.'));
  }

  // --- Brand lookalike ---
  const hostLc = host.toLowerCase();
  for (const brand of BRAND_TOKENS) {
    const asLabel = new RegExp(`(^|[.\-])${brand}([.\-]|$)`);
    if (asLabel.test(hostLc) && !BRAND_OFFICIAL.has(parts.registrable)) {
      findings.push(f('brand_lookalike', `Impersonates brand token "${brand}"`, 'high',
        `Host references "${brand}" but its registrable domain is "${parts.registrable}", not an official ${brand} domain. Common in credential-phishing lures.`));
      break;
    }
  }

  // --- Suspicious TLD ---
  if (ABUSED_TLDS.has(parts.tld)) {
    findings.push(f('suspicious_tld', `Frequently-abused TLD ".${parts.tld}"`, 'low',
      `The ".${parts.tld}" TLD is disproportionately used for phishing/malware. Not proof of anything, but a mild signal.`));
  }

  // --- Excessive subdomains ---
  if (parts.subdomainCount >= 4) {
    findings.push(f('deep_subdomains', 'Unusually deep subdomain nesting', 'medium',
      `Host has ${parts.subdomainCount} subdomain levels. Deep nesting is used to bury a lookalike brand token far from the real registrable domain.`));
  }

  // --- Known shortener (destination unresolved offline) ---
  if (SHORTENERS.has(parts.registrable)) {
    findings.push(f('shortener', 'URL shortener (true destination unknown)', 'medium',
      `"${parts.registrable}" is a link shortener. This tool is OFFLINE and does not follow redirects, so the final destination is UNRESOLVED. Treat with caution until you can see where it actually leads.`));
  }

  // --- Non-standard port ---
  if (url.port && url.port !== '80' && url.port !== '443') {
    findings.push(f('nonstandard_port', `Non-standard port :${url.port}`, 'low',
      `The link targets port ${url.port}. Consumer web services use 80/443; unusual ports are a mild oddity.`));
  }

  // --- Heavy percent-encoding ---
  const pct = (url.href.match(/%[0-9a-f]{2}/gi) || []).length;
  if (pct >= 6) {
    findings.push(f('heavy_encoding', 'Heavy percent-encoding', 'medium',
      `The URL contains ${pct} percent-encoded sequences, which can hide the real host/path from a casual reader.`));
  }

  // --- Risky download extension in path ---
  if (RISKY_PATH_EXT.test(url.pathname + url.search)) {
    findings.push(f('risky_extension', 'Points at an executable/archive file', 'medium',
      'The path appears to link directly to an executable or archive (e.g. .exe/.apk/.zip). Direct-download lures are a common malware vector.'));
  }

  // --- Overall length ---
  if (url.href.length >= 100) {
    findings.push(f('long_url', 'Very long URL', 'low',
      `The URL is ${url.href.length} characters long. Excessive length is sometimes used to push the real destination out of view.`));
  }

  // --- Many hyphens / digits in registrable domain ---
  const hyphens = (parts.registrable.match(/-/g) || []).length;
  const digits = (parts.registrable.match(/\d/g) || []).length;
  if (hyphens >= 3 || digits >= 5) {
    findings.push(f('noisy_domain', 'Noisy domain (many hyphens/digits)', 'low',
      `Registrable domain "${parts.registrable}" has ${hyphens} hyphen(s) and ${digits} digit(s); auto-generated phishing domains often look like this.`));
  }

  return findings;
}

// Extract a STATIC redirect chain from embedded redirect params (no network).
// Returns an array of URL strings, deepest-first is NOT guaranteed; order is
// [original, ...embedded targets discovered by decoding query params].
function staticRedirectChain(parsed, depth) {
  const chain = [];
  const seen = new Set();
  const maxDepth = depth == null ? 5 : depth;

  function walk(u, d) {
    if (d > maxDepth) return;
    let url;
    try { url = new URL(u); } catch (e) { return; }
    const key = url.href;
    if (seen.has(key)) return;
    seen.add(key);
    chain.push(url.href);
    for (const [k, v] of url.searchParams.entries()) {
      if (!v) continue;
      const kl = k.toLowerCase();
      if (REDIRECT_PARAMS.includes(kl)) {
        // The value may itself be percent-encoded; searchParams already decoded once.
        const cand = v.trim();
        if (/^https?:\/\//i.test(cand) || /^https?%3a/i.test(cand)) {
          try { walk(decodeURIComponent(cand), d + 1); }
          catch (e) { walk(cand, d + 1); }
        }
      }
    }
  }
  walk(parsed.url.href, 0);
  return chain;
}

module.exports = {
  runChecks,
  staticRedirectChain,
  BRAND_TOKENS,
  BRAND_OFFICIAL,
  ABUSED_TLDS,
  SHORTENERS,
  REDIRECT_PARAMS,
};
