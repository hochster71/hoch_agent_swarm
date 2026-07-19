// engine/constants.js — HCF Email Header Audit — shared constants.
'use strict';

const PRODUCT_NAME = 'Email Header Audit';
const PRODUCT_SLUG = 'hcf-header-audit';

// The mandatory, non-negotiable disclaimer. The report-linter fails closed if
// this is ever missing from a report.
const DISCLAIMER =
  'HEURISTIC REPORT — NOT A GUARANTEE. This is an offline, text-only reading of the ' +
  'headers you pasted. Headers can be forged, and every authentication result shown ' +
  'here is only what some server CLAIMED in the text — nothing here was re-verified ' +
  'against DNS, and no message body, attachment, or link was examined. This is not a ' +
  'security decision, an incident finding, or professional advice. Treat it as ONE ' +
  'input, confirm anything that matters through an independent trusted channel, and ' +
  'when in doubt do not act on the message.';

// Cap on input size so a paste bomb cannot wedge the function.
const MAX_INPUT_BYTES = 256 * 1024;

// Multi-label public suffixes we recognize when reducing a hostname to its
// registrable domain. APPROXIMATION — not the full Public Suffix List; the
// report says so wherever a registrable domain is used.
const MULTI_LABEL_SUFFIXES = new Set([
  'co.uk', 'org.uk', 'me.uk', 'ac.uk', 'gov.uk', 'net.uk', 'sch.uk',
  'com.au', 'net.au', 'org.au', 'edu.au', 'gov.au', 'id.au',
  'co.nz', 'net.nz', 'org.nz', 'govt.nz',
  'co.jp', 'or.jp', 'ne.jp', 'ac.jp', 'go.jp',
  'com.br', 'net.br', 'org.br', 'gov.br',
  'com.cn', 'net.cn', 'org.cn', 'gov.cn',
  'co.in', 'net.in', 'org.in', 'gov.in', 'ac.in',
  'co.za', 'org.za', 'gov.za',
  'com.mx', 'com.ar', 'com.tr', 'com.sg', 'com.hk', 'com.tw',
  'co.kr', 'or.kr', 'go.kr',
]);

// Domains commonly impersonated in credential-harvest mail. Used ONLY to notice
// that a sender domain LOOKS LIKE one of these without BEING one of these.
const IMPERSONATION_TARGETS = [
  'paypal.com', 'microsoft.com', 'office365.com', 'outlook.com', 'apple.com',
  'icloud.com', 'amazon.com', 'google.com', 'gmail.com', 'netflix.com',
  'docusign.com', 'dropbox.com', 'chase.com', 'wellsfargo.com', 'bankofamerica.com',
  'citibank.com', 'irs.gov', 'ups.com', 'fedex.com', 'dhl.com', 'usps.com',
  'linkedin.com', 'meta.com', 'facebook.com', 'instagram.com', 'coinbase.com',
  'stripe.com', 'adobe.com', 'zoom.us', 'slack.com',
];

module.exports = {
  PRODUCT_NAME,
  PRODUCT_SLUG,
  DISCLAIMER,
  MAX_INPUT_BYTES,
  MULTI_LABEL_SUFFIXES,
  IMPERSONATION_TARGETS,
};
