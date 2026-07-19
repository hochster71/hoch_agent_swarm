// engine/hops.js
//
// Received-chain parsing (offline, deterministic).
//
// A Received header is prepended by each relay, so headers[0] is the LAST hop
// (your server) and the final Received is the ORIGIN. We parse "from X by Y ...
// ; date", normalize to chronological order, and expose gap/ordering facts.
//
// Received headers are trivially forgeable below the first hop your own
// infrastructure added — the report frames every hop fact accordingly.
'use strict';

const { normalizeHost } = require('./addresses');

function extractIps(s) {
  const out = [];
  const v4 = /\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b/g;
  let m;
  while ((m = v4.exec(s)) !== null) {
    const parts = m[1].split('.').map(Number);
    if (parts.every((n) => n >= 0 && n <= 255)) out.push(m[1]);
  }
  const v6 = /\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b/g;
  while ((m = v6.exec(s)) !== null) out.push(m[0]);
  return Array.from(new Set(out));
}

function isPrivateIp(ip) {
  if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(ip)) return /^(::1|fc|fd)/i.test(ip);
  const p = ip.split('.').map(Number);
  if (p[0] === 10) return true;
  if (p[0] === 127) return true;
  if (p[0] === 192 && p[1] === 168) return true;
  if (p[0] === 172 && p[1] >= 16 && p[1] <= 31) return true;
  if (p[0] === 169 && p[1] === 254) return true;
  return false;
}

function parseReceived(value, index) {
  const v = String(value || '');

  // The timestamp is whatever follows the LAST semicolon.
  const semi = v.lastIndexOf(';');
  const dateText = semi === -1 ? '' : v.slice(semi + 1).trim();
  const head = semi === -1 ? v : v.slice(0, semi);

  let timestamp = null;
  if (dateText) {
    const t = Date.parse(dateText.replace(/\((?:[^()\\]|\\.)*\)/g, '').trim());
    if (!Number.isNaN(t)) timestamp = t;
  }

  const fromMatch = /\bfrom\s+([^\s;()]+)/i.exec(head);
  const byMatch = /\bby\s+([^\s;()]+)/i.exec(head);
  const withMatch = /\bwith\s+([A-Za-z0-9\/\-]+)/i.exec(head);

  const ips = extractIps(head);

  return {
    index,
    from: fromMatch ? normalizeHost(fromMatch[1]) : null,
    by: byMatch ? normalizeHost(byMatch[1]) : null,
    with: withMatch ? withMatch[1].toUpperCase() : null,
    ips,
    publicIps: ips.filter((ip) => !isPrivateIp(ip)),
    dateText,
    timestamp,
    tls: /\b(TLS|STARTTLS|ESMTPS|ESMTPSA)\b/i.test(head),
    raw: v,
  };
}

// receivedValues: Received header values in document order (newest first).
function buildChain(receivedValues) {
  const hops = receivedValues.map((v, i) => parseReceived(v, i));

  // Chronological order = reverse of document order (origin first).
  const chronological = hops.slice().reverse().map((h, i) => Object.assign({}, h, { position: i + 1 }));

  const timed = chronological.filter((h) => h.timestamp !== null);
  let outOfOrder = 0;
  let maxGapMs = 0;
  let maxGapBetween = null;
  for (let i = 1; i < timed.length; i += 1) {
    const delta = timed[i].timestamp - timed[i - 1].timestamp;
    if (delta < -60 * 1000) outOfOrder += 1; // >1min backwards
    if (delta > maxGapMs) {
      maxGapMs = delta;
      maxGapBetween = [timed[i - 1].position, timed[i].position];
    }
  }

  const origin = chronological.length ? chronological[0] : null;
  const totalTransitMs = timed.length >= 2 ? (timed[timed.length - 1].timestamp - timed[0].timestamp) : null;

  return {
    count: hops.length,
    hops: chronological,
    origin,
    timedCount: timed.length,
    untimedCount: chronological.length - timed.length,
    outOfOrder,
    maxGapMs,
    maxGapBetween,
    totalTransitMs,
    anyTls: chronological.some((h) => h.tls),
  };
}

module.exports = { buildChain, parseReceived, extractIps, isPrivateIp };
