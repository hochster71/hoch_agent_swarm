// api/morph.js — HSF STUB.
// Referenced by vercel.json (/api/morph). Scene/character morph transforms are
// not implemented in this scaffold. Honest not_implemented response.
'use strict';
module.exports = async function handler(req, res) {
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: morph is not implemented yet.',
  });
};
