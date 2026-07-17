// api/auth/request-link.js — HSF STUB.
// Called by the storefront (story-studio-v2.html L390) to email a magic sign-in
// link for the Creators tier. Passwordless auth (magic link + AUTH_SECRET) is
// NOT implemented in this scaffold. Returns not_implemented so no email is sent
// and nothing pretends a session was created.
'use strict';
module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: magic-link sign-in is not implemented yet (needs AUTH_SECRET + mailer).',
  });
};
