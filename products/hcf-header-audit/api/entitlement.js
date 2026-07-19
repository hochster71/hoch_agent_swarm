// api/entitlement.js
//
// HCF — Email Header Audit — entitlement check (REAL).
//
//     GET /api/entitlement?session_id=<id>
//
// Reads the same record the signed webhook writes via lib/store.js:
//     sess:<id>   (one paid audit)
//
// Read-only. Never grants anything. Never touches money.
'use strict';

const store = require('../lib/store');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use GET.' });
  }

  const sessionId = (req.query && req.query.session_id) || null;
  if (!sessionId) {
    return res.status(400).json({ error: 'no_session_id', message: 'Provide ?session_id=<checkout session id>.' });
  }

  const key = 'sess:' + sessionId;
  const paid = await store.isPaid(key);
  const record = await store.get(key);

  return res.status(200).json({
    entitled: !!paid,
    session_id: sessionId,
    store: store.kvConfigured() ? 'kv' : 'memory',
    record: record ? { paid: !!record.paid, product: record.product || null, tier: record.tier || null, updatedAt: record.updatedAt || null } : null,
  });
};
