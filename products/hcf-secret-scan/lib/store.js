// lib/store.js
//
// HCF — Secret & Key Exposure Scan — entitlement key/value store (REAL).
// Ported unchanged in design from the proven hcf-header-audit / hff-runway
// store so the checkout -> webhook -> entitlement -> gated delivery loop is
// identical across the factory.
//
// BACKENDS:
//   * @vercel/kv  — used ONLY when KV_REST_API_URL + KV_REST_API_TOKEN are set.
//     The require is lazy and guarded, so the module never crashes if the
//     package isn't installed.
//   * in-memory Map — automatic fallback with NO credentials. This is what lets
//     the code run locally and in tests without any KV / Stripe secrets.
//
// KEY CONVENTION ($5 ONE-TIME purchase, keyed by Checkout Session):
//   sess:<checkoutSessionId>  -> one paid scan unlock
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
