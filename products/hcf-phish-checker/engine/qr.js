// engine/qr.js
//
// QR intake. HONEST SCOPE / STUB BOUNDARY:
//   Decoding a QR from raw image PIXELS requires a computer-vision decoder. That
//   step is done CLIENT-SIDE in the browser (public/app.html loads a QR-decode
//   library) or by any QR scanner the user already has. This module receives the
//   ALREADY-DECODED payload string and classifies it, then hands any URL payload
//   to the same offline URL heuristics. The engine does not fabricate a decode.
//
// classifyPayload() recognizes the common QR payload grammars so the report can
// say what KIND of thing the QR encodes (a login URL is riskier than a plain
// phone number).

'use strict';

function classifyPayload(text) {
  const s = String(text == null ? '' : text).trim();
  if (s === '') return { kind: 'empty', value: s };
  if (/^https?:\/\//i.test(s)) return { kind: 'url', value: s };
  if (/^WIFI:/i.test(s)) return { kind: 'wifi', value: s };
  if (/^mailto:/i.test(s)) return { kind: 'email', value: s };
  if (/^(tel|sms):/i.test(s)) return { kind: 'phone', value: s };
  if (/^geo:/i.test(s)) return { kind: 'geo', value: s };
  if (/^BEGIN:VCARD/i.test(s)) return { kind: 'vcard', value: s };
  if (/^otpauth:\/\//i.test(s)) return { kind: 'otp', value: s };
  // A bare host like "paypal-login.com/verify" with no scheme — still a link.
  if (/^[a-z0-9.-]+\.[a-z]{2,}(\/|$)/i.test(s) && !/\s/.test(s)) {
    return { kind: 'url', value: s, schemeless: true };
  }
  return { kind: 'text', value: s };
}

module.exports = { classifyPayload };
