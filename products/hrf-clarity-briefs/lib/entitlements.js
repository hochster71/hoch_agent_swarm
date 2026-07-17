// lib/entitlements.js
//
// HRF — Clarity Briefs — entitlement store bridge (REAL, zero-dependency).
//
// This module writes the SAME on-disk JSON format that the Python engine reads
// in `engine/entitlement.py` (class EntitlementStore). That module resolves its
// path from `HRF_ENTITLEMENTS_PATH` (default "entitlements.json") and expects:
//
//     { "<token>": { "tier": "brief",   "remaining": 1 },       // one-off credit
//       "<token>": { "tier": "monthly", "remaining": null } }   // null = unlimited
//
// So when `api/webhook.js` grants an entitlement here, `require_entitlement()`
// on the Python side accepts the same token with no translation layer.
//
// DURABILITY NOTE (honest): this is a file-backed store, matching the engine's
// zero-dependency design. It is durable on any host with a persistent writable
// filesystem (a local box, a container with a mounted volume). On Vercel's
// ephemeral serverless filesystem, writes do NOT persist across invocations —
// the same limitation the sibling HSF store documents. To make the webhook and
// the generate route share state in that environment, point HRF_ENTITLEMENTS_PATH
// at a mounted/persistent volume or swap `loadAll/saveAll` for a KV backend.
// The format contract above is what matters and does not change.

'use strict';

const fs = require('fs');

// tier -> initial `remaining` value the engine gate understands.
//   brief   -> 1 one-off credit (consumed on first generation)
//   monthly -> null = unlimited within the subscription period
const TIER_REMAINING = { brief: 1, monthly: null };

function storePath() {
  return process.env.HRF_ENTITLEMENTS_PATH || 'entitlements.json';
}

function loadAll(p) {
  const path = p || storePath();
  try {
    return JSON.parse(fs.readFileSync(path, 'utf8')) || {};
  } catch (e) {
    return {}; // absent or unreadable -> empty store (fail-closed on reads)
  }
}

function saveAll(data, p) {
  const path = p || storePath();
  fs.writeFileSync(path, JSON.stringify(data, null, 2));
}

// grant(token, tier, meta) -> write an entitlement the Python gate will accept.
// Returns the written record. Extra meta keys (email, sessionId, grantedAt) are
// preserved for auditability; the engine ignores them and only reads `remaining`.
function grant(token, tier, meta) {
  if (!token) throw new Error('grant: token required');
  const remaining = Object.prototype.hasOwnProperty.call(TIER_REMAINING, tier)
    ? TIER_REMAINING[tier]
    : 1; // unknown tier -> conservative single credit
  const data = loadAll();
  data[token] = Object.assign(
    { tier: tier || 'brief', remaining, grantedAt: new Date().toISOString() },
    meta || {}
  );
  saveAll(data);
  return data[token];
}

// revoke(token) -> zero out remaining credits (subscription cancel/lapse).
// Kept as a record with remaining:0 so is_entitled() denies it. No-op if absent.
function revoke(token) {
  if (!token) return null;
  const data = loadAll();
  if (!data[token]) return null;
  data[token].remaining = 0;
  data[token].revokedAt = new Date().toISOString();
  saveAll(data);
  return data[token];
}

// isEntitled(token) -> mirror of the Python gate, for JS-side checks/tests.
function isEntitled(token) {
  if (!token) return false;
  const rec = loadAll()[token];
  if (!rec) return false;
  const r = rec.remaining;
  return r === null || (Number.isInteger(r) && r > 0);
}

module.exports = { grant, revoke, isEntitled, loadAll, saveAll, storePath, TIER_REMAINING };
