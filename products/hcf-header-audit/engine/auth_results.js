// engine/auth_results.js
//
// Parse Authentication-Results / ARC-Authentication-Results / Received-SPF.
//
// CRITICAL FRAMING (this is a guardrail, not a stylistic choice): these headers
// are ASSERTIONS MADE BY A SERVER IN PLAIN TEXT. Anyone who can write headers can
// write a passing Authentication-Results line. Only the header stamped by YOUR OWN
// receiving mail system means anything, and this tool cannot know which server
// that is. Every consumer of this module must present results as "reported", and
// the report says so explicitly.
'use strict';

const { normalizeHost, registrableDomain } = require('./addresses');

const METHODS = ['spf', 'dkim', 'dmarc', 'arc', 'iprev', 'auth', 'bimi'];

// "mx.example.com; spf=pass smtp.mailfrom=a.com; dkim=fail header.d=b.com"
function parseAuthResultsValue(value) {
  const v = String(value || '');
  const semi = v.indexOf(';');
  const authservId = normalizeHost((semi === -1 ? v : v.slice(0, semi)).split(/\s+/)[0] || '');
  const rest = semi === -1 ? '' : v.slice(semi + 1);

  const results = [];
  const rx = new RegExp('\\b(' + METHODS.join('|') + ')\\s*=\\s*([A-Za-z]+)', 'g');
  let m;
  while ((m = rx.exec(rest)) !== null) {
    const method = m[1].toLowerCase();
    const outcome = m[2].toLowerCase();
    // Capture the property fragment that follows, up to the next method= or ';'
    const tail = rest.slice(m.index + m[0].length);
    const stop = tail.search(new RegExp('(;|\\b(' + METHODS.join('|') + ')\\s*=)'));
    const props = (stop === -1 ? tail : tail.slice(0, stop)).trim();

    const entry = { method, result: outcome, props };
    const mailfrom = /smtp\.mailfrom\s*=\s*([^\s;()]+)/i.exec(props);
    if (mailfrom) entry.smtpMailfrom = normalizeHost(mailfrom[1].replace(/^.*@/, ''));
    const headerD = /header\.d\s*=\s*([^\s;()]+)/i.exec(props);
    if (headerD) entry.headerD = normalizeHost(headerD[1]);
    const headerFrom = /header\.from\s*=\s*([^\s;()]+)/i.exec(props);
    if (headerFrom) entry.headerFrom = normalizeHost(headerFrom[1].replace(/^.*@/, ''));
    results.push(entry);
  }

  return { authservId, results, raw: v };
}

// headers: parsed header objects, in document order.
// Returns a normalized summary of every authentication assertion found.
function collectAuthResults(headers) {
  const blocks = [];
  for (const h of headers) {
    if (h.nameLower === 'authentication-results' || h.nameLower === 'arc-authentication-results') {
      const parsed = parseAuthResultsValue(h.value);
      parsed.headerName = h.name;
      parsed.arc = h.nameLower.startsWith('arc-');
      parsed.line = h.line;
      blocks.push(parsed);
    }
  }

  // Legacy/simple Received-SPF: "Pass (mailfrom) identity=mailfrom; ..."
  const receivedSpf = [];
  for (const h of headers) {
    if (h.nameLower === 'received-spf') {
      const outcome = (/^\s*([A-Za-z]+)/.exec(h.value) || [null, ''])[1].toLowerCase();
      receivedSpf.push({ result: outcome, raw: h.value, line: h.line });
    }
  }

  // The FIRST non-ARC Authentication-Results header is the one added last by
  // the receiving side, and is the closest thing to authoritative available.
  const nearest = blocks.filter((b) => !b.arc)[0] || null;

  const byMethod = {};
  if (nearest) {
    for (const r of nearest.results) {
      if (!byMethod[r.method]) byMethod[r.method] = r;
    }
  }
  if (!byMethod.spf && receivedSpf.length) {
    byMethod.spf = { method: 'spf', result: receivedSpf[0].result, props: '', fromReceivedSpf: true };
  }

  const authservIds = Array.from(new Set(blocks.filter((b) => !b.arc).map((b) => b.authservId).filter(Boolean)));

  return {
    blocks,
    receivedSpf,
    nearest,
    byMethod,
    authservIds,
    present: blocks.length > 0 || receivedSpf.length > 0,
  };
}

// Does the DKIM signing domain align with the From domain (relaxed alignment,
// i.e. same registrable domain)? Returns null when unknown.
function dkimAlignment(byMethod, fromDomain) {
  const dkim = byMethod && byMethod.dkim;
  if (!dkim || !dkim.headerD || !fromDomain) return null;
  const a = registrableDomain(dkim.headerD);
  const b = registrableDomain(fromDomain);
  if (!a || !b) return null;
  return { signingDomain: dkim.headerD, fromDomain, aligned: a === b, result: dkim.result };
}

module.exports = { collectAuthResults, parseAuthResultsValue, dkimAlignment, METHODS };
