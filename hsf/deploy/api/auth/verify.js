// api/auth/verify.js — HSF STUB.
// Referenced by vercel.json (/api/auth/verify). Verifies a magic-link token and
// establishes a Creators session. NOT implemented in this scaffold.
'use strict';
module.exports = async function handler(req, res) {
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: magic-link verification is not implemented yet.',
  });
};
