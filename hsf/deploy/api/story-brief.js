// api/story-brief.js — HSF STUB.
// Called by the storefront (story-studio-v2.html L268) to expand a one-line
// idea into a structured brief. No language model is wired in this scaffold, so
// this returns an honest not_implemented response rather than fake content.
'use strict';
module.exports = async function handler(req, res) {
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: story-brief generation is not wired. No language model configured.',
  });
};
