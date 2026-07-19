// engine/constants.js
//
// HFF — Client Revenue Concentration Report. Shared constants.
'use strict';

const PRODUCT_NAME = 'Client Revenue Concentration Report';
const PRODUCT_SLUG = 'hff-client-concentration';

// Mandatory disclaimer, rendered on every artifact (XLSX Summary, PDF, JSON).
// Fragments of this wording are allowlisted in engine/advice_linter.js so the
// banner can never trip its own guardrail.
const DISCLAIMER =
  'This report is organizational tooling only. It describes how the revenue in the ' +
  'file you uploaded is distributed across the clients named in that file. It is not ' +
  'financial, tax, or legal advice, and it does not tell you which clients to keep, ' +
  'chase, or drop. Verify every line against your own records before acting.';

// Corporate suffixes stripped when grouping two spellings of the same client.
const CLIENT_SUFFIXES = [
  'INCORPORATED', 'INC', 'LLC', 'L L C', 'LLP', 'LP', 'LTD', 'LIMITED', 'CORP',
  'CORPORATION', 'COMPANY', 'CO', 'PLC', 'GMBH', 'PTY', 'SA', 'NV', 'BV', 'AB', 'AS',
];

// A client counts as "new in the observed window" if its first invoice falls
// within this many days of the end of the window.
const NEW_CLIENT_WINDOW_DAYS = 90;

// A client is flagged "no invoice since expected" when the gap since its last
// invoice exceeds this multiple of that same client's own median gap.
const DORMANCY_MULTIPLE = 2;

module.exports = {
  PRODUCT_NAME,
  PRODUCT_SLUG,
  DISCLAIMER,
  CLIENT_SUFFIXES,
  NEW_CLIENT_WINDOW_DAYS,
  DORMANCY_MULTIPLE,
};
