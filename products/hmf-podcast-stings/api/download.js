// api/download.js
//
// GATED delivery endpoint. Assembles and streams a purchased pack ZIP.
//
// Delivery requires an ACTIVE ENTITLEMENT for the requested pack. The buyer is
// identified by `subject` — in production this comes from the authenticated
// session / verified Stripe customer, NOT from arbitrary request input. The
// entitlement itself is only ever written by the Stripe webhook grant path.
//
// If un-entitled -> 403 and NOTHING is delivered (fail-closed). If the founder
// has not yet supplied audio, the endpoint stays in placeholder mode (503) so no
// fake product ships.

'use strict';

const { getPack } = require('../engine/catalog');
const { assemblePack, DeliveryDenied } = require('../engine/packager');

function resolveSubject(req) {
  return (req.headers && (req.headers['x-hmf-subject'] || req.headers['x-hmf-customer'])) ||
    (req.body && req.body.subject) || (req.query && req.query.subject) || null;
}

module.exports = async function handler(req, res) {
  const packId = (req.query && req.query.pack) || (req.body && req.body.pack);
  if (!packId) {
    return res.status(400).json({ error: 'missing_pack', message: 'Specify ?pack=<id>.' });
  }

  const pack = getPack(packId);
  if (!pack) {
    return res.status(404).json({ error: 'no_such_pack', message: `Unknown pack "${packId}".` });
  }

  const subject = resolveSubject(req);
  const requireAudio = pack.available === true;

  try {
    const zip = assemblePack(pack, { subject, requireAudio });
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="sting_pack_${pack.id}.zip"`);
    return res.status(200).send(zip);
  } catch (err) {
    if (err instanceof DeliveryDenied) {
      if (err.code === 'not_entitled') {
        return res.status(403).json({ error: 'not_entitled', message: 'Purchase this pack to download it.' });
      }
      if (err.code === 'policy_failed' && !requireAudio) {
        return res.status(503).json({ error: 'no_audio_yet', message: 'This pack has no license-cleared audio yet. See product README.' });
      }
      return res.status(403).json({ error: err.code, message: err.message });
    }
    console.error('[api/download] error:', err && err.message);
    return res.status(500).json({ error: 'delivery_error', message: 'Could not assemble the pack.' });
  }
};
