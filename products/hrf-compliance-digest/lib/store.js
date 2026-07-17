// lib/store.js
//
// HRF — Compliance Change Digest — entitlement key/value store (REAL).
//
// Mirrors the PROVEN hff-runway/lib/store.js. Digest is a $12/mo subscription,
// keyed by buyer email; an active subscriber can generate digests REPEATEDLY.
//
//   email:<addr>      -> active subscription unlock
//   cust:<customerId> -> { email } map, so a cancel/lapse can revoke by email

'use strict';

let _kv = null;
let _mem = null;

function kvConfigured() {
  return !!(process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN);
}

function backend() {
  if (kvConfigured() && _kv !== false) {
    if (!_kv) {
      try {
        // eslint-disable-next-line global-require
        _kv = require('@vercel/kv').kv;
      } catch (e) {
        console.warn('[store] @vercel/kv not installed; using in-memory fallback.');
        _kv = false;
      }
    }
    if (_kv) return { type: 'kv', kv: _kv };
  }
  if (!_mem) _mem = new Map();
  return { type: 'mem', mem: _mem };
}

async function get(key) {
  const b = backend();
  if (b.type === 'kv') {
    const v = await b.kv.get(key);
    return v == null ? null : v;
  }
  return b.mem.has(key) ? b.mem.get(key) : null;
}

async function put(key, value) {
  const b = backend();
  if (b.type === 'kv') { await b.kv.set(key, value); return; }
  b.mem.set(key, value);
}

async function setPaid(key, meta) {
  const record = Object.assign({ paid: true, updatedAt: new Date().toISOString() }, meta || {});
  await put(key, record);
  return record;
}

async function setUnpaid(key) {
  const existing = (await get(key)) || {};
  const record = Object.assign({}, existing, { paid: false, updatedAt: new Date().toISOString() });
  await put(key, record);
  return record;
}

async function isPaid(key) {
  const record = await get(key);
  return !!(record && record.paid === true);
}

async function _reset() { if (_mem) _mem.clear(); }

module.exports = { get, put, setPaid, setUnpaid, isPaid, kvConfigured, _reset };
