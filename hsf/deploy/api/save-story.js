// api/save-story.js — HSF STUB.
// Referenced by vercel.json (/api/save-story). Persisting an in-progress story
// is not implemented in this scaffold. Returns a clear not_implemented response
// so the deploy manifest resolves without pretending the feature exists.
'use strict';
module.exports = async function handler(req, res) {
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: save-story is not implemented yet.',
  });
};
