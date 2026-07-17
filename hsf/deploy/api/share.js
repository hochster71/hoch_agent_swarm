// api/share.js — HSF STUB.
// Referenced by vercel.json (/api/share). Public share-link creation is not
// implemented in this scaffold. Honest not_implemented response.
'use strict';
module.exports = async function handler(req, res) {
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: share is not implemented yet.',
  });
};
