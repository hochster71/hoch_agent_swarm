// engine/addresses.js
//
// Address-list and domain handling for the header audit (offline, deterministic).
//
// parseAddressList("Ops Team <ops@a.com>, b@c.co.uk")
//   -> [{ display, address, localPart, domain, registrable, valid }]
//
// Registrable-domain reduction uses an APPROXIMATE multi-label suffix set (see
// constants.js). Every place a registrable domain drives a finding, the report
// text names it as an approximation.
'use strict';

const { MULTI_LABEL_SUFFIXES } = require('./constants');

// Split a comma-separated address list without splitting inside quotes or angle
// brackets or parenthesised comments.
function splitAddressList(value) {
  const out = [];
  let buf = '';
  let inQuote = false;
  let angle = 0;
  let paren = 0;
  for (let i = 0; i < value.length; i += 1) {
    const c = value[i];
    if (c === '"' && value[i - 1] !== '\\') { inQuote = !inQuote; buf += c; continue; }
    if (!inQuote) {
      if (c === '<') angle += 1;
      else if (c === '>') angle = Math.max(0, angle - 1);
      else if (c === '(') paren += 1;
      else if (c === ')') paren = Math.max(0, paren - 1);
      if (c === ',' && angle === 0 && paren === 0) { out.push(buf); buf = ''; continue; }
    }
    buf += c;
  }
  if (buf.trim() !== '') out.push(buf);
  return out.map((s) => s.trim()).filter((s) => s !== '');
}

function stripComments(s) {
  return s.replace(/\((?:[^()\\]|\\.)*\)/g, ' ').trim();
}

function normalizeHost(host) {
  return String(host || '')
    .trim()
    .replace(/^\[|\]$/g, '')
    .replace(/\.$/, '')
    .toLowerCase();
}

// Reduce a hostname to its approximate registrable domain (eTLD+1).
function registrableDomain(host) {
  const h = normalizeHost(host);
  if (!h || h.indexOf('.') === -1) return h;
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(h)) return h; // bare IPv4 — not a domain
  const parts = h.split('.');
  if (parts.length <= 2) return h;
  const lastTwo = parts.slice(-2).join('.');
  if (MULTI_LABEL_SUFFIXES.has(lastTwo) && parts.length >= 3) {
    return parts.slice(-3).join('.');
  }
  return lastTwo;
}

// Locate the angle-bracketed address that is NOT inside a quoted string.
// This matters: a display name may itself be a quoted string CONTAINING angle
// brackets, e.g.
//     "PayPal Billing <service@paypal.com>" <billing@lookalike.example>
// A naive first-match regex would return the decoy inside the quotes and report
// the wrong sending domain — the exact inversion this product exists to catch.
// We therefore take the LAST unquoted <...> pair.
function findAngleAddress(s) {
  let inQuote = false;
  let start = -1;
  let best = null;
  for (let i = 0; i < s.length; i += 1) {
    const c = s[i];
    if (c === '"' && s[i - 1] !== '\\') { inQuote = !inQuote; continue; }
    if (inQuote) continue;
    if (c === '<') start = i;
    else if (c === '>' && start !== -1) { best = { start, end: i, value: s.slice(start + 1, i) }; start = -1; }
  }
  return best;
}

function parseOneAddress(entry) {
  const original = entry.trim();
  let display = '';
  let address = '';

  const angle = findAngleAddress(original);
  if (angle) {
    address = angle.value.trim();
    display = (original.slice(0, angle.start) + ' ' + original.slice(angle.end + 1)).trim();
  } else {
    address = stripComments(original).trim();
    const comment = /\((?:[^()\\]|\\.)*\)/.exec(original);
    if (comment) display = comment[0].replace(/^\(|\)$/g, '').trim();
  }

  // Unquote and unescape a quoted display name.
  if (/^".*"$/.test(display)) {
    display = display.slice(1, -1).replace(/\\(.)/g, '$1');
  }

  address = address.replace(/^mailto:/i, '').trim();

  const at = address.lastIndexOf('@');
  const valid = at > 0 && at < address.length - 1 && !/\s/.test(address);
  const localPart = valid ? address.slice(0, at) : '';
  const domain = valid ? normalizeHost(address.slice(at + 1)) : '';

  return {
    raw: original,
    display,
    address: valid ? (localPart + '@' + domain) : address,
    localPart,
    domain,
    registrable: valid ? registrableDomain(domain) : '',
    valid,
  };
}

function parseAddressList(value) {
  if (!value || typeof value !== 'string' || value.trim() === '') return [];
  return splitAddressList(value).map(parseOneAddress);
}

// The single most relevant address in a header value (the first one).
function firstAddress(value) {
  const list = parseAddressList(value);
  return list.length ? list[0] : null;
}

module.exports = {
  parseAddressList,
  firstAddress,
  registrableDomain,
  normalizeHost,
  splitAddressList,
};
